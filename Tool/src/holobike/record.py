"""Run records, and their binding.

Canonical contract: `schemas/record.schema.json`, enforced by `schema.py` and
held by the fixtures under `tests/fixtures/record`. Every verb validates the
record it is about to write through this module before writing it — a tool
that emits documents it would refuse to read has no contract at all.

The schema carries the shape, including the five kinds: it is one `allOf` of
`if kind == … then …`, so a resolution with actions or a bootstrap with gates
is refused there, as a category error rather than a tolerance.

Two rules remain here because no schema can state them. Both are cross-field
set equalities — an assembly's `builds` and an emulation's `members` must key
exactly the deployables the same record claims, so a record cannot describe
work on something it did not say it composed. Those are keyed by deployable
while `resolved` and `actions` stay keyed by integration, because a checkout
is per repository however many deployables it produces.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from . import document, filesystem, schema

SCHEMA_VERSION = 3
MAX_RECORD_BYTES = 4 * 1024 * 1024

# Which key must agree with `integrations`, per kind.
_ROSTER_AGREEMENT = {"assembly": "builds", "emulation": "members"}


def _bind(root):
    errors = []
    kind = root["kind"]

    holder = _ROSTER_AGREEMENT.get(kind)
    if holder:
        declared = set(root["deployables"])
        if set(root[holder]) != declared:
            errors.append(
                f"{holder}: keys must exactly match the recorded "
                "deployables")

    if errors:
        return None, errors
    return root, []


def validate_record_text(text):
    root, errors = document.parse(text, schema.contract("record"))
    if errors:
        return None, errors
    return _bind(root)


def load_record(path):
    root, _, _, errors = load_record_snapshot(path)
    return root, errors


def load_record_snapshot(path):
    """Return one parsed record, its exact text and digest, or errors.

    The digest is taken over the bytes read, not over a re-serialization: the
    chain binds records by what is on disk.
    """
    try:
        content = filesystem.read_file_snapshot(
            Path(path), max_bytes=MAX_RECORD_BYTES)
        text = content.decode("utf-8")
    except (OSError, UnicodeError,
            filesystem.FilesystemContractError) as error:
        return None, None, None, [f"document: unreadable: {error}"]
    root, errors = validate_record_text(text)
    if errors:
        return None, text, None, errors
    return root, text, hashlib.sha256(content).hexdigest(), []
