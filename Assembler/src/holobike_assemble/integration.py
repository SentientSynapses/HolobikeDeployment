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
              "origin", "entry_points", "artifacts")
_ENTRY_POINTS = ("prove", "build", "serve", "probe")


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
    prove_argv: tuple = ()
    build_steps: tuple = ()
    artifacts: tuple = ()
    serve: Command = Command()
    probe: Command = Command()


def _check_repository_name(errors, value):
    if not isinstance(value, str) or not value:
        errors.append("repository: must be a non-empty string")
        return
    allowed = set(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._-")
    if not set(value) <= allowed:
        errors.append("repository: must match ^[A-Za-z0-9._-]+$")


def _check_argv(errors, where, value):
    if not isinstance(value, list) or not value:
        errors.append(f"{where}: must be a non-empty array")
        return ()
    if any(not isinstance(item, str) or not item for item in value):
        errors.append(f"{where}: every element must be a non-empty string")
        return ()
    return tuple(value)


def _check_environment_map(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return ()
    for key, entry in sorted(value.items()):
        if not key or not isinstance(entry, str):
            errors.append(
                f"{where}: keys must be non-empty and values must be "
                "strings")
            return ()
    return tuple(sorted(value.items()))


def _check_command(errors, where, value):
    """A serve/probe entry: {argv, env?}; returns a Command."""
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return Command()
    for key in sorted(value):
        if key not in ("argv", "env"):
            errors.append(f"{where}.{key}: unknown name")
    argv = _check_argv(errors, f"{where}.argv", value.get("argv"))
    env = ()
    if "env" in value:
        env = _check_environment_map(errors, f"{where}.env", value["env"])
    return Command(argv=argv, env=env)


def _check_entry_points(errors, value):
    prove_argv = ()
    build_steps = ()
    serve = Command()
    probe = Command()
    if not isinstance(value, dict):
        errors.append("entry_points: must be an object")
        return prove_argv, build_steps, serve, probe
    for key in sorted(value):
        if key not in _ENTRY_POINTS:
            errors.append(f"entry_points.{key}: unknown name")
    if "prove" in value:
        prove = value["prove"]
        if not isinstance(prove, dict):
            errors.append("entry_points.prove: must be an object")
        else:
            for key in sorted(prove):
                if key != "argv":
                    errors.append(f"entry_points.prove.{key}: unknown name")
            prove_argv = _check_argv(
                errors, "entry_points.prove.argv", prove.get("argv"))
    if "build" in value:
        build = value["build"]
        if not isinstance(build, dict):
            errors.append("entry_points.build: must be an object")
        else:
            for key in sorted(build):
                if key != "steps":
                    errors.append(f"entry_points.build.{key}: unknown name")
            steps = build.get("steps")
            if not isinstance(steps, list) or not steps:
                errors.append(
                    "entry_points.build.steps: must be a non-empty array")
            else:
                collected = []
                for index, step in enumerate(steps):
                    where = f"entry_points.build.steps[{index}]"
                    if not isinstance(step, dict) \
                            or sorted(step) != ["argv"]:
                        errors.append(f"{where}: must be an object "
                                      "with exactly argv")
                        continue
                    argv = _check_argv(errors, f"{where}.argv", step["argv"])
                    if argv:
                        collected.append(argv)
                build_steps = tuple(collected)
    if "serve" in value:
        serve = _check_command(errors, "entry_points.serve", value["serve"])
    if "probe" in value:
        probe = _check_command(errors, "entry_points.probe", value["probe"])
    return prove_argv, build_steps, serve, probe


def _check_artifacts(errors, value):
    if not isinstance(value, list) or not value:
        errors.append("artifacts: must be a non-empty array")
        return ()
    collected = []
    for index, path in enumerate(value):
        where = f"artifacts[{index}]"
        if not isinstance(path, str) or not path:
            errors.append(f"{where}: must be a non-empty string")
            continue
        if path.startswith("/") or ".." in Path(path).parts:
            errors.append(f"{where}: must be relative and must not escape")
            continue
        collected.append(path)
    return tuple(collected)


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
    build_steps = ()
    serve = Command()
    probe = Command()
    if "entry_points" in root:
        prove_argv, build_steps, serve, probe = _check_entry_points(
            errors, root["entry_points"])

    artifacts = ()
    if "artifacts" in root:
        artifacts = _check_artifacts(errors, root["artifacts"])

    if errors:
        return None, errors
    return IntegrationDocument(
        integration=integration,
        kit=kit,
        repository=root["repository"],
        origin=origin,
        prove_argv=prove_argv,
        build_steps=build_steps,
        artifacts=artifacts,
        serve=serve,
        probe=probe,
    ), []


def load_integration(path):
    """Read and validate the leaf at path; returns (doc or None, errors)."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_integration_text(text)
