"""Strict validation for the development-environment mapping.

The canonical contract is Schemas/environment.schema.json. This module is a
hand-written binding to it — Python ships no JSON-Schema engine and this
tool takes no dependencies — held in agreement with the schema by the
fixtures under Conformance/environment and by the roster-parity test.

Validation is fail-closed: unknown keys are rejections, not tolerances. A
misspelled integration name must fail rather than silently deselect an
integration.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SCHEMA_VERSION = 1

# The closed integration roster. The schema is canonical; the parity test
# refuses a drift between this tuple and the schema's own property set.
INTEGRATIONS = (
    "uroborOS",
    "HexAtlas",
    "Assetscape",
    "HolobikeCore",
    "AthleteIdentity",
    "drAIs",
    "HolobikeExperience",
    "HolobikeDevice",
    "HolobikeRider",
    "HolobikeWorlds",
)

TOOLCHAINS = (
    "unreal_engine",
    "vcpkg",
)

_ROOT_KEYS = ("schema_version", "checkouts", "toolchains")


@dataclass(frozen=True)
class EnvironmentDocument:
    """A validated mapping: declared checkouts and toolchains by name."""

    checkouts: dict = field(default_factory=dict)
    toolchains: dict = field(default_factory=dict)


def _check_path_value(errors, where, value):
    if not isinstance(value, str):
        errors.append(f"{where}: must be a string path")
        return
    if not value:
        errors.append(f"{where}: must not be empty")
        return
    if not value.startswith("/"):
        errors.append(f"{where}: must be an absolute path")


def _check_closed_object(errors, where, value, allowed):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return {}
    for key in sorted(value):
        if key not in allowed:
            errors.append(f"{where}.{key}: unknown name")
    for key in allowed:
        if key in value:
            _check_path_value(errors, f"{where}.{key}", value[key])
    return {key: value[key] for key in allowed
            if key in value and isinstance(value[key], str)}


def validate_environment_text(text):
    """Validate one document; returns (EnvironmentDocument or None, errors).

    The document is returned only when the error list is empty.
    """
    errors = []
    try:
        root = json.loads(text)
    except json.JSONDecodeError as error:
        return None, [f"document: not valid JSON ({error.msg}, line {error.lineno})"]
    if not isinstance(root, dict):
        return None, ["document: the root must be an object"]

    for key in sorted(root):
        if key not in _ROOT_KEYS:
            errors.append(f"document.{key}: unknown name")

    if "schema_version" not in root:
        errors.append("schema_version: required")
    else:
        version = root["schema_version"]
        # bool is an int in Python; a boolean version is still a rejection.
        if isinstance(version, bool) or not isinstance(version, int):
            errors.append("schema_version: must be the integer 1")
        elif version != SCHEMA_VERSION:
            errors.append(
                f"schema_version: must be {SCHEMA_VERSION}, got {version}")

    checkouts = {}
    if "checkouts" not in root:
        errors.append("checkouts: required")
    else:
        checkouts = _check_closed_object(
            errors, "checkouts", root["checkouts"], INTEGRATIONS)

    toolchains = {}
    if "toolchains" in root:
        toolchains = _check_closed_object(
            errors, "toolchains", root["toolchains"], TOOLCHAINS)

    if errors:
        return None, errors
    return EnvironmentDocument(checkouts=checkouts, toolchains=toolchains), []


def load_environment(path):
    """Read and validate the document at path; returns (doc or None, errors)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_environment_text(text)
