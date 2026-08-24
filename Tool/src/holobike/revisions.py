"""The revision manifest's binding.

Canonical contract: `schemas/revisions.schema.json`, enforced by `schema.py`
and held by the fixtures under `tests/fixtures/revisions`. The rules it carries —
a selection is exclusive, exactly one of branch or commit; a commit is a full
40-hex identity because an abbreviation is ambiguity, not identity; a branch
name is one git will accept — are all stated there.

Nothing cross-field remains, so this module is the typed view and no more.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import document, schema

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Selection:
    branch: str = ""
    commit: str = ""


@dataclass(frozen=True)
class RevisionsDocument:
    line: str
    selections: dict


def _bind(root):
    return RevisionsDocument(
        line=root["line"],
        selections={
            name: Selection(branch=value.get("branch", ""),
                            commit=value.get("commit", ""))
            for name, value in sorted(root["selections"].items())
        }), []


def validate_revisions_text(text):
    """Validate one manifest; returns (RevisionsDocument or None, errors)."""
    root, errors = document.parse(text, schema.contract("revisions"))
    if errors:
        return None, errors
    return _bind(root)


def load_revisions(path):
    root, errors = document.read(path, schema.contract("revisions"))
    if errors:
        return None, errors
    return _bind(root)
