"""The resolve verb: pin a declaration.

Resolve reads a revision manifest, verifies each selected integration's
checkout against its selection, and writes a record of what actually is —
exact commits, dirty state, mismatches — into the untracked Artifacts/
directory. The record always states facts; refusing to promote a record
with problems is admission's job, not this verb's. Every record is
validated through the record contract before it is written: a tool that
emits documents it would refuse to read has no contract at all.
"""

from __future__ import annotations

import datetime
import json
from pathlib import Path

from . import environment
from . import filesystem
from . import gitfacts
from . import record as record_contract
from . import revisions as revisions_contract


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _selection_as_json(selection):
    if selection.branch:
        return {"branch": selection.branch}
    return {"commit": selection.commit}


def _resolve_one(name, selection, document):
    facts = {"selected": _selection_as_json(selection)}
    if name not in document.checkouts:
        facts["status"] = "unresolvable"
        facts["detail"] = "no checkout declared in the environment mapping"
        return facts
    checkout = Path(document.checkouts[name])
    revision, error = gitfacts.git_query(checkout, "rev-parse", "HEAD")
    if revision is None:
        facts["status"] = "unresolvable"
        facts["detail"] = error or "checkout is not a readable repository"
        return facts
    branch, _ = gitfacts.git_query(
        checkout, "rev-parse", "--abbrev-ref", "HEAD")
    porcelain, _ = gitfacts.git_query(checkout, "status", "--porcelain")
    facts["revision"] = revision
    facts["branch"] = branch or ""
    facts["dirty"] = bool(porcelain)

    if selection.branch:
        if branch == selection.branch:
            facts["status"] = "resolved"
        else:
            facts["status"] = "selection_mismatch"
            facts["detail"] = (
                f"selected branch {selection.branch}, checkout is on "
                f"{branch or 'no branch'}")
    else:
        if revision == selection.commit:
            facts["status"] = "resolved"
        else:
            facts["status"] = "selection_mismatch"
            facts["detail"] = (
                f"selected commit {selection.commit}, checkout is at "
                f"{revision}")
    return facts


def _deployment_identity(repo_root):
    revision, error = gitfacts.git_query(repo_root, "rev-parse", "HEAD")
    if revision is None:
        return None, error or "the deployment repository is unreadable"
    porcelain, _ = gitfacts.git_query(repo_root, "status", "--porcelain")
    return {"revision": revision, "dirty": bool(porcelain)}, ""


def run(revisions_path, environment_path, artifacts_root, repo_root,
        stdout, stderr, policy_root=None):
    """Execute resolve; returns the process exit code.

    0: record written, every selection resolved.
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
    deployment, error = _deployment_identity(repo_root)
    if deployment is None:
        print(f"deployment identity: {error}", file=stderr)
        return 2

    resolved = {
        name: _resolve_one(name, selection, document)
        for name, selection in sorted(manifest.selections.items())
    }
    problems = [
        f"{name}: {facts['status']} — {facts.get('detail', '')}".rstrip(" —")
        for name, facts in resolved.items()
        if facts["status"] != "resolved"
    ]

    body = {
        "schema_version": record_contract.SCHEMA_VERSION,
        "kind": "resolution",
        "run": {
            "verb": "resolve",
            "started_at_utc": started,
            "finished_at_utc": _utc_now(),
        },
        "deployment": deployment,
        "line": manifest.line,
        "resolved": resolved,
        "problems": problems,
    }

    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    _, errors = record_contract.validate_record_text(text)
    if errors:
        # The tool refusing its own output is the contract working; write
        # nothing and fail loudly.
        for error in errors:
            print(f"record self-validation: {error}", file=stderr)
        return 2

    # Microsecond stamp: two runs in the same second must not share a name —
    # a record that overwrites a record is an edit, and records are never
    # edited.
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ")
    records_root = Path(artifacts_root) / "records"
    record_path = records_root / f"resolve-{manifest.line}-{stamp}.json"
    filesystem.publish_text(record_path, text)

    print(f"record: {record_path}", file=stdout)
    for problem in problems:
        print(f"problem: {problem}", file=stdout)
    print(
        f"resolved {sum(1 for f in resolved.values() if f['status'] == 'resolved')}"
        f"/{len(resolved)} selections on line {manifest.line}",
        file=stdout)
    return 1 if problems else 0
