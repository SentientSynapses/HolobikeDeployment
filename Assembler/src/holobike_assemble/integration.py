"""Strict validation for a Stack leaf's integration contract.

The canonical contract is Schemas/integration.schema.json; this module is a
hand-written binding held to it by the fixtures under
Conformance/integration and by the roster-parity test. Fail-closed
throughout: unknown keys and unknown names are rejections.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .environment import INTEGRATIONS

SCHEMA_VERSION = 1

KITS = ("ai_kit", "bike_kit", "geo_kit", "id_kit", "os_kit", "ue_kit")

_ROOT_KEYS = ("schema_version", "integration", "kit", "repository",
              "origin", "entry_points")
_ENTRY_POINTS = ("prove",)


@dataclass(frozen=True)
class IntegrationDocument:
    integration: str
    kit: str
    repository: str
    origin: str = ""
    prove_argv: tuple = ()


def _check_repository_name(errors, value):
    if not isinstance(value, str) or not value:
        errors.append("repository: must be a non-empty string")
        return
    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")
    if not set(value) <= allowed:
        errors.append("repository: must match ^[A-Za-z0-9._-]+$")


def _check_entry_points(errors, value):
    prove_argv = ()
    if not isinstance(value, dict):
        errors.append("entry_points: must be an object")
        return prove_argv
    for key in sorted(value):
        if key not in _ENTRY_POINTS:
            errors.append(f"entry_points.{key}: unknown name")
    if "prove" in value:
        prove = value["prove"]
        if not isinstance(prove, dict):
            errors.append("entry_points.prove: must be an object")
            return prove_argv
        for key in sorted(prove):
            if key != "argv":
                errors.append(f"entry_points.prove.{key}: unknown name")
        argv = prove.get("argv")
        if not isinstance(argv, list) or not argv:
            errors.append(
                "entry_points.prove.argv: must be a non-empty array")
        elif any(not isinstance(item, str) or not item for item in argv):
            errors.append(
                "entry_points.prove.argv: every element must be a "
                "non-empty string")
        else:
            prove_argv = tuple(argv)
    return prove_argv


def validate_integration_text(text):
    """Validate one leaf document; returns (IntegrationDocument or None, errors)."""
    errors = []
    try:
        root = json.loads(text)
    except json.JSONDecodeError as error:
        return None, [
            f"document: not valid JSON ({error.msg}, line {error.lineno})"]
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

    integration = root.get("integration")
    if "integration" not in root:
        errors.append("integration: required")
    elif integration not in INTEGRATIONS:
        errors.append(
            f"integration: unknown name {integration!r} — the roster is "
            "closed")

    kit = root.get("kit")
    if "kit" not in root:
        errors.append("kit: required")
    elif kit not in KITS:
        errors.append(f"kit: unknown kit {kit!r}")

    if "repository" not in root:
        errors.append("repository: required")
    else:
        _check_repository_name(errors, root["repository"])

    origin = ""
    if "origin" in root:
        raw_origin = root["origin"]
        if not isinstance(raw_origin, str) or not raw_origin \
                or any(character.isspace() for character in raw_origin):
            errors.append("origin: must be a non-empty string without spaces")
        else:
            origin = raw_origin

    prove_argv = ()
    if "entry_points" in root:
        prove_argv = _check_entry_points(errors, root["entry_points"])

    if errors:
        return None, errors
    return IntegrationDocument(
        integration=integration,
        kit=kit,
        repository=root["repository"],
        origin=origin,
        prove_argv=prove_argv,
    ), []


def load_integration(path):
    """Read and validate the leaf at path; returns (doc or None, errors)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_integration_text(text)
