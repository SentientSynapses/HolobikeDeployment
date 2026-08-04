"""Strict validation for profiles.

Canonical contract: Schemas/profiles.schema.json, held by the fixtures
under Conformance/profiles.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .environment import INTEGRATIONS

SCHEMA_VERSION = 1

_ROOT_KEYS = ("schema_version", "profile", "integrations", "topology")
_MEMBER_KEYS = ("run", "environment")
RUN_MODES = ("host",)
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class MemberTopology:
    run: str = "host"
    environment: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileDocument:
    profile: str
    integrations: tuple
    topology: dict = field(default_factory=dict)


def _check_environment_map(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return {}
    for key, entry in sorted(value.items()):
        if not key or not isinstance(entry, str):
            errors.append(
                f"{where}.{key or '<empty>'}: keys must be non-empty and "
                "values must be strings")
            return {}
    return dict(value)


def _check_topology(errors, value, members):
    topology = {}
    if not isinstance(value, dict):
        errors.append("topology: must be an object")
        return topology
    for name in sorted(value):
        where = f"topology.{name}"
        if name not in members:
            errors.append(
                f"{where}: not a member of this profile's integrations")
            continue
        entry = value[name]
        if not isinstance(entry, dict):
            errors.append(f"{where}: must be an object")
            continue
        for key in sorted(entry):
            if key not in _MEMBER_KEYS:
                errors.append(f"{where}.{key}: unknown name")
        run = entry.get("run", "host")
        if run not in RUN_MODES:
            errors.append(f"{where}.run: must be one of {RUN_MODES}")
            continue
        environment = {}
        if "environment" in entry:
            environment = _check_environment_map(
                errors, f"{where}.environment", entry["environment"])
        topology[name] = MemberTopology(run=run, environment=environment)
    return topology


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

    topology = {}
    if "topology" in root:
        topology = _check_topology(errors, root["topology"], set(integrations))

    if errors:
        return None, errors
    return ProfileDocument(
        profile=profile,
        integrations=tuple(integrations),
        topology=topology), []


def load_profile(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_profile_text(text)
