"""Strict validation for run records.

Canonical contract: Schemas/record.schema.json, held by the fixtures under
Conformance/record. The resolve verb validates every record through this
module before writing it — a tool that emits documents it would refuse to
read has no contract at all.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from . import document, filesystem
from .environment import INTEGRATIONS

SCHEMA_VERSION = 1
MAX_RECORD_BYTES = 4 * 1024 * 1024

_BASE_KEYS = ("schema_version", "kind", "run", "deployment", "line",
              "problems")
# Every kind carries the base plus exactly its own keys; a resolution with
# actions, or a bootstrap with gates, is a category error, not a tolerance.
_KIND_KEYS = {
    "resolution": ("resolved", "gates"),
    "bootstrap": ("actions",),
    "assembly": ("profile", "integrations", "resolution", "builds",
                 "artifacts", "bundle"),
    "emulation": ("profile", "integrations", "assembly", "members"),
    "release": ("version", "profile", "integrations", "chain",
                "attestation"),
}
_KIND_VERBS = {
    "resolution": "resolve",
    "bootstrap": "bootstrap",
    "assembly": "assemble",
    "emulation": "emulate",
    "release": "admit",
}
_VERSION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9.-]*$")
_CHAIN_KEYS = ("resolution", "assembly", "emulation")
_ATTESTATION_KEYS = ("gates", "builds", "selections", "emulation")
_MEMBER_KEYS = ("status", "run", "serve", "probe", "log", "shutdown",
                "detail")
_MEMBER_STATUSES = ("healthy", "skipped", "spawn_failed", "exited_early",
                    "never_ready", "failed_settle", "unclean_shutdown")
_RUN_MODES = ("host",)
_BUILD_KEYS = ("status", "steps", "detail")
_BUILD_STATUSES = ("built", "failed", "skipped", "invalidated")
_STEP_KEYS = ("argv", "exit", "log")
_ARTIFACT_KEYS = ("path", "sha256", "bytes")
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_RUN_KEYS = ("verb", "started_at_utc", "finished_at_utc")
_ACTION_KEYS = ("status", "detail", "revision_before", "revision_after")
_ACTION_STATUSES = (
    "cloned", "clone_failed", "updated", "up_to_date", "matched",
    "dirty_skipped", "selection_mismatch", "diverged", "fetch_failed",
    "unclonable", "unreadable_repository",
)
_RESOLUTION_KEYS = ("selected", "status", "revision", "branch", "dirty",
                    "detail")
_STATUSES = ("resolved", "selection_mismatch", "unresolvable")
_GATE_KEYS = ("kind", "status", "counts", "mismatches", "truncated",
              "detail")
_GATE_STATUSES = ("pass", "fail", "skipped")
_GATE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
_RECORD_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.json$")


def _require_string(errors, where, value, pattern=None, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value):
        errors.append(f"{where}: must be a non-empty string")
        return
    if pattern is not None and not pattern.fullmatch(value):
        errors.append(f"{where}: malformed")


def _require_relative_path(errors, where, value):
    try:
        filesystem.relative_parts(value)
    except filesystem.FilesystemContractError as error:
        errors.append(f"{where}: {error}")


def _check_record_reference(errors, where, value, extra_keys=()):
    allowed = ("record", "sha256") + tuple(extra_keys)
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return
    _check_closed_keys(errors, where, value, allowed)
    _require_string(
        errors, f"{where}.record", value.get("record"),
        _RECORD_NAME_PATTERN)
    _require_string(
        errors, f"{where}.sha256", value.get("sha256"), _SHA256_PATTERN)


def _check_closed_keys(errors, where, value, allowed):
    for key in sorted(value):
        if key not in allowed:
            errors.append(f"{where}.{key}: unknown name")


def _check_integrations(errors, value):
    if not isinstance(value, list) or not value:
        errors.append("integrations: must be a non-empty array")
        return None
    if any(name not in INTEGRATIONS for name in value):
        errors.append("integrations: contains an unknown roster name")
        return None
    if len(set(value)) != len(value):
        errors.append("integrations: entries must be unique")
        return None
    return tuple(value)


def _check_run(errors, value, expected_verb):
    if not isinstance(value, dict):
        errors.append("run: must be an object")
        return
    _check_closed_keys(errors, "run", value, _RUN_KEYS)
    if value.get("verb") != expected_verb:
        errors.append(f"run.verb: must be {expected_verb}")
    for key in ("started_at_utc", "finished_at_utc"):
        stamp = value.get(key)
        if not isinstance(stamp, str) or not stamp.endswith("Z"):
            errors.append(f"run.{key}: must be a UTC timestamp ending in Z")


def _check_action(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return
    _check_closed_keys(errors, where, value, _ACTION_KEYS)
    if value.get("status") not in _ACTION_STATUSES:
        errors.append(f"{where}.status: must be one of {_ACTION_STATUSES}")
    if "detail" in value:
        _require_string(errors, f"{where}.detail", value["detail"])
    for key in ("revision_before", "revision_after"):
        if key in value and not isinstance(value[key], str):
            errors.append(f"{where}.{key}: must be a string")


def _check_deployment(errors, value):
    if not isinstance(value, dict):
        errors.append("deployment: must be an object")
        return
    _check_closed_keys(errors, "deployment", value, ("revision", "dirty"))
    _require_string(
        errors, "deployment.revision", value.get("revision"),
        _COMMIT_PATTERN)
    if not isinstance(value.get("dirty"), bool):
        errors.append("deployment.dirty: must be a boolean")


def _check_selected(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return
    _check_closed_keys(errors, where, value, ("branch", "commit"))
    named = [key for key in ("branch", "commit") if key in value]
    if len(named) != 1:
        errors.append(f"{where}: exactly one of branch or commit")
        return
    if "branch" in value:
        _require_string(errors, f"{where}.branch", value["branch"])
    else:
        _require_string(
            errors, f"{where}.commit", value["commit"], _COMMIT_PATTERN)


def _check_resolution(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return
    _check_closed_keys(errors, where, value, _RESOLUTION_KEYS)
    if "selected" not in value:
        errors.append(f"{where}.selected: required")
    else:
        _check_selected(errors, f"{where}.selected", value["selected"])
    if value.get("status") not in _STATUSES:
        errors.append(f"{where}.status: must be one of {_STATUSES}")
    if "revision" in value:
        _require_string(
            errors, f"{where}.revision", value["revision"], _COMMIT_PATTERN)
    if "branch" in value and not isinstance(value["branch"], str):
        errors.append(f"{where}.branch: must be a string")
    if "dirty" in value and not isinstance(value["dirty"], bool):
        errors.append(f"{where}.dirty: must be a boolean")
    if "detail" in value:
        _require_string(errors, f"{where}.detail", value["detail"])
    if value.get("status") in ("resolved", "selection_mismatch"):
        for key in ("revision", "branch", "dirty"):
            if key not in value:
                errors.append(f"{where}.{key}: required for a readable checkout")


def _check_gate_verdict(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return
    _check_closed_keys(errors, where, value, _GATE_KEYS)
    if value.get("kind") != "tree_parity":
        errors.append(f"{where}.kind: must be tree_parity")
    if value.get("status") not in _GATE_STATUSES:
        errors.append(f"{where}.status: must be one of {_GATE_STATUSES}")
    if "counts" in value:
        counts = value["counts"]
        if not isinstance(counts, dict) or any(
                not isinstance(count, int) or isinstance(count, bool)
                or count < 0 for count in counts.values()):
            errors.append(f"{where}.counts: must map to whole numbers")
    if "mismatches" in value and (
            not isinstance(value["mismatches"], list) or any(
                not isinstance(item, str) or not item
                for item in value["mismatches"])):
        errors.append(f"{where}.mismatches: must be non-empty strings")
    if "truncated" in value and (
            isinstance(value["truncated"], bool)
            or not isinstance(value["truncated"], int)
            or value["truncated"] < 0):
        errors.append(f"{where}.truncated: must be a whole number")
    if "detail" in value:
        _require_string(errors, f"{where}.detail", value["detail"])


def _check_build(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return
    _check_closed_keys(errors, where, value, _BUILD_KEYS)
    if value.get("status") not in _BUILD_STATUSES:
        errors.append(f"{where}.status: must be one of {_BUILD_STATUSES}")
    steps = value.get("steps")
    if not isinstance(steps, list):
        errors.append(f"{where}.steps: required array")
    else:
        exits = []
        for index, step in enumerate(steps):
            step_where = f"{where}.steps[{index}]"
            if not isinstance(step, dict):
                errors.append(f"{step_where}: must be an object")
                continue
            _check_closed_keys(errors, step_where, step, _STEP_KEYS)
            argv = step.get("argv")
            if not isinstance(argv, list) or not argv or any(
                    not isinstance(item, str) or not item for item in argv):
                errors.append(f"{step_where}.argv: must be non-empty strings")
            code = step.get("exit")
            if isinstance(code, bool) or not isinstance(code, int):
                errors.append(f"{step_where}.exit: must be an integer")
            else:
                exits.append(code)
            _require_string(errors, f"{step_where}.log", step.get("log"))
            if isinstance(step.get("log"), str):
                _require_relative_path(
                    errors, f"{step_where}.log", step["log"])
        status = value.get("status")
        if status == "built" and (not exits or any(code != 0 for code in exits)):
            errors.append(
                f"{where}: built requires at least one successful step")
        if status == "failed" and not any(code != 0 for code in exits):
            errors.append(f"{where}: failed requires a failing step")
        if status == "skipped" and steps:
            errors.append(f"{where}: skipped must not carry executed steps")
        if status == "invalidated" and (
                not exits or any(code != 0 for code in exits)):
            errors.append(
                f"{where}: invalidated requires successful executed steps")
    if "detail" in value:
        _require_string(errors, f"{where}.detail", value["detail"])
    elif value.get("status") in ("skipped", "invalidated"):
        errors.append(f"{where}.detail: required for {value.get('status')}")


def _check_staged_artifacts(errors, where, value):
    if not isinstance(value, list):
        errors.append(f"{where}: must be an array")
        return
    for index, entry in enumerate(value):
        entry_where = f"{where}[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{entry_where}: must be an object")
            continue
        _check_closed_keys(errors, entry_where, entry, _ARTIFACT_KEYS)
        _require_string(errors, f"{entry_where}.path", entry.get("path"))
        if isinstance(entry.get("path"), str):
            _require_relative_path(
                errors, f"{entry_where}.path", entry["path"])
        _require_string(
            errors, f"{entry_where}.sha256", entry.get("sha256"),
            _SHA256_PATTERN)
        size = entry.get("bytes")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            errors.append(f"{entry_where}.bytes: must be a whole number")


def _check_member(errors, where, value):
    if not isinstance(value, dict):
        errors.append(f"{where}: must be an object")
        return
    _check_closed_keys(errors, where, value, _MEMBER_KEYS)
    if value.get("status") not in _MEMBER_STATUSES:
        errors.append(f"{where}.status: must be one of {_MEMBER_STATUSES}")
    if value.get("run") not in _RUN_MODES:
        errors.append(f"{where}.run: must be one of {_RUN_MODES}")
    if "serve" in value:
        serve = value["serve"]
        if not isinstance(serve, dict):
            errors.append(f"{where}.serve: must be an object")
        else:
            _check_closed_keys(
                errors, f"{where}.serve", serve, ("argv", "env"))
            argv = serve.get("argv")
            if not isinstance(argv, list) or not argv or any(
                    not isinstance(item, str) or not item for item in argv):
                errors.append(
                    f"{where}.serve.argv: must be non-empty strings")
            env = serve.get("env", {})
            if not isinstance(env, dict) or any(
                    not key or not isinstance(entry, str)
                    for key, entry in env.items()):
                errors.append(f"{where}.serve.env: must map names to strings")
    if "probe" in value:
        probe = value["probe"]
        if not isinstance(probe, dict):
            errors.append(f"{where}.probe: must be an object")
        else:
            _check_closed_keys(
                errors, f"{where}.probe", probe,
                ("attempts", "ready_after_ms"))
            attempts = probe.get("attempts")
            if isinstance(attempts, bool) or not isinstance(attempts, int) \
                    or attempts < 0:
                errors.append(
                    f"{where}.probe.attempts: must be a whole number")
            if "ready_after_ms" in probe:
                ready = probe["ready_after_ms"]
                if isinstance(ready, bool) or not isinstance(ready, int) \
                        or ready < 0:
                    errors.append(
                        f"{where}.probe.ready_after_ms: must be a whole "
                        "number")
    if "log" in value:
        _require_string(errors, f"{where}.log", value["log"])
        if isinstance(value["log"], str):
            _require_relative_path(errors, f"{where}.log", value["log"])
    if "shutdown" in value:
        shutdown = value["shutdown"]
        if not isinstance(shutdown, dict):
            errors.append(f"{where}.shutdown: must be an object")
        else:
            _check_closed_keys(
                errors, f"{where}.shutdown", shutdown, ("clean", "detail"))
            if not isinstance(shutdown.get("clean"), bool):
                errors.append(f"{where}.shutdown.clean: must be a boolean")
            if "detail" in shutdown:
                _require_string(
                    errors, f"{where}.shutdown.detail", shutdown["detail"])
    if "detail" in value:
        _require_string(errors, f"{where}.detail", value["detail"])


def validate_record_text(text):
    """Validate one record; returns (parsed dict or None, errors)."""
    errors = []
    try:
        root = document.loads(text)
    except document.JsonDocumentError as error:
        return None, [f"document: not valid JSON ({error})"]
    if not isinstance(root, dict):
        return None, ["document: the root must be an object"]

    kind = root.get("kind")
    if kind not in _KIND_KEYS:
        return None, [f"kind: must be one of {tuple(_KIND_KEYS)}"]

    allowed = _BASE_KEYS + _KIND_KEYS[kind]
    _check_closed_keys(errors, "document", root, allowed)
    for key in allowed:
        if key not in root:
            errors.append(f"{key}: required")
    if errors:
        return None, errors

    version = root["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) \
            or version != SCHEMA_VERSION:
        errors.append(f"schema_version: must be the integer {SCHEMA_VERSION}")
    _check_run(errors, root["run"], _KIND_VERBS[kind])
    _check_deployment(errors, root["deployment"])
    _require_string(errors, "line", root["line"])

    if kind == "resolution":
        resolved = root["resolved"]
        if not isinstance(resolved, dict) or not resolved:
            errors.append("resolved: must be a non-empty object")
        else:
            for name in sorted(resolved):
                if name not in INTEGRATIONS:
                    errors.append(
                        f"resolved.{name}: unknown name — the roster is "
                        "closed")
                    continue
                _check_resolution(errors, f"resolved.{name}", resolved[name])

        gate_verdicts = root["gates"]
        if not isinstance(gate_verdicts, dict):
            errors.append("gates: must be an object")
        else:
            for name in sorted(gate_verdicts):
                if not _GATE_NAME_PATTERN.fullmatch(name):
                    errors.append(f"gates.{name}: malformed gate name")
                    continue
                _check_gate_verdict(
                    errors, f"gates.{name}", gate_verdicts[name])

    if kind == "bootstrap":
        actions = root["actions"]
        if not isinstance(actions, dict) or not actions:
            errors.append("actions: must be a non-empty object")
        else:
            for name in sorted(actions):
                if name not in INTEGRATIONS:
                    errors.append(
                        f"actions.{name}: unknown name — the roster is "
                        "closed")
                    continue
                _check_action(errors, f"actions.{name}", actions[name])

    if kind == "assembly":
        profile = root["profile"]
        if not isinstance(profile, str) \
                or not _SLUG_PATTERN.fullmatch(profile):
            errors.append("profile: must match ^[a-z0-9][a-z0-9-]*$")
        integrations = _check_integrations(errors, root["integrations"])
        resolution = root["resolution"]
        _check_record_reference(errors, "resolution", resolution, ("line",))
        if isinstance(resolution, dict):
            _require_string(errors, "resolution.line", resolution.get("line"))
        builds = root["builds"]
        if not isinstance(builds, dict) or not builds:
            errors.append("builds: must be a non-empty object")
        else:
            for name in sorted(builds):
                if name not in INTEGRATIONS:
                    errors.append(
                        f"builds.{name}: unknown name — the roster is "
                        "closed")
                    continue
                _check_build(errors, f"builds.{name}", builds[name])
            if integrations is not None and set(builds) != set(integrations):
                errors.append(
                    "builds: keys must exactly match the recorded integrations")
        staged = root["artifacts"]
        if not isinstance(staged, dict):
            errors.append("artifacts: must be an object")
        else:
            for name in sorted(staged):
                if name not in INTEGRATIONS:
                    errors.append(
                        f"artifacts.{name}: unknown name — the roster is "
                        "closed")
                    continue
                _check_staged_artifacts(
                    errors, f"artifacts.{name}", staged[name])
        _require_relative_path(errors, "bundle", root["bundle"])

    if kind == "release":
        version = root["version"]
        if not isinstance(version, str) \
                or not _VERSION_PATTERN.fullmatch(version):
            errors.append("version: must match ^[a-z0-9][a-z0-9.-]*$")
        profile = root["profile"]
        if not isinstance(profile, str) \
                or not _SLUG_PATTERN.fullmatch(profile):
            errors.append("profile: must match ^[a-z0-9][a-z0-9-]*$")
        _check_integrations(errors, root["integrations"])
        chain = root["chain"]
        if not isinstance(chain, dict):
            errors.append("chain: must be an object")
        else:
            _check_closed_keys(errors, "chain", chain, _CHAIN_KEYS)
            for key in _CHAIN_KEYS:
                if key not in chain:
                    errors.append(f"chain.{key}: required")
            _check_record_reference(
                errors, "chain.resolution", chain.get("resolution"))
            _check_record_reference(
                errors, "chain.assembly", chain.get("assembly"))
            # emulation is nullable: a release may be admitted un-emulated,
            # and the attestation says so honestly.
            if chain.get("emulation") is not None:
                _check_record_reference(
                    errors, "chain.emulation", chain.get("emulation"))
        attestation = root["attestation"]
        if not isinstance(attestation, dict):
            errors.append("attestation: must be an object")
        else:
            _check_closed_keys(
                errors, "attestation", attestation, _ATTESTATION_KEYS)
            for key in ("gates", "builds", "selections"):
                if attestation.get(key) != "pass":
                    errors.append(
                        f"attestation.{key}: an admitted release attests "
                        "pass")
            if attestation.get("emulation") not in ("healthy", "absent"):
                errors.append(
                    "attestation.emulation: must be healthy or absent")

    if kind == "emulation":
        profile = root["profile"]
        if not isinstance(profile, str) \
                or not _SLUG_PATTERN.fullmatch(profile):
            errors.append("profile: must match ^[a-z0-9][a-z0-9-]*$")
        integrations = _check_integrations(errors, root["integrations"])
        assembly = root["assembly"]
        _check_record_reference(errors, "assembly", assembly, ("bundle",))
        if isinstance(assembly, dict):
            _require_relative_path(errors, "assembly.bundle",
                                   assembly.get("bundle"))
        members = root["members"]
        if not isinstance(members, dict) or not members:
            errors.append("members: must be a non-empty object")
        else:
            for name in sorted(members):
                if name not in INTEGRATIONS:
                    errors.append(
                        f"members.{name}: unknown name — the roster is "
                        "closed")
                    continue
                _check_member(errors, f"members.{name}", members[name])
            if integrations is not None and set(members) != set(integrations):
                errors.append(
                    "members: keys must exactly match the recorded integrations")

    problems = root["problems"]
    if not isinstance(problems, list) or any(
            not isinstance(item, str) or not item for item in problems):
        errors.append("problems: must be an array of non-empty strings")

    if errors:
        return None, errors
    return root, []


def load_record(path):
    root, _, _, errors = load_record_snapshot(path)
    return root, errors


def load_record_snapshot(path):
    """Return one parsed record, its exact text and digest, or errors."""
    try:
        content = filesystem.read_file_snapshot(
            Path(path), max_bytes=MAX_RECORD_BYTES)
        text = content.decode("utf-8")
    except (OSError, UnicodeError,
            filesystem.FilesystemContractError) as error:
        return None, None, None, [f"document: unreadable: {error}"]
    root, errors = validate_record_text(text)
    if errors:
        return None, text, None, errors
    return root, text, hashlib.sha256(content).hexdigest(), []
