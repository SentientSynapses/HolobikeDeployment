"""Strict JSON decoding shared by declared deployment contracts."""

from __future__ import annotations

import json


class JsonDocumentError(ValueError):
    """A document is not strict, interoperable JSON."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JsonDocumentError(f"duplicate object member {key!r}")
        result[key] = value
    return result


def _reject_nonfinite(value):
    raise JsonDocumentError(f"non-finite number {value!r} is not JSON")


def loads(text):
    """Decode strict JSON, rejecting ambiguous members and extensions."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonfinite,
        )
    except JsonDocumentError:
        raise
    except json.JSONDecodeError as error:
        raise JsonDocumentError(
            f"{error.msg}, line {error.lineno}") from error
