"""The admit verb: promote a validated chain into Releases/.

Admission is the one writer of Releases/ — the tracked, committed
attestation tier — and the only step that refuses. It follows an assembly
record back to the resolution whose gates guarded it, optionally forward to
an emulation that ran the bundle, and promotes only a clean chain: every
gate passed, every selection resolved, every member built, and any
emulation healthy. A release is made self-contained — the chain records are
copied in — because Artifacts/ is untracked and ephemeral, and an
attestation that points at swept evidence attests nothing.

Records state facts; admission decides. A refused admission writes nothing
to Releases/ and says why.
"""

from __future__ import annotations

import datetime
import json
import re
import secrets
import shutil
from pathlib import Path

from . import artifacts as artifact_contract
from . import filesystem
from . import gitfacts
from . import record as record_contract


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _integrations_of(refs):
    """The distinct repositories behind a list of deployable references.

    A resolution is keyed by integration because a checkout is per
    repository; an assembly is keyed by deployable because the work is.
    Joining the two chains means collapsing one to the other.
    """
    seen = []
    for ref in refs:
        name = ref.split(".", 1)[0]
        if name not in seen:
            seen.append(name)
    return seen


def _judge_resolution(resolution, expected_integrations):
    problems = []
    if resolution["deployment"]["dirty"]:
        problems.append("resolution: deployment repository was dirty")
    if not resolution["gates"]:
        problems.append("resolution: no policy gates were evaluated")
    for name in expected_integrations:
        if name not in resolution["resolved"]:
            problems.append(f"selection {name}: absent from the resolution")
    for name, facts in sorted(resolution["resolved"].items()):
        if facts["status"] != "resolved":
            problems.append(
                f"selection {name}: {facts['status']} — not release-clean")
        elif facts.get("dirty"):
            problems.append(f"selection {name}: source checkout was dirty")
    for name, verdict in sorted(resolution["gates"].items()):
        # "linked" is parity by construction — one canonical tree behind
        # both sites — so it admits exactly as a pass does.
        if verdict["status"] not in ("pass", "linked"):
            problems.append(f"gate {name}: {verdict['status']}")
    problems.extend(f"resolution: {item}" for item in resolution["problems"])
    return problems


def _judge_assembly(assembly, profile_members):
    problems = []
    if assembly["deployment"]["dirty"]:
        problems.append("assembly: deployment repository was dirty")
    for name in profile_members:
        facts = assembly["builds"].get(name)
        if facts is None:
            problems.append(f"build {name}: absent from the assembly")
        elif facts["status"] != "built":
            problems.append(f"build {name}: {facts['status']} — not shippable")
        elif not assembly["artifacts"].get(name):
            problems.append(f"artifacts {name}: built but nothing was staged")
    problems.extend(f"assembly: {item}" for item in assembly["problems"])
    return problems


def _judge_emulation(emulation):
    problems = []
    if emulation["deployment"]["dirty"]:
        problems.append("emulation: deployment repository was dirty")
    for name, facts in sorted(emulation["members"].items()):
        if facts["status"] != "healthy":
            problems.append(f"emulation {name}: {facts['status']}")
    problems.extend(f"emulation: {item}" for item in emulation["problems"])
    return problems


def run(version, assembly_record_path, emulation_record_path, artifacts_root,
        releases_root, repo_root, stdout, stderr):
    """Execute admit; returns the process exit code.

    0: admitted — Releases/<version>/ written, decision recorded.
    1: refused — the chain was not clean; Releases/ untouched.
    2: an input was refused, or the version already exists.
    """
    started = _utc_now()

    if not re.fullmatch(r"[a-z0-9][a-z0-9.-]*", version or ""):
        print(f"version: must match ^[a-z0-9][a-z0-9.-]*$, got {version!r}",
              file=stderr)
        return 2
    release_dir = Path(releases_root) / version
    if release_dir.exists():
        print(f"version {version} already exists at {release_dir} — "
              "releases are immutable; admit a new version", file=stderr)
        return 2

    records_dir = Path(artifacts_root) / "records"
    try:
        assembly_path = filesystem.resolve_direct_child(
            records_dir, assembly_record_path)
    except (OSError, filesystem.FilesystemContractError) as error:
        print(f"assembly record: {error}", file=stderr)
        return 2
    assembly, assembly_text, assembly_digest, errors = \
        record_contract.load_record_snapshot(assembly_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    if assembly["kind"] != "assembly":
        print(f"{assembly_record_path}: admit consumes an assembly record, "
              f"got kind {assembly['kind']}", file=stderr)
        return 2

    resolution_reference = assembly["resolution"]
    resolution_name = resolution_reference["record"]
    try:
        resolution_path = filesystem.resolve_beneath(
            records_dir, resolution_name, kind="file")
    except (OSError, filesystem.FilesystemContractError) as error:
        print(f"resolution record: {error}", file=stderr)
        return 2
    resolution, resolution_text, resolution_digest, errors = \
        record_contract.load_record_snapshot(resolution_path)
    if errors:
        print(f"{resolution_path}: the assembly's resolution is unreadable",
              file=stderr)
        for error in errors:
            print(error, file=stderr)
        return 2
    if resolution_digest != resolution_reference["sha256"]:
        print("resolution record digest does not match the assembly reference",
              file=stderr)
        return 2
    if resolution["kind"] != "resolution":
        print(f"{resolution_path}: not a resolution record", file=stderr)
        return 2
    if resolution["line"] != assembly["line"] \
            or resolution_reference["line"] != assembly["line"]:
        print("resolution and assembly lines do not match", file=stderr)
        return 2

    emulation = None
    emulation_text = None
    emulation_digest = None
    emulation_name = None
    if emulation_record_path is not None:
        try:
            emulation_path = filesystem.resolve_direct_child(
                records_dir, emulation_record_path)
        except (OSError, filesystem.FilesystemContractError) as error:
            print(f"emulation record: {error}", file=stderr)
            return 2
        emulation, emulation_text, emulation_digest, errors = \
            record_contract.load_record_snapshot(emulation_path)
        if errors:
            for error in errors:
                print(error, file=stderr)
            return 2
        if emulation["kind"] != "emulation":
            print(f"{emulation_record_path}: not an emulation record",
                  file=stderr)
            return 2
        # Chain integrity: emulation must bind this exact assembly record.
        reference = emulation["assembly"]
        if reference["record"] != assembly_path.name \
                or reference["sha256"] != assembly_digest \
                or reference["bundle"] != assembly["bundle"] \
                or emulation["line"] != assembly["line"] \
                or emulation["profile"] != assembly["profile"] \
                or emulation["deployables"] != assembly["deployables"]:
            print("emulation does not bind the exact assembly — the chain "
                  "does not connect", file=stderr)
            return 2
        emulation_name = emulation_path.name

    profile_members = assembly["deployables"]
    _, artifact_problems = artifact_contract.verify_bundle(
        artifacts_root, assembly)
    problems = (
        _judge_resolution(resolution, _integrations_of(profile_members))
        + _judge_assembly(assembly, profile_members)
        + (_judge_emulation(emulation) if emulation is not None else [])
        + artifact_problems
    )
    deployment_revisions = {
        resolution["deployment"]["revision"],
        assembly["deployment"]["revision"],
    }
    if emulation is not None:
        deployment_revisions.add(emulation["deployment"]["revision"])
    if len(deployment_revisions) != 1:
        problems.append(
            "chain: lifecycle stages used different deployment revisions")

    decision_stamp = datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    deployment_revision, error = gitfacts.git_query(
        repo_root, "rev-parse", "HEAD")
    if deployment_revision is None:
        print(f"deployment identity: {error}", file=stderr)
        return 2
    porcelain, _ = gitfacts.git_query(repo_root, "status", "--porcelain")
    if porcelain:
        problems.append("admission: deployment repository is currently dirty")
    if deployment_revision not in deployment_revisions:
        problems.append(
            "admission: deployment revision differs from the lifecycle chain")

    # The decision is always recorded (untracked), admitted or not — a
    # refused admission is a fact about the chain, even though it promotes
    # nothing. Only a clean chain is promoted into tracked Releases/.
    admitted = not problems
    decision = {
        "version": version,
        "admitted": admitted,
        "assembly": assembly_path.name,
        "problems": problems,
        "at": started,
    }
    decision_path = records_dir / f"admit-{version}-{decision_stamp}.json"

    if not admitted:
        filesystem.publish_text(
            decision_path,
            json.dumps(decision, indent=2, sort_keys=True) + "\n")
        print(f"refused: {version} is not admissible", file=stdout)
        for problem in problems:
            print(f"problem: {problem}", file=stdout)
        return 1

    release = {
        "schema_version": record_contract.SCHEMA_VERSION,
        "kind": "release",
        "run": {
            "verb": "admit",
            "started_at_utc": started,
            "finished_at_utc": _utc_now(),
        },
        "deployment": {
            "revision": deployment_revision,
            "dirty": bool(porcelain),
        },
        "line": assembly["line"],
        "version": version,
        "profile": assembly["profile"],
        "deployables": list(assembly["deployables"]),
        "chain": {
            "resolution": {
                "record": resolution_name,
                "sha256": resolution_reference["sha256"],
            },
            "assembly": {
                "record": assembly_path.name,
                "sha256": assembly_digest,
            },
            "emulation": ({
                "record": emulation_name,
                "sha256": emulation_digest,
            } if emulation is not None else None),
        },
        "attestation": {
            "gates": "pass",
            "builds": "pass",
            "selections": "pass",
            "emulation": "healthy" if emulation is not None else "absent",
        },
        "problems": [],
    }
    text = json.dumps(release, indent=2, sort_keys=True) + "\n"
    _, errors = record_contract.validate_record_text(text)
    if errors:
        for error in errors:
            print(f"release self-validation: {error}", file=stderr)
        return 2

    # Self-contained and atomically visible: prepare the complete release
    # beside its destination, then publish the directory in one rename.
    releases_root_path = Path(releases_root)
    releases_root_path.mkdir(parents=True, exist_ok=True)
    staging = releases_root_path / (
        f".{version}.{secrets.token_hex(8)}.pending")
    staging.mkdir()
    try:
        filesystem.publish_text(staging / "release.json", text)
        filesystem.publish_text(
            staging / "resolution.json",
            resolution_text)
        filesystem.publish_text(
            staging / "assembly.json",
            assembly_text)
        if emulation is not None:
            filesystem.publish_text(
                staging / "emulation.json",
                emulation_text)
        filesystem.publish_directory(staging, release_dir)
    except FileExistsError:
        print(f"version {version} became immutable during admission",
              file=stderr)
        return 2
    finally:
        if staging.exists():
            shutil.rmtree(staging)

    filesystem.publish_text(
        decision_path,
        json.dumps(decision, indent=2, sort_keys=True) + "\n")

    print(f"admitted: {release_dir}", file=stdout)
    print(f"version {version} — profile {assembly['profile']}, line "
          f"{assembly['line']}, emulation "
          f"{'healthy' if emulation is not None else 'absent'}", file=stdout)
    return 0
