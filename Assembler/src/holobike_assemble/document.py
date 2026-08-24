"""Strict JSON decoding, and holding a document to its contract."""

from __future__ import annotations

import json
import pathlib


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


def parse(text, contract):
    """Decode `text` strictly and validate it against a compiled schema.

    Returns `(document, errors)`. Strictness that JSON Schema cannot express —
    duplicate members, non-finite numbers — is refused here before the schema
    ever sees the document, because a schema validates a decoded value and by
    then the ambiguity is already resolved one way or the other.
    """
    try:
        root = loads(text)
    except JsonDocumentError as error:
        return None, [f"document: not valid JSON ({error})"]
    errors = contract.validate(root)
    if errors:
        return None, errors
    return root, []


def read(path, contract):
    """`parse` for a file, reporting an unreadable path as a document error."""
    try:
        text = pathlib.Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return parse(text, contract)
