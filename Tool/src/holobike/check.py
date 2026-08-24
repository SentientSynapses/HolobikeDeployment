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
from pathlib import Path

from . import environment
from . import gitfacts
from . import integration as integration_contract
from . import nonmembers as nonmembers_contract
from . import stack as stack_contract

# Tools every current workflow expects to resolve from PATH. Reported, never
# installed; absence is a fact, not a failure of preflight itself.
PATH_TOOLS = ("git", "cmake", "ninja", "node", "npm", "python3")


_git = gitfacts.git_query


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


def _engine_version(root):
    """The engine's own Major.Minor, read from Engine/Build/Build.version.

    Read rather than parsed out of the directory name: a checkout can be
    renamed, moved, or symlinked, and a check that trusted the folder would
    then confirm exactly the thing it was built to catch.
    """
    try:
        text = (Path(root) / "Engine" / "Build" / "Build.version").read_text(
            encoding="utf-8")
        build = json.loads(text)
        return f"{build['MajorVersion']}.{build['MinorVersion']}"
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _inspect_toolchain(name, document):
    facts = {"declared": name in document.toolchains}
    if not facts["declared"]:
        facts["status"] = "undeclared"
        return facts
    path = Path(document.toolchains[name])
    facts["path"] = str(path)
    facts["status"] = "present" if path.is_dir() else "missing"
    if name == "unreal_engine" and facts["status"] == "present":
        facts["version"] = _engine_version(path)
    return facts


def _inspect_engine_association(document, leaves, toolchains):
    """Hold every declared .uproject against the declared engine.

    Both halves of this were previously unstated. The environment names an
    engine directory and preflight only asked whether that directory exists —
    and a workstation carrying two engines answers "present" to either, so a
    mapping that named the wrong one read as healthy. Meanwhile the project's
    own EngineAssociation is the thing that actually decides what gets built.
    Agreement between the two is the fact worth reporting; either alone is not.
    """
    engine = toolchains.get("unreal_engine", {})
    associations = {}
    for name, leaf in sorted(leaves.items()):
        project = leaf.get("unreal_project")
        if not project:
            continue
        facts = {"project": project}
        associations[name] = facts
        if name not in document.checkouts:
            facts["status"] = "checkout_undeclared"
            continue
        path = Path(document.checkouts[name]) / project
        try:
            declared = json.loads(path.read_text(encoding="utf-8"))
            facts["engine_association"] = str(declared["EngineAssociation"])
        except (OSError, ValueError, KeyError, TypeError):
            facts["status"] = "project_unreadable"
            continue
        if engine.get("status") != "present":
            facts["status"] = "engine_unavailable"
            continue
        facts["engine_version"] = engine.get("version")
        if facts["engine_version"] is None:
            facts["status"] = "engine_unversioned"
        elif facts["engine_version"] == facts["engine_association"]:
            facts["status"] = "agrees"
        else:
            facts["status"] = "engine_mismatch"
    return associations


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
    for leaf_path in stack_contract.leaves(stack):
        leaf_directory = leaf_path.stem
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
        if document_leaf.unreal_project:
            entry["unreal_project"] = document_leaf.unreal_project
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


def _inspect_roster_closure(stack_root, document, leaves):
    """Every adjacent checkout is a member, a declared non-member, or a
    problem with a name. Absent the declaration this reports nothing rather
    than reporting everything: the loop is closed by a document, not assumed.
    """
    declaration = Path(stack_root) / nonmembers_contract.FILENAME
    if not declaration.exists():
        return {"status": "undeclared",
                "detail": f"{declaration} is absent, so nothing is scanned"}
    declared, errors = nonmembers_contract.load_nonmembers(declaration)
    if errors:
        return {"status": "invalid", "errors": errors}
    members = {entry.get("repository") for entry in leaves.values()
               if entry.get("repository")}
    strays = nonmembers_contract.scan(
        nonmembers_contract.search_roots(document.checkouts),
        members, set(declared))
    return {
        "status": "clean" if not strays else "unenrolled_repository",
        "declared": len(declared),
        "candidates": sorted(
            name for name, entry in declared.items() if entry.get("candidate")),
        "strays": strays,
    }


def build_report(document, stack_root):
    leaves, strays = _inspect_stack(stack_root, document)
    toolchains = {
        name: _inspect_toolchain(name, document)
        for name in environment.TOOLCHAINS
    }
    return {
        "generated_by": "holobike check",
        "host": {"host": document.host, "os": document.os},
        "integrations": {
            name: _inspect_integration(name, document)
            for name in environment.INTEGRATIONS
        },
        "stack": leaves,
        "stack_strays": strays,
        "roster_closure": _inspect_roster_closure(stack_root, document, leaves),
        "toolchains": toolchains,
        "engine_associations": _inspect_engine_association(
            document, leaves, toolchains),
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
    closure = report.get("roster_closure", {})
    if closure.get("status") == "invalid":
        problems.extend(f"nonmembers: {error}"
                        for error in closure.get("errors", []))
    for stray in closure.get("strays", ()):
        # In neither the roster nor nonmembers.json. A named problem, which
        # is the whole reason the declaration exists.
        problems.append(f"unenrolled_repository: {stray['path']}")
    for name, facts in report["toolchains"].items():
        if facts["status"] == "missing":
            problems.append(f"toolchain {name}: missing")
    for name, facts in report["engine_associations"].items():
        if facts["status"] == "engine_mismatch":
            problems.append(
                f"{name}: the project asks for engine "
                f"{facts['engine_association']}, the declared toolchain is "
                f"{facts['engine_version']}")
        elif facts["status"] != "agrees":
            problems.append(f"{name}: engine association {facts['status']}")
    return problems


def _print_table(report, stdout):
    identity = report.get("host") or {}
    if identity.get("host"):
        print(f"host: {identity['host']} ({identity['os']})", file=stdout)
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
        version = facts.get("version")
        suffix = f" ({version})" if version else ""
        print(f"toolchain {name}: {facts['status']}{suffix}", file=stdout)
    for name, facts in report["engine_associations"].items():
        detail = facts["status"]
        if facts["status"] in ("agrees", "engine_mismatch"):
            detail = (f"{facts['status']} — project {facts['engine_association']}, "
                      f"toolchain {facts['engine_version']}")
        print(f"engine {name}: {detail}", file=stdout)
    identity = report.get("host", {})
    if identity:
        print(f"host: {identity['host']} ({identity['os']})", file=stdout)
    closure = report.get("roster_closure", {})
    if closure.get("status") == "clean":
        line = f"roster: closed — {closure['declared']} declared non-members"
        if closure.get("candidates"):
            line += (", " + str(len(closure["candidates"]))
                     + " awaiting a decision: "
                     + ", ".join(closure["candidates"]))
        print(line, file=stdout)
    elif closure.get("status") == "unenrolled_repository":
        for stray in closure["strays"]:
            print(f"unenrolled repository: {stray['path']} — enrol it or "
                  "record it in Stack/nonmembers.json with a reason",
                  file=stdout)
    elif closure.get("status") == "invalid":
        print("roster: nonmembers.json is invalid", file=stdout)
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
        as_json, stdout, stderr, validate_nonmembers=None):
    """Execute preflight; returns the process exit code.

    0: report complete, every declared thing present and consistent.
    1: report complete, problems found.
    2: a judged document was refused.
    """
    if validate_integration is not None:
        return _judge_only(
            integration_contract.load_integration,
            validate_integration, stdout, stderr)
    if validate_nonmembers is not None:
        return _judge_only(
            nonmembers_contract.load_nonmembers,
            validate_nonmembers, stdout, stderr)

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
