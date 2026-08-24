"""A Stack leaf's integration contract, and its binding.

Canonical contract: `Schemas/integration.schema.json`, enforced by
`schema.py` and held by the fixtures under `Conformance/integration`.

A leaf declares **named deployables** (D-11): a repository may produce more
than one, and several here produce both the device half and the server half
of one contract. `prove` stays at the leaf, because it proves the repository
rather than any single deployable. A deployable with no build and no
artifacts is a *recorded absence* — named, visibly unbuildable here, and
honest about it rather than silently missing.

Two rules a schema cannot state live here. Artifact file names must be unique
across the whole leaf, because `assemble` stages them flat into one bundle
and two paths ending in the same name would collide. And a leaf may carry at
most one deployable that builds, for as long as the verbs still work per
integration — see `producer` below.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from . import document, schema

SCHEMA_VERSION = 2

DOMAINS = tuple(
    schema.contract("integration").document["properties"]["domain"]["enum"])
#: Destination values that end a chain rather than naming another member.
TERMINALS = ("device", "server")


@dataclass(frozen=True)
class Command:
    """One declared command: argv, executed without a shell, plus a
    non-secret environment overlay."""
    argv: tuple = ()
    env: tuple = ()  # sorted (key, value) pairs; hashable for frozen use


@dataclass(frozen=True)
class Deployable:
    """One named output of a repository, and where it ends up."""
    name: str
    destination: str
    build_steps: tuple = ()
    artifacts: tuple = ()
    serve: Command = Command()
    probe: Command = Command()

    @property
    def is_recorded_absence(self):
        """Named, and nothing here can build it. That is a fact, not a gap."""
        return not self.build_steps and not self.artifacts

    @property
    def is_terminal(self):
        return self.destination in TERMINALS


@dataclass(frozen=True)
class IntegrationDocument:
    integration: str
    domain: str
    repository: str
    origin: str = ""
    unreal_project: str = ""
    prove_argv: tuple = ()
    deployables: tuple = ()

    def deployable(self, name):
        for candidate in self.deployables:
            if candidate.name == name:
                return candidate
        return None

    @property
    def producer(self):
        """The one deployable that builds, or None.

        Transitional. The verbs still work per integration, and every leaf
        today has at most one deployable that builds, so this is unambiguous
        — the binding refuses a leaf where it would not be. Phase 3 selects
        deployables directly and this goes.
        """
        building = [d for d in self.deployables if d.build_steps or d.artifacts
                    or d.serve.argv or d.probe.argv]
        return building[0] if building else None

    @property
    def build_steps(self):
        return self.producer.build_steps if self.producer else ()

    @property
    def artifacts(self):
        return self.producer.artifacts if self.producer else ()

    @property
    def serve(self):
        return self.producer.serve if self.producer else Command()

    @property
    def probe(self):
        return self.producer.probe if self.producer else Command()


def _command(value):
    if not value:
        return Command()
    return Command(
        argv=tuple(value["argv"]),
        env=tuple(sorted((value.get("env") or {}).items())))


def _bind(root):
    errors = []
    deployables = []
    for name, body in root["deployables"].items():
        deployables.append(Deployable(
            name=name,
            destination=body["destination"],
            build_steps=tuple(
                tuple(step["argv"])
                for step in (body.get("build") or {}).get("steps") or ()),
            artifacts=tuple(body.get("artifacts") or ()),
            serve=_command(body.get("serve")),
            probe=_command(body.get("probe"))))

    names = [PurePosixPath(path).name
             for d in deployables for path in d.artifacts]
    if len(set(names)) != len(names):
        errors.append(
            "deployables: artifact file names must be unique across the "
            "leaf — assemble stages them flat into one bundle")

    active = [d for d in deployables
              if d.build_steps or d.artifacts or d.serve.argv or d.probe.argv]
    if len(active) > 1:
        errors.append(
            "deployables: more than one deployable declares work, and the "
            "verbs still select whole integrations — "
            f"{', '.join(sorted(d.name for d in active))}")

    if errors:
        return None, errors
    return IntegrationDocument(
        integration=root["integration"],
        domain=root["domain"],
        repository=root["repository"],
        origin=root.get("origin", ""),
        unreal_project=root.get("unreal_project", ""),
        prove_argv=tuple((root.get("prove") or {}).get("argv") or ()),
        deployables=tuple(deployables),
    ), []


def validate_integration_text(text):
    """Validate one leaf document; returns (IntegrationDocument or None, errors)."""
    root, errors = document.parse(text, schema.contract("integration"))
    if errors:
        return None, errors
    return _bind(root)


def load_integration(path):
    """Read and validate the leaf at path; returns (doc or None, errors)."""
    root, errors = document.read(path, schema.contract("integration"))
    if errors:
        return None, errors
    return _bind(root)
