"""Strict validation for a revision manifest.

Canonical contract: Schemas/revisions.schema.json, held by the fixtures
under Conformance/revisions and the parity test. A selection is exclusive —
exactly one of branch or commit — and a commit is a full 40-hex identity,
because an abbreviation is ambiguity, not identity.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import document
from .environment import INTEGRATIONS

SCHEMA_VERSION = 1

_ROOT_KEYS = ("schema_version", "line", "selections")
_LINE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _is_branch_name(value):
    if not isinstance(value, str) or not value or value.startswith("-"):
        return False
    if value == "@" or value.endswith(("/", ".")):
        return False
    if ".." in value or "@{" in value or "//" in value:
        return False
    forbidden = set(" ~^:?*[\\")
    if any(character in forbidden or ord(character) < 32 \
           or ord(character) == 127 for character in value):
        return False
    return all(
        component and not component.startswith(".")
        and not component.endswith(".lock")
        for component in value.split("/"))


@dataclass(frozen=True)
class Selection:
    branch: str = ""
    commit: str = ""


@dataclass(frozen=True)
class RevisionsDocument:
    line: str
    selections: dict


def _check_selection(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return None
    keys = sorted(value)
    for key in keys:
        if key not in ("branch", "commit"):
            errors.append(f"{where}.{key}: unknown name")
    named = [key for key in keys if key in ("branch", "commit")]
    if len(named) != 1:
        errors.append(
            f"{where}: exactly one of branch or commit, got {len(named)}")
        return None
    if "branch" in value:
        branch = value["branch"]
        if not _is_branch_name(branch):
            errors.append(f"{where}.branch: must be a safe full branch name")
            return None
        return Selection(branch=branch)
    commit = value["commit"]
    if not isinstance(commit, str) or not _COMMIT_PATTERN.fullmatch(commit):
        errors.append(f"{where}.commit: must be a full 40-hex commit id")
        return None
    return Selection(commit=commit)


def validate_revisions_text(text):
    """Validate one manifest; returns (RevisionsDocument or None, errors)."""
    errors = []
    try:
        root = document.loads(text)
    except document.JsonDocumentError as error:
        return None, [f"document: not valid JSON ({error})"]
    if not isinstance(root, dict):
        return None, ["document: the root must be an object"]

    for key in sorted(root):
        if key not in _ROOT_KEYS:
            errors.append(f"document.{key}: unknown name")

    version = root.get("schema_version")
    if "schema_version" not in root:
        errors.append("schema_version: required")
    elif isinstance(version, bool) or not isinstance(version, int) \
            or version != SCHEMA_VERSION:
        errors.append(f"schema_version: must be the integer {SCHEMA_VERSION}")

    line = root.get("line")
    if "line" not in root:
        errors.append("line: required")
    elif not isinstance(line, str) or not _LINE_PATTERN.fullmatch(line):
        errors.append("line: must match ^[a-z0-9][a-z0-9-]*$")

    selections = {}
    if "selections" not in root:
        errors.append("selections: required")
    elif not isinstance(root["selections"], dict):
        errors.append("selections: must be an object")
    elif not root["selections"]:
        errors.append("selections: must select at least one integration")
    else:
        for name in sorted(root["selections"]):
            if name not in INTEGRATIONS:
                errors.append(
                    f"selections.{name}: unknown name — the roster is closed")
                continue
            selection = _check_selection(
                errors, f"selections.{name}", root["selections"][name])
            if selection is not None:
                selections[name] = selection

    if errors:
        return None, errors
    return RevisionsDocument(line=line, selections=selections), []


def load_revisions(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_revisions_text(text)
