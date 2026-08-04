"""Strict validation for policy documents.

Canonical contract: Schemas/policy.schema.json, held by the fixtures under
Conformance/policy. A site path is relative and may not escape its
checkout; excluded names are path components, declared per gate rather
than assumed by the tool.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .environment import INTEGRATIONS

SCHEMA_VERSION = 1

_ROOT_KEYS = ("schema_version", "policy", "gates")
_GATE_KEYS = ("name", "kind", "left", "right", "exclude")
_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")


@dataclass(frozen=True)
class Site:
    integration: str
    path: str


@dataclass(frozen=True)
class Gate:
    name: str
    kind: str
    left: Site
    right: Site
    exclude: tuple = field(default_factory=tuple)


@dataclass(frozen=True)
class PolicyDocument:
    policy: str
    gates: tuple


def _check_site(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return None
    for key in sorted(value):
        if key not in ("integration", "path"):
            errors.append(f"{where}.{key}: unknown name")
    integration = value.get("integration")
    if integration not in INTEGRATIONS:
        errors.append(
            f"{where}.integration: unknown name — the roster is closed")
        return None
    path = value.get("path")
    if not isinstance(path, str) or not path:
        errors.append(f"{where}.path: must be a non-empty string")
        return None
    if path.startswith("/") or ".." in Path(path).parts:
        errors.append(f"{where}.path: must be relative and must not escape")
        return None
    return Site(integration=integration, path=path)


def _check_gate(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return None
    for key in sorted(value):
        if key not in _GATE_KEYS:
            errors.append(f"{where}.{key}: unknown name")
    name = value.get("name")
    if not isinstance(name, str) or not _NAME_PATTERN.fullmatch(name):
        errors.append(f"{where}.name: must match ^[a-z0-9][a-z0-9-]*$")
        name = None
    if value.get("kind") != "tree_parity":
        errors.append(f"{where}.kind: must be tree_parity")
    left = _check_site(errors, f"{where}.left", value.get("left")) \
        if "left" in value else errors.append(f"{where}.left: required")
    right = _check_site(errors, f"{where}.right", value.get("right")) \
        if "right" in value else errors.append(f"{where}.right: required")
    exclude = ()
    if "exclude" in value:
        raw = value["exclude"]
        if not isinstance(raw, list) or any(
                not isinstance(item, str) or not item or "/" in item
                for item in raw):
            errors.append(
                f"{where}.exclude: must be an array of path component names")
        else:
            exclude = tuple(raw)
    if name is None or left is None or right is None:
        return None
    return Gate(name=name, kind="tree_parity", left=left, right=right,
                exclude=exclude)


def validate_policy_text(text):
    """Validate one policy document; returns (PolicyDocument or None, errors)."""
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

    policy = root.get("policy")
    if "policy" not in root:
        errors.append("policy: required")
    elif not isinstance(policy, str) or not _NAME_PATTERN.fullmatch(policy):
        errors.append("policy: must match ^[a-z0-9][a-z0-9-]*$")

    gates = []
    if "gates" not in root:
        errors.append("gates: required")
    elif not isinstance(root["gates"], list) or not root["gates"]:
        errors.append("gates: must be a non-empty array")
    else:
        names = set()
        for index, raw in enumerate(root["gates"]):
            gate = _check_gate(errors, f"gates[{index}]", raw)
            if gate is not None:
                if gate.name in names:
                    errors.append(f"gates[{index}].name: duplicate gate name")
                names.add(gate.name)
                gates.append(gate)

    if errors:
        return None, errors
    return PolicyDocument(policy=policy, gates=tuple(gates)), []


def load_policy(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_policy_text(text)
