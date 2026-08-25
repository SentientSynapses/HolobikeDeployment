"""The `build` verb: declarations in, an admitted release out.

`resolve` → `assemble` → `emulate` → `admit` were six-sevenths of a pipeline
exposed as an interface. Nobody wants to run `admit` by hand, and nobody wants
to remember that `emulate` reads the newest assembly record. They are stages
here, reachable individually with `--only` when something needs debugging, and
run in order otherwise.

A build either produces provenance or fails. Without `--version` it stops
after emulation and reports what it would admit; with one, it admits.
"""

from __future__ import annotations

import json
import pathlib
from pathlib import Path

from . import admit, assemble, emulate, resolve
from . import profiles as profiles_contract
from . import stack as stack_contract

#: In order. `emulate` is skipped when nothing in the profile can be probed,
#: which is a recorded fact rather than a silent omission (D-10's shape: the
#: chain admits against assembly evidence when emulation has nothing honest
#: to say).
STAGES = ("resolve", "assemble", "emulate", "admit")


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

def _problems_within(resolution_path, profile_path, stdout, stderr):
    """0 when every resolution problem lies outside the profile's members;
    1 when one of them is a member the profile composes."""
    profile, errors = profiles_contract.load_profile(profile_path)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2
    resolution = json.loads(Path(resolution_path).read_text("utf-8"))
    inside = sorted(
        name for name in profile.integrations
        if resolution["resolved"].get(name, {}).get("status") != "resolved")
    if inside:
        print(f"unresolved in profile {profile.profile}: "
              + ", ".join(inside), file=stderr)
        return 1
    print(f"the resolution's problems lie outside profile {profile.profile}; "
          "continuing", file=stdout)
    return 0


def _probeable(profile_path, stack_root, stderr):
    """Whether anything the profile selects declares a service to probe.

    Returns (probeable, code). `emulate` proves coexistence by running what
    declares `serve`; a profile in which nothing does has nothing for it to
    say, and the docstring at STAGES describes what happens then.
    """
    profile, errors = profiles_contract.load_profile(profile_path)
    if not errors:
        documents, errors = stack_contract.load_stack(stack_root)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return False, 2
    for selection in profile.selections:
        leaf = documents.get(selection.integration)
        deployable = leaf.deployable(selection.deployable) if leaf else None
        if deployable is not None and deployable.serve.argv:
            return True, 0
    return False, 0


def run(*, profile_path, revisions_path, environment_path, stack_root,
        profiles_root, artifacts_root, releases_root, repo_root,
        version, only, pinned_record, pinned_emulation, ready_timeout,
        terminate_grace, stdout, stderr):
    """Execute the build pipeline; returns the process exit code.

    A stage that fails stops the run: there is no value in assembling a
    resolution that was refused, and every later stage binds the earlier one
    by digest anyway. One refinement (D-23): the resolution is line-wide —
    drift anywhere in the stack is its business — but a build composes one
    profile, so a resolution whose only problems lie in members the profile
    does not select is a recorded fact this build carries, not a reason to
    stop. `--only resolve` keeps the line-wide exit code; that is the daily
    cadence's contract.
    """
    # A profile's name is its file name under Profiles/, and a line's is its
    # manifest's — both stated by their schemas — so the stem is the scope.
    profile = Path(profile_path).stem
    line = Path(revisions_path).stem
    wanted = STAGES if only is None else (only,)

    if "resolve" in wanted:
        code = resolve.run(
            revisions_path=revisions_path,
            environment_path=environment_path,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            stdout=stdout, stderr=stderr)
        if code == 1 and wanted is STAGES:
            code = _problems_within(
                _newest(artifacts_root, "resolve", line), profile_path,
                stdout, stderr)
        if code:
            return code

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
        if code:
            return code

    emulation_record = None
    if "emulate" in wanted and wanted is STAGES:
        # `--only emulate` is a person debugging that stage; it runs against
        # the record it is given and is never skipped on their behalf.
        probeable, code = _probeable(profile_path, stack_root, stderr)
        if code:
            return code
        if not probeable:
            print(f"emulate: skipped — nothing in profile {profile} declares "
                  "a service to probe", file=stdout)
            wanted = tuple(stage for stage in wanted if stage != "emulate")
    if "emulate" in wanted:
        assembly = (Path(pinned_record) if pinned_record
                    else _newest(artifacts_root, "assemble", profile))
        if assembly is None:
            print("no assembly record — run the assemble stage first",
                  file=stderr)
            return 2
        code = emulate.run(
            record_path=str(assembly),
            stack_root=stack_root,
            profiles_root=profiles_root,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            environment_path=environment_path,
            ready_timeout=ready_timeout,
            terminate_grace=terminate_grace,
            stdout=stdout, stderr=stderr)
        if code:
            return code
        newest = _newest(artifacts_root, "emulate", profile)
        emulation_record = str(newest) if newest else None
    if pinned_emulation:
        emulation_record = pinned_emulation

    if "admit" in wanted:
        if version is None:
            assembly = (Path(pinned_record) if pinned_record
                    else _newest(artifacts_root, "assemble", profile))
            if assembly is None:
                print("nothing built", file=stderr)
                return 2
            print(f"built: {assembly.name}", file=stdout)
            print("pass --version to admit it as a release", file=stdout)
            return 0
        assembly = (Path(pinned_record) if pinned_record
                    else _newest(artifacts_root, "assemble", profile))
        if assembly is None:
            print("no assembly record — run the assemble stage first",
                  file=stderr)
            return 2
        return admit.run(
            version=version,
            assembly_record_path=str(assembly),
            emulation_record_path=emulation_record,
            artifacts_root=artifacts_root,
            releases_root=releases_root,
            repo_root=repo_root,
            environment_path=environment_path,
            stdout=stdout, stderr=stderr)
    return 0
