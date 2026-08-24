"""The profile contract's binding.

Canonical contract: `Schemas/profiles.schema.json`, enforced by `schema.py`
and held by the fixtures under `Conformance/profiles`.

What remains here is what a schema cannot say. The topology map may only key
integrations *this profile* carries — a cross-field rule, which the schema's
own description defers to this binding — and the typed view the verbs consume.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import document, schema

SCHEMA_VERSION = 1
RUN_MODES = ("host",)


@dataclass(frozen=True)
class MemberTopology:
    run: str = "host"
    environment: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileDocument:
    profile: str
    integrations: tuple
    topology: dict = field(default_factory=dict)


def _bind(root):
    errors = []
    members = set(root["integrations"])
    topology = {}
    declared = root.get("topology") or {}
    for name in sorted(declared):
        if name not in members:
            errors.append(
                f"topology.{name}: not a member of this profile's "
                "integrations")
            continue
        entry = declared[name]
        topology[name] = MemberTopology(
            run=entry.get("run", "host"),
            environment=dict(entry.get("environment") or {}))
    if errors:
        return None, errors
    return ProfileDocument(
        profile=root["profile"],
        integrations=tuple(root["integrations"]),
        topology=topology), []


def validate_profile_text(text):
    root, errors = document.parse(text, schema.contract("profiles"))
    if errors:
        return None, errors
    return _bind(root)


def load_profile(path):
    root, errors = document.read(path, schema.contract("profiles"))
    if errors:
        return None, errors
    return _bind(root)
