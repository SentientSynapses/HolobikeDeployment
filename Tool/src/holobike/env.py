"""The `env` verb: a workstation that can actually run the thing.

The development composition is the release composition run in a persistent,
developer-facing mode — not a parallel system (D-16). So `env` is the same
stages `build` runs, stopping where a developer wants to be: services up,
probed, and held.

`bootstrap` is folded in rather than being a verb of its own. A developer
whose tree is missing a checkout wants it materialized, not diagnosed.
"""

from __future__ import annotations

import pathlib
from pathlib import Path

from . import assemble, bootstrap, check, emulate, resolve

STAGES = ("check", "bootstrap", "resolve", "assemble", "serve")


def _newest(artifacts_root, kind, scope):
    """The most recent record of `kind` for `scope`, or None.

    Scoped deliberately. Record names are `<kind>-<scope>-<stamp>.json`, so a
    sort over an unscoped glob orders by profile or line name first and only
    then by time — which quietly hands `device` the newest `server` record,
    or a retired profile's leftovers. The scope is the point: a build composes
    one profile on one line, and it must not inherit another's evidence.
    """
    records = sorted(
        pathlib.Path(artifacts_root).glob(f"records/{kind}-{scope}-*.json"),
        key=lambda path: path.name)
    return records[-1] if records else None

def run(*, profile_path, revisions_path, environment_path, stack_root,
        profiles_root, artifacts_root, repo_root, only,
        pinned_record, ready_timeout, terminate_grace, stdout, stderr):
    """Bring a development environment up and hold it; returns an exit code.

    A stage that reports *problems* (1) does not stop the composition — a
    partial workstation is a recorded fact, not a refusal, which is the M3
    tradition. A stage that *refuses* (2) does stop it. The worst code any
    stage returned is the run's code, so `env` never reports success over a
    stage that did not have it.
    """
    # A profile's name is its file name under Profiles/, and a line's is its
    # manifest's — both stated by their schemas — so the stem is the scope.
    profile = Path(profile_path).stem
    line = Path(revisions_path).stem
    wanted = STAGES if only is None else (only,)
    worst = 0

    def note(code):
        nonlocal worst
        worst = max(worst, code)
        return code == 2

    if "check" in wanted:
        # A broken environment is named before anything launches. Problems
        # here are reported and do not stop the run: a partial workstation is
        # a recorded fact, not a refusal (the M3 tradition).
        code = check.run(
            environment_path=environment_path,
            stack_root=stack_root,
            validate_only=False,
            validate_integration=None,
            validate_nonmembers=None,
            as_json=False,
            stdout=stdout, stderr=stderr)
        if note(code):
            return worst

    if "bootstrap" in wanted:
        code = bootstrap.run(
            revisions_path=revisions_path,
            environment_path=environment_path,
            stack_root=stack_root,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            stdout=stdout, stderr=stderr)
        if note(code):
            return worst

    if "resolve" in wanted:
        code = resolve.run(
            revisions_path=revisions_path,
            environment_path=environment_path,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            stdout=stdout, stderr=stderr)
        if note(code):
            return worst

    if "assemble" in wanted:
        resolution = (Path(pinned_record) if pinned_record
                      else _newest(artifacts_root, "resolve", line))
        if resolution is None:
            print("no resolution record — run the resolve stage first",
                  file=stderr)
            return 2
        code = assemble.run(
            profile_path=profile_path,
            record_path=str(resolution),
            environment_path=environment_path,
            stack_root=stack_root,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            stdout=stdout, stderr=stderr)
        if note(code):
            return worst

    if "serve" in wanted:
        assembly = (Path(pinned_record) if pinned_record
                    else _newest(artifacts_root, "assemble", profile))
        if assembly is None:
            print("no assembly record — run the assemble stage first",
                  file=stderr)
            return 2
        note(emulate.run(
            record_path=str(assembly),
            stack_root=stack_root,
            profiles_root=profiles_root,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            environment_path=environment_path,
            ready_timeout=ready_timeout,
            terminate_grace=terminate_grace,
            stdout=stdout, stderr=stderr,
            hold=True))
    return worst
