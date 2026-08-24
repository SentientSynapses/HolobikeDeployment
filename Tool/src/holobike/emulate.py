"""The emulate verb: run an assembly and watch it answer.

Emulate consumes the bundle, never the workstation: serve and probe argvs
reference ${BUNDLE} (the member's staged artifacts) and ${STATE} (a
per-member writable root), so a member that cannot run from its bundle is
an incomplete bundle — and this is the verb that catches it. Members spawn
as host processes, readiness is the member's own probe answering, one
settle pass proves coexistence, and teardown is guaranteed: a failed
emulation still reaps its children and still writes its record.
"""

from __future__ import annotations

import datetime
import json
import os
import signal
import subprocess
import time
from pathlib import Path

from . import artifacts as artifact_contract
from . import filesystem
from . import gitfacts
from . import profiles as profiles_contract
from . import record as record_contract
from . import stack as stack_contract

PROBE_INTERVAL_SECONDS = 0.25
PROBE_ATTEMPT_TIMEOUT_SECONDS = 10.0

_PROBLEM_STATUSES = ("skipped", "spawn_failed", "exited_early",
                     "never_ready", "failed_settle", "unclean_shutdown")


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


def _substitute(value, bundle_dir, state_dir):
    return value.replace("${BUNDLE}", str(bundle_dir)) \
                .replace("${STATE}", str(state_dir))


def _substitute_command(command, overlay, bundle_dir, state_dir):
    argv = [_substitute(item, bundle_dir, state_dir)
            for item in command.argv]
    env = {key: _substitute(entry, bundle_dir, state_dir)
           for key, entry in command.env}
    for key, entry in overlay.items():
        env[key] = _substitute(entry, bundle_dir, state_dir)
    return argv, env


def _probe_once(argv, env, state_dir):
    merged = _runtime_environment(state_dir)
    merged.update(env)
    try:
        process = subprocess.Popen(
            argv,
            cwd=state_dir,
            env=merged,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            return process.wait(timeout=PROBE_ATTEMPT_TIMEOUT_SECONDS) == 0
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            return False
    except OSError:
        return False


def _runtime_environment(state_dir):
    """Build a bounded child environment without inheriting host secrets."""
    inherited = {
        key: os.environ[key]
        for key in ("PATH", "LANG", "LC_ALL", "TZ")
        if key in os.environ
    }
    inherited.update({
        "HOME": str(state_dir),
        "XDG_CACHE_HOME": str(Path(state_dir) / ".cache"),
        "XDG_CONFIG_HOME": str(Path(state_dir) / ".config"),
        "XDG_DATA_HOME": str(Path(state_dir) / ".local/share"),
        "XDG_STATE_HOME": str(Path(state_dir) / ".local/state"),
    })
    return inherited


class _Member:
    """One spawned member's lifecycle state — not a public surface."""

    def __init__(self, name):
        self.name = name
        self.facts = {}
        self.process = None
        self.probe_argv = None
        self.probe_env = {}
        self.state_dir = None
        self.ready = False


def _spawn_and_await(member, served, topology, bundle_root, run_root,
                     ready_timeout):
    facts = member.facts
    facts["run"] = topology.run
    if not served.serve.argv:
        facts["status"] = "skipped"
        facts["detail"] = "no serve entry point declared for this deployable"
        return
    if not served.probe.argv:
        facts["status"] = "skipped"
        facts["detail"] = "no probe entry point declared for this deployable"
        return

    bundle_dir = Path(bundle_root) / member.name
    referenced = any(
        "${BUNDLE}" in item
        for item in list(served.serve.argv) + list(served.probe.argv))
    if referenced and not bundle_dir.is_dir():
        facts["status"] = "spawn_failed"
        facts["detail"] = "member is absent from the bundle"
        return

    member.state_dir = run_root / "members" / member.name
    member.state_dir.mkdir(mode=0o700)
    serve_argv, serve_env = _substitute_command(
        served.serve, topology.environment, bundle_dir, member.state_dir)
    member.probe_argv, member.probe_env = _substitute_command(
        served.probe, topology.environment, bundle_dir, member.state_dir)
    facts["serve"] = {"argv": serve_argv, "env": serve_env}

    log_path = run_root / "logs" / f"{member.name}.serve.log"
    facts["log"] = str(log_path.relative_to(run_root))
    merged = _runtime_environment(member.state_dir)
    merged.update(serve_env)
    try:
        with filesystem.open_private_output(log_path) as log:
            member.process = subprocess.Popen(
                serve_argv,
                cwd=member.state_dir,
                env=merged,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
    except OSError as error:
        facts["status"] = "spawn_failed"
        facts["detail"] = str(error)
        return

    attempts = 0
    started = time.monotonic()
    deadline = started + ready_timeout
    while time.monotonic() < deadline:
        exited = member.process.poll()
        if exited is not None:
            facts["status"] = "exited_early"
            facts["detail"] = f"serve exited {exited} before ready"
            facts["probe"] = {"attempts": attempts}
            return
        attempts += 1
        if _probe_once(member.probe_argv, member.probe_env,
                       member.state_dir):
            member.ready = True
            facts["probe"] = {
                "attempts": attempts,
                "ready_after_ms": int(
                    (time.monotonic() - started) * 1000),
            }
            return
        time.sleep(PROBE_INTERVAL_SECONDS)
    facts["status"] = "never_ready"
    facts["detail"] = f"probe never passed within {ready_timeout:g}s"
    facts["probe"] = {"attempts": attempts}


def _teardown(member, grace):
    """Reap one member process group; records shutdown facts. Never raises."""
    process = member.process
    if process is None:
        return
    process.poll()
    clean = True
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        process.poll()
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        clean = False
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.wait()
    member.facts["shutdown"] = {"clean": clean}
    if not clean:
        member.facts["shutdown"]["detail"] = (
            f"ignored SIGTERM for {grace:g}s; killed")


def run(record_path, stack_root, profiles_root, artifacts_root, repo_root,
        ready_timeout, terminate_grace, stdout, stderr, hold=False):
    """Execute emulate; returns the process exit code.

    0: every member healthy — ready, settled, cleanly shut down.
    1: record written, problems inside it.
    2: an input was refused (or the record could not be written).
    """
    started = _utc_now()

    if os.geteuid() == 0:
        print("host-process emulation refuses to run as root", file=stderr)
        return 2

    records_root = Path(artifacts_root) / "records"
    try:
        assembly_path = filesystem.resolve_direct_child(
            records_root, record_path)
    except (OSError, filesystem.FilesystemContractError) as error:
        print(f"assembly record: {error}", file=stderr)
        return 2
    assembly, _, assembly_digest, errors = \
        record_contract.load_record_snapshot(assembly_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    if assembly["kind"] != "assembly":
        print(
            f"{record_path}: emulate consumes an assembly record, got "
            f"kind {assembly['kind']}", file=stderr)
        return 2
    bundle_root, artifact_problems = artifact_contract.verify_bundle(
        artifacts_root, assembly)
    if artifact_problems:
        for problem in artifact_problems:
            print(problem, file=stderr)
        return 2
    profile_path = Path(profiles_root) / f"{assembly['profile']}.json"
    profile, errors = profiles_contract.load_profile(profile_path)
    if errors:
        for error in errors:
            print(f"{profile_path}: {error}", file=stderr)
        return 2
    if [s.ref for s in profile.selections] != list(
            assembly["deployables"]):
        print(
            f"{profile_path}: profile membership changed after assembly",
            file=stderr)
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
    run_root = Path(artifacts_root) / "emulations" \
        / f"{profile.profile}-{stamp}"
    run_root.mkdir(parents=True, mode=0o700)
    run_root.chmod(0o700)
    (run_root / "logs").mkdir(mode=0o700)
    (run_root / "members").mkdir(mode=0o700)

    members = []
    try:
        for selection in profile.selections:
            # The member's name is the deployable's reference: two halves of
            # one repository run as two members, with two state directories
            # and two logs, which is what they are.
            member = _Member(selection.ref)
            members.append(member)
            topology = profile.topology.get(selection.ref)
            if topology is None:
                member.facts["run"] = "host"
                member.facts["status"] = "skipped"
                member.facts["detail"] = \
                    "no topology declared for this member"
                continue
            leaf = leaves.get(selection.integration)
            if leaf is None:
                member.facts["run"] = topology.run
                member.facts["status"] = "skipped"
                member.facts["detail"] = "no Stack leaf found"
                continue
            served = leaf.deployable(selection.deployable)
            if served is None:
                member.facts["run"] = topology.run
                member.facts["status"] = "skipped"
                member.facts["detail"] = \
                    "the Stack leaf declares no such deployable"
                continue
            _spawn_and_await(
                member, served, topology, bundle_root, run_root,
                ready_timeout)

        # The settle pass: every ready member must still answer once all of
        # them are up — coexistence, not just startup.
        for member in members:
            if member.ready:
                if not _probe_once(member.probe_argv, member.probe_env,
                                   member.state_dir):
                    member.ready = False
                    member.facts["status"] = "failed_settle"
                    member.facts["detail"] = \
                        "probe failed once every member was up"

        if hold:
            # The development posture: the same bring-up, then stay. Teardown
            # is still the `finally` below, so an interrupt tears down exactly
            # as a completed run does — one path, not two.
            ready = [m for m in members if m.ready]
            print(f"ready: {len(ready)} of {len(members)} member(s) serving",
                  file=stdout)
            for member in ready:
                print(f"  {member.name}: {member.state_dir}", file=stdout)
            print("holding — interrupt to stop", file=stdout)
            try:
                signal.pause()
            except (KeyboardInterrupt, AttributeError):
                pass
    finally:
        for member in reversed(members):
            _teardown(member, terminate_grace)

    for member in members:
        if "status" not in member.facts:
            shutdown = member.facts.get("shutdown", {"clean": True})
            member.facts["status"] = \
                "healthy" if shutdown["clean"] else "unclean_shutdown"

    problems = [
        f"{member.name}: {member.facts['status']} — "
        f"{member.facts.get('detail', '')}".rstrip(" —")
        for member in members
        if member.facts["status"] in _PROBLEM_STATUSES
    ]

    body = {
        "schema_version": record_contract.SCHEMA_VERSION,
        "kind": "emulation",
        "run": {
            "verb": "emulate",
            "started_at_utc": started,
            "finished_at_utc": _utc_now(),
        },
        "deployment": {
            "revision": deployment_revision,
            "dirty": bool(porcelain),
        },
        "line": assembly["line"],
        "profile": profile.profile,
        "deployables": list(assembly["deployables"]),
        "assembly": {
            "record": assembly_path.name,
            "sha256": assembly_digest,
            "bundle": assembly["bundle"],
        },
        "members": {member.name: member.facts for member in members},
        "problems": problems,
    }
    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    _, errors = record_contract.validate_record_text(text)
    if errors:
        for error in errors:
            print(f"record self-validation: {error}", file=stderr)
        return 2

    record_file = records_root \
        / f"emulate-{profile.profile}-{stamp}.json"
    filesystem.publish_text(record_file, text)

    print(f"run: {run_root}", file=stdout)
    print(f"record: {record_file}", file=stdout)
    for member in members:
        print(f"{member.name}: {member.facts['status']}", file=stdout)
    for problem in problems:
        print(f"problem: {problem}", file=stdout)
    return 1 if problems else 0
