"""A Stack leaf's integration contract, and its binding.

Canonical contract: `Schemas/integration.schema.json`, enforced by
`schema.py` and held by the fixtures under `Conformance/integration`. The
shape rules — the closed roster, the closed kit set, a repository name, an
origin without spaces, checkout-relative artifact paths that never escape, a
`.uproject` that is a real relative path — are stated there.

Two things remain here. The one rule a schema cannot state: artifact *file
names* must be unique, because `assemble` stages them flat into one bundle
and two paths ending in the same name would collide even though the paths
differ. And the flattening the verbs consume — `entry_points` is a document
shape, while `preflight` wants argv, `assemble` wants build steps, and
`emulate` wants commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from . import document, schema

SCHEMA_VERSION = 1

KITS = tuple(
    schema.contract("integration").document["properties"]["kit"]["enum"])


@dataclass(frozen=True)
class Command:
    """One declared command: argv, executed without a shell, plus a
    non-secret environment overlay."""
    argv: tuple = ()
    env: tuple = ()  # sorted (key, value) pairs; hashable for frozen use


@dataclass(frozen=True)
class IntegrationDocument:
    integration: str
    kit: str
    repository: str
    origin: str = ""
    unreal_project: str = ""
    prove_argv: tuple = ()
    build_steps: tuple = ()
    artifacts: tuple = ()
    serve: Command = Command()
    probe: Command = Command()


def _command(value):
    if not value:
        return Command()
    return Command(
        argv=tuple(value["argv"]),
        env=tuple(sorted((value.get("env") or {}).items())))


def _bind(root):
    entry_points = root.get("entry_points") or {}
    artifacts = tuple(root.get("artifacts") or ())

    names = [PurePosixPath(path).name for path in artifacts]
    if len(set(names)) != len(names):
        return None, [
            "artifacts: file names must be unique in the staged bundle"]

    build = entry_points.get("build") or {}
    return IntegrationDocument(
        integration=root["integration"],
        kit=root["kit"],
        repository=root["repository"],
        origin=root.get("origin", ""),
        unreal_project=root.get("unreal_project", ""),
        prove_argv=tuple((entry_points.get("prove") or {}).get("argv") or ()),
        build_steps=tuple(
            tuple(step["argv"]) for step in build.get("steps") or ()),
        artifacts=artifacts,
        serve=_command(entry_points.get("serve")),
        probe=_command(entry_points.get("probe")),
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
