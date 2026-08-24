"""The profile contract's binding.

Canonical contract: `Schemas/profiles.schema.json`, enforced by `schema.py`
and held by the fixtures under `Conformance/profiles`.

A profile names **deployables**, not whole repositories (D-11), so a
development composition can take the device half of a contract and leave the
estate half alone. One profile per destination: the verb chooses the posture,
so a development run and a release run of the same product are the same
document rather than two that must be kept in agreement (D-16).

What remains here is what a schema cannot say: `topology` may only key
deployables *this profile* selects. Whether a selected deployable exists at
all, and whether its own destination resolves to this profile's, needs the
whole Stack and lives in `stack.select`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import document, schema

SCHEMA_VERSION = 2
RUN_MODES = ("host",)


@dataclass(frozen=True)
class Selection:
    """One chosen deployable, named by its integration and its own name."""
    integration: str
    deployable: str

    @property
    def ref(self):
        """`Integration.Deployable` — how topology keys it, and how a
        problem names it."""
        return f"{self.integration}.{self.deployable}"


@dataclass(frozen=True)
class MemberTopology:
    run: str = "host"
    environment: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ProfileDocument:
    profile: str
    destination: str
    selections: tuple
    topology: dict = field(default_factory=dict)

    @property
    def integrations(self):
        """The distinct integrations selected, in declaration order.

        Derived, never declared: a profile that listed both would be two
        statements of one fact, and they would drift.
        """
        seen = []
        for selection in self.selections:
            if selection.integration not in seen:
                seen.append(selection.integration)
        return tuple(seen)

    def selection_for(self, integration):
        for selection in self.selections:
            if selection.integration == integration:
                return selection
        return None

    def topology_for(self, selection):
        return self.topology.get(selection.ref, MemberTopology())


def _bind(root):
    errors = []
    selections = tuple(
        Selection(integration=item["integration"],
                  deployable=item["deployable"])
        for item in root["deployables"])

    refs = {selection.ref for selection in selections}
    for ref in sorted(root.get("topology") or {}):
        if ref not in refs:
            errors.append(
                f"topology.{ref}: not a deployable this profile selects")

    if errors:
        return None, errors
    topology = {
        ref: MemberTopology(run=entry.get("run", "host"),
                            environment=dict(entry.get("environment") or {}))
        for ref, entry in (root.get("topology") or {}).items()
    }
    return ProfileDocument(
        profile=root["profile"],
        destination=root["destination"],
        selections=selections,
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
