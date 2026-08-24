"""The bootstrap verb: materialize the environment.

Bootstrap's mutations are bounded and enumerable: it clones a missing
checkout from its Stack-declared origin, and it fast-forwards a clean
checkout that is already on its selected branch. Nothing else. A dirty
tree, a diverged branch, a checkout on the wrong branch — all reported,
never reset, never switched. System-level tools are preflight's to report
and nobody's to install. Every run writes a bootstrap record.
"""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path

from . import environment
from . import filesystem
from . import gitfacts
from . import record as record_contract
from . import revisions as revisions_contract
from . import stack as stack_contract

PROBLEM_STATUSES = (
    "clone_failed", "dirty_skipped", "selection_mismatch", "diverged",
    "fetch_failed", "unclonable", "unreadable_repository",
)


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _git_mutate(*arguments, cwd=None):
    """One bounded git mutation; returns (ok, first stderr line)."""
    result = subprocess.run(
        ["git", *arguments],
        capture_output=True,
        text=True,
        check=False,
        cwd=cwd,
    )
    first = result.stderr.strip().splitlines()[0] if result.stderr else ""
    return result.returncode == 0, first


def _load_origins(stack_root, stderr):
    """Map integration name -> declared origin; None on refused leaves."""
    leaves, errors = stack_contract.load_stack(stack_root)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return None
    return {name: document.origin for name, document in leaves.items()}


def _clone(selection, origin, path):
    action = {}
    if not origin:
        action["status"] = "unclonable"
        action["detail"] = "no origin declared in the Stack leaf"
        return action
    arguments = ["clone", "--quiet"]
    if selection.branch:
        arguments += ["--branch", selection.branch]
    arguments += ["--", origin, str(path)]
    ok, error = _git_mutate(*arguments)
    if not ok:
        action["status"] = "clone_failed"
        action["detail"] = error or "git clone failed"
        return action
    revision, _ = gitfacts.git_query(path, "rev-parse", "HEAD")
    action["revision_after"] = revision or ""
    if selection.commit and revision != selection.commit:
        action["status"] = "selection_mismatch"
        action["detail"] = (
            f"cloned default branch at {revision}, selection wants "
            f"{selection.commit}")
    else:
        action["status"] = "cloned"
    return action


def _update(selection, path):
    action = {}
    revision, error = gitfacts.git_query(path, "rev-parse", "HEAD")
    if revision is None:
        action["status"] = "unreadable_repository"
        action["detail"] = error
        return action
    action["revision_before"] = revision
    porcelain, _ = gitfacts.git_query(path, "status", "--porcelain")
    if porcelain:
        action["status"] = "dirty_skipped"
        action["detail"] = "working tree is dirty; bootstrap never resets"
        return action

    if selection.commit:
        if revision == selection.commit:
            action["status"] = "matched"
        else:
            action["status"] = "selection_mismatch"
            action["detail"] = (
                f"selection wants {selection.commit}, checkout is at "
                f"{revision}; bootstrap does not move commit selections")
        return action

    branch, _ = gitfacts.git_query(path, "rev-parse", "--abbrev-ref", "HEAD")
    if branch != selection.branch:
        action["status"] = "selection_mismatch"
        action["detail"] = (
            f"selection wants branch {selection.branch}, checkout is on "
            f"{branch or 'no branch'}; bootstrap never switches branches")
        return action

    ok, error = _git_mutate(
        "fetch", "--quiet", "origin", selection.branch, cwd=path)
    if not ok:
        action["status"] = "fetch_failed"
        action["detail"] = error or "git fetch failed"
        return action
    ok, error = _git_mutate("merge", "--ff-only", "FETCH_HEAD", cwd=path)
    if not ok:
        action["status"] = "diverged"
        action["detail"] = error or "fast-forward was not possible"
        return action
    after, _ = gitfacts.git_query(path, "rev-parse", "HEAD")
    action["revision_after"] = after or ""
    action["status"] = "up_to_date" if after == revision else "updated"
    return action


def _bootstrap_one(name, selection, document, origins):
    if name not in document.checkouts:
        return {
            "status": "unclonable",
            "detail": "no checkout path declared in the environment mapping",
        }
    path = Path(document.checkouts[name])
    if not path.exists():
        return _clone(selection, origins.get(name, ""), path)
    return _update(selection, path)


def run(revisions_path, environment_path, stack_root, artifacts_root,
        repo_root, stdout, stderr):
    """Execute bootstrap; returns the process exit code.

    0: record written, every selection materialized or already current.
    1: record written, problems inside it.
    2: an input was refused (or the record could not be written).
    """
    started = _utc_now()

    document, errors = environment.load_environment(environment_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    manifest, errors = revisions_contract.load_revisions(revisions_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    origins = _load_origins(stack_root, stderr)
    if origins is None:
        return 2

    deployment_revision, error = gitfacts.git_query(
        repo_root, "rev-parse", "HEAD")
    if deployment_revision is None:
        print(f"deployment identity: {error}", file=stderr)
        return 2
    porcelain, _ = gitfacts.git_query(repo_root, "status", "--porcelain")

    actions = {
        name: _bootstrap_one(name, selection, document, origins)
        for name, selection in sorted(manifest.selections.items())
    }
    problems = [
        f"{name}: {action['status']} — {action.get('detail', '')}"
        .rstrip(" —")
        for name, action in actions.items()
        if action["status"] in PROBLEM_STATUSES
    ]

    body = {
        "schema_version": record_contract.SCHEMA_VERSION,
        "kind": "bootstrap",
        "run": {
            "verb": "bootstrap",
            **environment.producer(document),
            "started_at_utc": started,
            "finished_at_utc": _utc_now(),
        },
        "deployment": {
            "revision": deployment_revision,
            "dirty": bool(porcelain),
        },
        "line": manifest.line,
        "actions": actions,
        "problems": problems,
    }
    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    _, errors = record_contract.validate_record_text(text)
    if errors:
        for error in errors:
            print(f"record self-validation: {error}", file=stderr)
        return 2

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ")
    records_root = Path(artifacts_root) / "records"
    record_path = records_root / f"bootstrap-{manifest.line}-{stamp}.json"
    filesystem.publish_text(record_path, text)

    print(f"record: {record_path}", file=stdout)
    for name, action in sorted(actions.items()):
        print(f"{name}: {action['status']}", file=stdout)
    for problem in problems:
        print(f"problem: {problem}", file=stdout)
    return 1 if problems else 0
