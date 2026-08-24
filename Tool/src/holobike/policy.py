"""The policy document's binding.

Canonical contract: `schemas/policy.schema.json`, enforced by `schema.py` and
held by the fixtures under `tests/fixtures/policy`. The rules it carries — a
site path is relative and may not escape its checkout, excluded names are
path components declared per gate rather than assumed by the tool, a gate
kind is `tree_parity` — are stated there.

What remains here is the one rule a schema cannot state: gate names are
unique within a document. `uniqueItems` compares whole gates, and two gates
differing only in their sites would still collide on name.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import document, schema

SCHEMA_VERSION = 1


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


def _site(value):
    return Site(integration=value["integration"], path=value["path"])


def _bind(root):
    errors = []
    gates = []
    seen = set()
    for index, raw in enumerate(root["gates"]):
        if raw["name"] in seen:
            errors.append(f"gates[{index}].name: duplicate gate name")
            continue
        seen.add(raw["name"])
        gates.append(Gate(
            name=raw["name"],
            kind=raw["kind"],
            left=_site(raw["left"]),
            right=_site(raw["right"]),
            exclude=tuple(raw.get("exclude") or ())))
    if errors:
        return None, errors
    return PolicyDocument(policy=root["policy"], gates=tuple(gates)), []


def validate_policy_text(text):
    """Validate one policy document; returns (PolicyDocument or None, errors)."""
    root, errors = document.parse(text, schema.contract("policy"))
    if errors:
        return None, errors
    return _bind(root)


def load_policy(path):
    root, errors = document.read(path, schema.contract("policy"))
    if errors:
        return None, errors
    return _bind(root)
