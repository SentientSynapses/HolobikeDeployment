"""Strict validation for profiles.

Canonical contract: Schemas/profiles.schema.json, held by the fixtures
under Conformance/profiles.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .environment import INTEGRATIONS

SCHEMA_VERSION = 1

_ROOT_KEYS = ("schema_version", "profile", "integrations")
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class ProfileDocument:
    profile: str
    integrations: tuple


def validate_profile_text(text):
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

    profile = root.get("profile")
    if "profile" not in root:
        errors.append("profile: required")
    elif not isinstance(profile, str) or not _NAME_PATTERN.fullmatch(profile):
        errors.append("profile: must match ^[a-z0-9][a-z0-9-]*$")

    integrations = []
    if "integrations" not in root:
        errors.append("integrations: required")
    elif not isinstance(root["integrations"], list) \
            or not root["integrations"]:
        errors.append("integrations: must be a non-empty array")
    else:
        seen = set()
        for name in root["integrations"]:
            if name not in INTEGRATIONS:
                errors.append(
                    f"integrations: unknown name {name!r} — the roster is "
                    "closed")
                continue
            if name in seen:
                errors.append(f"integrations: {name} listed twice")
                continue
            seen.add(name)
            integrations.append(name)

    if errors:
        return None, errors
    return ProfileDocument(
        profile=profile, integrations=tuple(integrations)), []


def load_profile(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_profile_text(text)
