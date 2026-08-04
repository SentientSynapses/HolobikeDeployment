"""Strict validation for run records.

Canonical contract: Schemas/record.schema.json, held by the fixtures under
Conformance/record. The resolve verb validates every record through this
module before writing it — a tool that emits documents it would refuse to
read has no contract at all.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from .environment import INTEGRATIONS

SCHEMA_VERSION = 1

_ROOT_KEYS = ("schema_version", "kind", "run", "deployment", "line",
              "resolved", "gates", "problems")
_RUN_KEYS = ("verb", "started_at_utc", "finished_at_utc")
_RESOLUTION_KEYS = ("selected", "status", "revision", "branch", "dirty",
                    "detail")
_STATUSES = ("resolved", "selection_mismatch", "unresolvable")
_GATE_KEYS = ("kind", "status", "counts", "mismatches", "truncated",
              "detail")
_GATE_STATUSES = ("pass", "fail", "skipped")
_GATE_NAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def _require_string(errors, where, value, pattern=None, allow_empty=False):
    if not isinstance(value, str) or (not allow_empty and not value):
        errors.append(f"{where}: must be a non-empty string")
        return
    if pattern is not None and not pattern.fullmatch(value):
        errors.append(f"{where}: malformed")


def _check_closed_keys(errors, where, value, allowed):
    for key in sorted(value):
        if key not in allowed:
            errors.append(f"{where}.{key}: unknown name")


def _check_run(errors, value):
    if not isinstance(value, dict):
        errors.append("run: must be an object")
        return
    _check_closed_keys(errors, "run", value, _RUN_KEYS)
    if value.get("verb") != "resolve":
        errors.append("run.verb: must be resolve")
    for key in ("started_at_utc", "finished_at_utc"):
        stamp = value.get(key)
        if not isinstance(stamp, str) or not stamp.endswith("Z"):
            errors.append(f"run.{key}: must be a UTC timestamp ending in Z")


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


def validate_record_text(text):
    """Validate one record; returns (parsed dict or None, errors)."""
    errors = []
    try:
        root = json.loads(text)
    except json.JSONDecodeError as error:
        return None, [
            f"document: not valid JSON ({error.msg}, line {error.lineno})"]
    if not isinstance(root, dict):
        return None, ["document: the root must be an object"]

    _check_closed_keys(errors, "document", root, _ROOT_KEYS)
    for key in _ROOT_KEYS:
        if key not in root:
            errors.append(f"{key}: required")
    if errors:
        return None, errors

    version = root["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int) \
            or version != SCHEMA_VERSION:
        errors.append(f"schema_version: must be the integer {SCHEMA_VERSION}")
    if root["kind"] != "resolution":
        errors.append("kind: must be resolution")
    _check_run(errors, root["run"])
    _check_deployment(errors, root["deployment"])
    _require_string(errors, "line", root["line"])

    resolved = root["resolved"]
    if not isinstance(resolved, dict) or not resolved:
        errors.append("resolved: must be a non-empty object")
    else:
        for name in sorted(resolved):
            if name not in INTEGRATIONS:
                errors.append(
                    f"resolved.{name}: unknown name — the roster is closed")
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

    problems = root["problems"]
    if not isinstance(problems, list) or any(
            not isinstance(item, str) or not item for item in problems):
        errors.append("problems: must be an array of non-empty strings")

    if errors:
        return None, errors
    return root, []


def load_record(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as error:
        return None, [f"document: unreadable: {error}"]
    return validate_record_text(text)
