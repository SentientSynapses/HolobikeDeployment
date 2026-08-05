"""The assemble verb: stage a product bundle.

Assemble consumes a resolution record and a profile, invokes each member
integration's repository-owned build steps, and stages its declared
artifacts — digested, sized, and inventoried — into a bundle under the
untracked Artifacts/ directory. Repository-owned build tools may produce
ignored outputs in their own checkout; assemble verifies the exact clean
source identity both before and after every build and refuses to stage from
one that changed. Every run writes an assembly record that names and digests
the resolution it built from.
"""

from __future__ import annotations

import datetime
import json
import subprocess
from pathlib import Path

from . import environment
from . import filesystem
from . import gitfacts
from . import profiles as profiles_contract
from . import record as record_contract
from . import stack as stack_contract


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _load_leaves(stack_root, stderr):
    leaves, errors = stack_contract.load_stack(stack_root)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return None
    return leaves


def _source_problem(name, checkout, resolution):
    facts = resolution["resolved"].get(name)
    if facts is None:
        return f"{name}: absent from the resolution record"
    if facts["status"] != "resolved":
        return f"{name}: resolution status is {facts['status']}"
    if facts.get("dirty"):
        return f"{name}: resolution captured a dirty source checkout"
    expected = facts.get("revision")
    actual, error = gitfacts.git_query(checkout, "rev-parse", "HEAD")
    if actual is None:
        return f"{name}: source checkout is unreadable: {error}"
    if actual != expected:
        return f"{name}: source moved from resolved revision {expected} to {actual}"
    porcelain, error = gitfacts.git_query(checkout, "status", "--porcelain")
    if porcelain is None:
        return f"{name}: source status is unreadable: {error}"
    if porcelain:
        return f"{name}: source checkout became dirty after resolution"
    return ""


def _run_steps(name, steps, checkout, logs_root, bundle_root):
    """Run one integration's build steps; returns (facts, problems)."""
    facts = {"steps": []}
    problems = []
    for index, argv in enumerate(steps):
        log_path = logs_root / f"{name}-step{index}.log"
        with filesystem.open_private_output(log_path) as log:
            completed = subprocess.run(
                list(argv), cwd=checkout, stdout=log,
                stderr=subprocess.STDOUT, check=False)
        facts["steps"].append({
            "argv": list(argv),
            "exit": completed.returncode,
            "log": str(log_path.relative_to(bundle_root)),
        })
        if completed.returncode != 0:
            facts["status"] = "failed"
            problems.append(
                f"{name}: build step {index} exited "
                f"{completed.returncode} ({' '.join(argv)})")
            return facts, problems
    facts["status"] = "built"
    return facts, problems


def _stage_artifacts(name, leaf, checkout, bundle_root):
    """Copy declared artifacts into the bundle; returns (entries, problems)."""
    entries = []
    problems = []
    if not leaf.artifacts:
        problems.append(f"{name}: built, but no artifacts are declared")
        return entries, problems
    destination_root = bundle_root / name
    destination_root.mkdir(parents=True, exist_ok=True)
    staged_names = set()
    for relative in leaf.artifacts:
        try:
            source = filesystem.resolve_beneath(
                checkout, relative, kind="file")
        except (OSError, filesystem.FilesystemContractError) as error:
            problems.append(
                f"{name}: declared artifact unavailable: {relative}: {error}")
            continue
        base = Path(relative).name
        if base in staged_names:
            problems.append(
                f"{name}: artifact name collision in bundle: {base}")
            continue
        staged_names.add(base)
        destination = destination_root / base
        try:
            digest, byte_count = filesystem.copy_file_snapshot(
                source, destination)
        except (OSError, filesystem.FilesystemContractError) as error:
            problems.append(
                f"{name}: artifact changed or could not be staged: "
                f"{relative}: {error}")
            continue
        entries.append({
            "path": str(destination.relative_to(bundle_root)),
            "sha256": digest,
            "bytes": byte_count,
        })
    return entries, problems


def run(profile_path, record_path, environment_path, stack_root,
        artifacts_root, repo_root, stdout, stderr):
    """Execute assemble; returns the process exit code.

    0: bundle staged, every member built and every artifact staged.
    1: bundle staged, problems inside the record.
    2: an input was refused (or the record could not be written).
    """
    started = _utc_now()

    profile, errors = profiles_contract.load_profile(profile_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    records_root = Path(artifacts_root) / "records"
    try:
        resolution_path = filesystem.resolve_direct_child(
            records_root, record_path)
    except (OSError, filesystem.FilesystemContractError) as error:
        print(f"resolution record: {error}", file=stderr)
        return 2
    resolution, _, resolution_digest, errors = \
        record_contract.load_record_snapshot(resolution_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    if resolution["kind"] != "resolution":
        print(
            f"{record_path}: assemble consumes a resolution record, "
            f"got kind {resolution['kind']}", file=stderr)
        return 2
    document, errors = environment.load_environment(environment_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    leaves = _load_leaves(stack_root, stderr)
    if leaves is None:
        return 2

    deployment_revision, error = gitfacts.git_query(
        repo_root, "rev-parse", "HEAD")
    if deployment_revision is None:
        print(f"deployment identity: {error}", file=stderr)
        return 2
    porcelain, _ = gitfacts.git_query(repo_root, "status", "--porcelain")

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y%m%dT%H%M%S%fZ")
    bundle_root = Path(artifacts_root) / "bundles" \
        / f"{profile.profile}-{stamp}"
    logs_root = bundle_root / "logs"
    logs_root.mkdir(parents=True, mode=0o700)
    logs_root.chmod(0o700)

    builds = {}
    staged = {}
    problems = []
    for name in profile.integrations:
        leaf = leaves.get(name)
        if leaf is None:
            builds[name] = {"status": "skipped", "steps": [],
                            "detail": "no Stack leaf found"}
            problems.append(f"{name}: skipped — no Stack leaf found")
            continue
        if name not in document.checkouts:
            builds[name] = {
                "status": "skipped", "steps": [],
                "detail": "no checkout declared in the environment mapping"}
            problems.append(f"{name}: skipped — no checkout declared")
            continue
        if not leaf.build_steps:
            builds[name] = {
                "status": "skipped", "steps": [],
                "detail": "no build entry point declared in the Stack leaf"}
            problems.append(
                f"{name}: skipped — no build entry point declared")
            continue
        checkout = Path(document.checkouts[name])
        source_problem = _source_problem(name, checkout, resolution)
        if source_problem:
            builds[name] = {
                "status": "skipped", "steps": [], "detail": source_problem}
            problems.append(source_problem)
            continue
        facts, step_problems = _run_steps(
            name, leaf.build_steps, checkout, logs_root, bundle_root)
        builds[name] = facts
        problems.extend(step_problems)
        if facts["status"] != "built":
            continue
        source_problem = _source_problem(name, checkout, resolution)
        if source_problem:
            facts["status"] = "invalidated"
            facts["detail"] = source_problem
            problems.append(source_problem)
            continue
        entries, staging_problems = _stage_artifacts(
            name, leaf, checkout, bundle_root)
        staged[name] = entries
        problems.extend(staging_problems)

    body = {
        "schema_version": record_contract.SCHEMA_VERSION,
        "kind": "assembly",
        "run": {
            "verb": "assemble",
            "started_at_utc": started,
            "finished_at_utc": _utc_now(),
        },
        "deployment": {
            "revision": deployment_revision,
            "dirty": bool(porcelain),
        },
        "line": resolution["line"],
        "profile": profile.profile,
        "integrations": list(profile.integrations),
        "resolution": {
            "record": resolution_path.name,
            "sha256": resolution_digest,
            "line": resolution["line"],
        },
        "builds": builds,
        "artifacts": staged,
        "bundle": str(bundle_root.relative_to(Path(artifacts_root))),
        "problems": problems,
    }
    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    _, errors = record_contract.validate_record_text(text)
    if errors:
        for error in errors:
            print(f"record self-validation: {error}", file=stderr)
        return 2

    record_file = records_root \
        / f"assemble-{profile.profile}-{stamp}.json"
    filesystem.publish_text(record_file, text)

    # The bundle carries its own record too, so a bundle directory is
    # self-describing when it travels.
    filesystem.publish_text(bundle_root / "assembly.json", text)

    print(f"bundle: {bundle_root}", file=stdout)
    print(f"record: {record_file}", file=stdout)
    for name in profile.integrations:
        count = len(staged.get(name, []))
        print(f"{name}: {builds[name]['status']}, {count} artifact(s) "
              "staged", file=stdout)
    for problem in problems:
        print(f"problem: {problem}", file=stdout)
    return 1 if problems else 0
