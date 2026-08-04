"""The read-only preflight verb.

Preflight validates the environment mapping, then reports facts: every
roster integration's checkout state (revision, branch, dirty), every Stack
leaf's integration contract (present, valid, consistent with the checkout),
declared toolchains, and expected PATH tools. It is safe to run before
anything is trusted, because it can change nothing: every subprocess it
spawns is a read-only git query.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from . import environment
from . import integration as integration_contract

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


def _inspect_stack(stack_root, document):
    """Judge the Stack leaves against the roster, in both directions.

    Every roster integration must have exactly one valid leaf whose file
    agrees with its directory; every leaf found must belong to the roster.
    The leaf's repository name is cross-checked against the declared
    checkout's directory name, so the contract and the workstation cannot
    quietly disagree about what a checkout is called.
    """
    found = {}
    strays = []
    stack = Path(stack_root)
    for leaf_path in sorted(stack.glob("**/integration.json")):
        leaf_directory = leaf_path.parent.name
        document_leaf, errors = integration_contract.load_integration(
            leaf_path)
        if document_leaf is None:
            entry = {
                "status": "invalid",
                "path": str(leaf_path),
                "errors": errors,
            }
            if leaf_directory in environment.INTEGRATIONS:
                found.setdefault(leaf_directory, []).append(entry)
            else:
                strays.append(entry)
            continue
        entry = {
            "status": "ok",
            "path": str(leaf_path),
            "repository": document_leaf.repository,
            "prove_declared": bool(document_leaf.prove_argv),
        }
        if document_leaf.integration != leaf_directory:
            entry["status"] = "name_mismatch"
            entry["detail"] = (
                f"the file says {document_leaf.integration}, "
                f"the directory is {leaf_directory}")
        found.setdefault(document_leaf.integration, []).append(entry)

    leaves = {}
    for name in environment.INTEGRATIONS:
        entries = found.get(name, [])
        if not entries:
            leaves[name] = {"status": "leaf_missing"}
        elif len(entries) > 1:
            leaves[name] = {
                "status": "duplicate",
                "paths": [entry["path"] for entry in entries],
            }
        else:
            entry = entries[0]
            if entry["status"] == "ok" and name in document.checkouts:
                checkout_name = Path(document.checkouts[name]).name
                if checkout_name != entry["repository"]:
                    entry["status"] = "checkout_repository_mismatch"
                    entry["detail"] = (
                        f"the leaf says {entry['repository']}, the declared "
                        f"checkout is {checkout_name}")
            leaves[name] = entry
    return leaves, strays


def build_report(document, stack_root):
    leaves, strays = _inspect_stack(stack_root, document)
    return {
        "generated_by": "holobike-assemble preflight",
        "integrations": {
            name: _inspect_integration(name, document)
            for name in environment.INTEGRATIONS
        },
        "stack": leaves,
        "stack_strays": strays,
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
    for name, facts in report["stack"].items():
        if facts["status"] != "ok":
            problems.append(f"stack {name}: {facts['status']}")
    for stray in report["stack_strays"]:
        problems.append(f"stack stray: {stray['path']}")
    for name, facts in report["toolchains"].items():
        if facts["status"] == "missing":
            problems.append(f"toolchain {name}: missing")
    return problems


def _print_table(report, stdout):
    rows = [("INTEGRATION", "STATUS", "LEAF", "REVISION", "BRANCH")]
    for name, facts in report["integrations"].items():
        rows.append((
            name,
            facts["status"],
            report["stack"][name]["status"],
            (facts.get("revision") or "-")[:12],
            facts.get("branch") or "-",
        ))
    widths = [
        max(len(row[column]) for row in rows)
        for column in range(len(rows[0]))
    ]
    for row in rows:
        line = "  ".join(
            value.ljust(width) for value, width in zip(row, widths))
        print(line.rstrip(), file=stdout)
    for stray in report["stack_strays"]:
        print(f"stack stray: {stray['path']}", file=stdout)
    for name, facts in report["toolchains"].items():
        print(f"toolchain {name}: {facts['status']}", file=stdout)
    missing_tools = sorted(
        tool for tool, found in report["path_tools"].items() if not found)
    if missing_tools:
        print("missing from PATH: " + ", ".join(missing_tools), file=stdout)


def _judge_only(loader, path, stdout, stderr):
    _, errors = loader(path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    print(f"{path}: valid", file=stdout)
    return 0


def run(environment_path, stack_root, validate_only, validate_integration,
        as_json, stdout, stderr):
    """Execute preflight; returns the process exit code.

    0: report complete, every declared thing present and consistent.
    1: report complete, problems found.
    2: a judged document was refused.
    """
    if validate_integration is not None:
        return _judge_only(
            integration_contract.load_integration,
            validate_integration, stdout, stderr)

    document, errors = environment.load_environment(environment_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    if validate_only:
        print(f"{environment_path}: valid", file=stdout)
        return 0

    report = build_report(document, stack_root)
    if as_json:
        print(json.dumps(report, indent=2, sort_keys=True), file=stdout)
    else:
        _print_table(report, stdout)
    return 1 if _problems(report) else 0
