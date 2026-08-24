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

from pathlib import Path

from . import admit, assemble, emulate, resolve

#: In order. `emulate` is skipped when nothing in the profile can be probed,
#: which is a recorded fact rather than a silent omission (D-10's shape: the
#: chain admits against assembly evidence when emulation has nothing honest
#: to say).
STAGES = ("resolve", "assemble", "emulate", "admit")


def _newest(artifacts_root, pattern):
    records = sorted(
        Path(artifacts_root).glob(f"records/{pattern}"),
        key=lambda path: path.name)
    return records[-1] if records else None


def run(*, profile_path, revisions_path, environment_path, stack_root,
        profiles_root, artifacts_root, releases_root, repo_root,
        version, only, pinned_record, pinned_emulation, ready_timeout,
        terminate_grace, stdout, stderr):
    """Execute the build pipeline; returns the process exit code.

    A stage that fails stops the run: there is no value in assembling a
    resolution that was refused, and every later stage binds the earlier one
    by digest anyway.
    """
    wanted = STAGES if only is None else (only,)

    if "resolve" in wanted:
        code = resolve.run(
            revisions_path=revisions_path,
            environment_path=environment_path,
            artifacts_root=artifacts_root,
            repo_root=repo_root,
            stdout=stdout, stderr=stderr)
        if code:
            return code

    if "assemble" in wanted:
        resolution = (Path(pinned_record) if pinned_record
                      else _newest(artifacts_root, "resolve-*.json"))
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
    if "emulate" in wanted:
        assembly = (Path(pinned_record) if pinned_record
                    else _newest(artifacts_root, "assemble-*.json"))
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
        newest = _newest(artifacts_root, "emulate-*.json")
        emulation_record = str(newest) if newest else None
    if pinned_emulation:
        emulation_record = pinned_emulation

    if "admit" in wanted:
        if version is None:
            assembly = (Path(pinned_record) if pinned_record
                    else _newest(artifacts_root, "assemble-*.json"))
            if assembly is None:
                print("nothing built", file=stderr)
                return 2
            print(f"built: {assembly.name}", file=stdout)
            print("pass --version to admit it as a release", file=stdout)
            return 0
        assembly = (Path(pinned_record) if pinned_record
                    else _newest(artifacts_root, "assemble-*.json"))
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
