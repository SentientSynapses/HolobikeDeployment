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
from pathlib import Path

from . import gitfacts
from . import record as record_contract


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")


def _judge_resolution(resolution):
    problems = []
    for name, facts in sorted(resolution["resolved"].items()):
        if facts["status"] != "resolved":
            problems.append(
                f"selection {name}: {facts['status']} — not release-clean")
    for name, verdict in sorted(resolution["gates"].items()):
        if verdict["status"] != "pass":
            problems.append(f"gate {name}: {verdict['status']}")
    problems.extend(f"resolution: {item}" for item in resolution["problems"])
    return problems


def _judge_assembly(assembly, profile_members):
    problems = []
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
    for name, facts in sorted(emulation["members"].items()):
        if facts["status"] not in ("healthy", "skipped"):
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

    import re
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
    assembly, errors = record_contract.load_record(assembly_record_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    if assembly["kind"] != "assembly":
        print(f"{assembly_record_path}: admit consumes an assembly record, "
              f"got kind {assembly['kind']}", file=stderr)
        return 2

    resolution_name = assembly["resolution"]["record"]
    resolution_path = records_dir / resolution_name
    resolution, errors = record_contract.load_record(resolution_path)
    if errors:
        print(f"{resolution_path}: the assembly's resolution is unreadable",
              file=stderr)
        for error in errors:
            print(error, file=stderr)
        return 2
    if resolution["kind"] != "resolution":
        print(f"{resolution_path}: not a resolution record", file=stderr)
        return 2

    emulation = None
    emulation_name = None
    if emulation_record_path is not None:
        emulation, errors = record_contract.load_record(emulation_record_path)
        if errors:
            for error in errors:
                print(error, file=stderr)
            return 2
        if emulation["kind"] != "emulation":
            print(f"{emulation_record_path}: not an emulation record",
                  file=stderr)
            return 2
        # Chain integrity: the emulation must have run THIS assembly's bundle.
        if emulation["assembly"]["bundle"] != assembly["bundle"]:
            print("emulation ran a different bundle than the assembly built "
                  "— the chain does not connect", file=stderr)
            return 2
        emulation_name = Path(emulation_record_path).name

    profile_members = sorted(assembly["builds"])
    problems = (
        _judge_resolution(resolution)
        + _judge_assembly(assembly, profile_members)
        + (_judge_emulation(emulation) if emulation is not None else [])
    )

    decision_stamp = datetime.datetime.now(
        datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    deployment_revision, error = gitfacts.git_query(
        repo_root, "rev-parse", "HEAD")
    if deployment_revision is None:
        print(f"deployment identity: {error}", file=stderr)
        return 2
    porcelain, _ = gitfacts.git_query(repo_root, "status", "--porcelain")

    # The decision is always recorded (untracked), admitted or not — a
    # refused admission is a fact about the chain, even though it promotes
    # nothing. Only a clean chain is promoted into tracked Releases/.
    admitted = not problems
    decision = {
        "version": version,
        "admitted": admitted,
        "assembly": Path(assembly_record_path).name,
        "problems": problems,
        "at": started,
    }
    records_dir.mkdir(parents=True, exist_ok=True)
    (records_dir / f"admit-{version}-{decision_stamp}.json").write_text(
        json.dumps(decision, indent=2, sort_keys=True) + "\n",
        encoding="utf-8")

    if not admitted:
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
        "chain": {
            "resolution": resolution_name,
            "assembly": Path(assembly_record_path).name,
            "emulation": emulation_name,
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

    # Self-contained: copy the chain in, so the release references nothing
    # under untracked Artifacts/.
    release_dir.mkdir(parents=True)
    (release_dir / "release.json").write_text(text, encoding="utf-8")
    (release_dir / "resolution.json").write_text(
        resolution_path.read_text(encoding="utf-8"), encoding="utf-8")
    (release_dir / "assembly.json").write_text(
        Path(assembly_record_path).read_text(encoding="utf-8"),
        encoding="utf-8")
    if emulation_record_path is not None:
        (release_dir / "emulation.json").write_text(
            Path(emulation_record_path).read_text(encoding="utf-8"),
            encoding="utf-8")

    print(f"admitted: {release_dir}", file=stdout)
    print(f"version {version} — profile {assembly['profile']}, line "
          f"{assembly['line']}, emulation "
          f"{'healthy' if emulation is not None else 'absent'}", file=stdout)
    return 0
