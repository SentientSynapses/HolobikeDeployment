"""The read-only preflight verb.

Preflight validates the environment mapping, then reports facts about every
integration in the roster: whether it is declared, whether its checkout
exists and is a git repository, its revision, branch, and dirty state — and
whether declared toolchains and expected PATH tools are present. It is safe
to run before anything is trusted, because it can change nothing: every
subprocess it spawns is a read-only git query.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import environment

# Tools every current workflow expects to resolve from PATH. Reported, never
# installed; absence is a fact, not a failure of preflight itself.
PATH_TOOLS = ("git", "cmake", "ninja", "node", "npm", "python3")


def _git(checkout, *arguments):
    result = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None, result.stderr.strip().splitlines()[0] if result.stderr else ""
    return result.stdout.strip(), ""


def _inspect_integration(name, document):
    facts = {"declared": name in document.checkouts}
    if not facts["declared"]:
        facts["status"] = "undeclared"
        return facts
    path = Path(document.checkouts[name])
    facts["path"] = str(path)
    if not path.is_dir():
        facts["status"] = "missing"
        return facts
    revision, error = _git(path, "rev-parse", "HEAD")
    if revision is None:
        # A directory with git metadata that git refuses (ownership,
        # corruption) is a different fact from a directory that never was a
        # repository — conflating them sends the operator hunting the wrong
        # problem.
        if (path / ".git").exists():
            facts["status"] = "unreadable_repository"
            facts["detail"] = error
        else:
            facts["status"] = "not_a_git_repository"
        return facts
    porcelain, _ = _git(path, "status", "--porcelain")
    branch, _ = _git(path, "rev-parse", "--abbrev-ref", "HEAD")
    facts["revision"] = revision
    facts["branch"] = branch or ""
    facts["dirty"] = bool(porcelain)
    facts["status"] = "dirty" if porcelain else "clean"
    return facts


def _inspect_toolchain(name, document):
    facts = {"declared": name in document.toolchains}
    if not facts["declared"]:
        facts["status"] = "undeclared"
        return facts
    path = Path(document.toolchains[name])
    facts["path"] = str(path)
    facts["status"] = "present" if path.is_dir() else "missing"
    return facts


def build_report(document):
    return {
        "generated_by": "holobike-assemble preflight",
        "integrations": {
            name: _inspect_integration(name, document)
            for name in environment.INTEGRATIONS
        },
        "toolchains": {
            name: _inspect_toolchain(name, document)
            for name in environment.TOOLCHAINS
        },
        "path_tools": {
            tool: shutil.which(tool) is not None for tool in PATH_TOOLS
        },
    }


def _problems(report):
    problems = []
    for name, facts in report["integrations"].items():
        if facts["status"] in (
                "missing", "not_a_git_repository", "unreadable_repository"):
            problems.append(f"{name}: {facts['status']}")
    for name, facts in report["toolchains"].items():
        if facts["status"] == "missing":
            problems.append(f"toolchain {name}: missing")
    return problems


def _print_table(report, stdout):
    rows = [("INTEGRATION", "STATUS", "REVISION", "BRANCH")]
    for name, facts in report["integrations"].items():
        rows.append((
            name,
            facts["status"],
            (facts.get("revision") or "-")[:12],
            facts.get("branch") or "-",
        ))
    widths = [max(len(row[column]) for row in rows) for column in range(4)]
    for row in rows:
        line = "  ".join(
            value.ljust(width) for value, width in zip(row, widths))
        print(line.rstrip(), file=stdout)
    for name, facts in report["toolchains"].items():
        print(f"toolchain {name}: {facts['status']}", file=stdout)
    missing_tools = sorted(
        tool for tool, found in report["path_tools"].items() if not found)
    if missing_tools:
        print("missing from PATH: " + ", ".join(missing_tools), file=stdout)


def run(environment_path, validate_only, as_json, stdout, stderr):
    """Execute preflight; returns the process exit code.

    0: report complete, every declared thing present.
    1: report complete, problems found (missing checkout or toolchain).
    2: the environment document was refused.
    """
    document, errors = environment.load_environment(environment_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    if validate_only:
        print(f"{environment_path}: valid", file=stdout)
        return 0

    report = build_report(document)
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True), file=stdout)
    else:
        _print_table(report, stdout)
    return 1 if _problems(report) else 0
