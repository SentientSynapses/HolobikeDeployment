"""The `holobike` command line.

Four verbs, because there are four things a person wants: know whether this
workstation can do the work, run the product for development, build it for
release, and put a build somewhere.

    holobike check                 toolchains, checkouts, engine, roster
    holobike env <profile>         bring the product up and hold it
    holobike build <profile>       stage a bundle, gate it, admit a release
    holobike provision <device|server>   place a build on a thing

`resolve`, `bootstrap`, `assemble`, `emulate` and `admit` are stages of those
verbs rather than verbs themselves — reachable with `--only` when something
needs debugging, and run in order otherwise. Six stages exposed as an
interface is a pipeline, not a tool.

The CLI is the tool's testable surface: suites drive these verbs and nothing
beneath them. This file owns argument contracts and dispatch only.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from . import build as build_verb
from . import check
from . import env as env_verb
from . import filesystem
from . import integration as integration_contract
from . import nonmembers as nonmembers_contract
from . import policy as policy_contract
from . import profiles as profiles_contract
from . import provision as provision_verb
from . import record as record_contract
from . import revisions as revisions_contract

# .../Assembler/src/holobike_assemble/cli.py -> the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENVIRONMENT = REPO_ROOT / ".local" / "environment.json"
DEFAULT_STACK = REPO_ROOT / "Stack"
DEFAULT_PROFILES = REPO_ROOT / "Profiles"
DEFAULT_REVISIONS = REPO_ROOT / "Revisions"
DEFAULT_POLICY = REPO_ROOT / "Policy"
DEFAULT_RELEASES = REPO_ROOT / "Releases"
DEFAULT_ARTIFACTS = REPO_ROOT / "Artifacts"

#: Every declared document kind `check` will judge, and its loader.
JUDGES = {
    "environment": None,  # handled inside check.run, which also reports
    "integration": integration_contract.load_integration,
    "nonmembers": nonmembers_contract.load_nonmembers,
    "policy": policy_contract.load_policy,
    "profile": profiles_contract.load_profile,
    "record": record_contract.load_record,
    "revisions": revisions_contract.load_revisions,
}


def _positive_seconds(value):
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError(
            "must be a finite number greater than zero")
    return parsed


def _common(parser, *, stack=True, artifacts=True):
    parser.add_argument(
        "--environment", default=str(DEFAULT_ENVIRONMENT),
        help="path to the environment mapping "
        "(default: .local/environment.json)")
    if stack:
        parser.add_argument(
            "--stack", default=str(DEFAULT_STACK),
            help="path to the Stack tree of integration contracts")
    if artifacts:
        parser.add_argument(
            "--artifacts", default=str(DEFAULT_ARTIFACTS),
            help="path to the working Artifacts/ root")


def _composition(parser):
    parser.add_argument(
        "profile", nargs="?", default="device",
        help="the profile to compose, named as under Profiles/ "
             "(default: device)")
    parser.add_argument(
        "--line", default="dev",
        help="the revision line to compose (default: dev)")
    parser.add_argument("--profile-path", help="an explicit profile document")
    parser.add_argument("--revisions", help="an explicit revision manifest")
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILES))
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument(
        "--ready-timeout", type=_positive_seconds, default=30.0,
        help="seconds to wait for a member to probe healthy")
    parser.add_argument(
        "--terminate-grace", type=_positive_seconds, default=5.0,
        help="seconds between SIGTERM and SIGKILL at teardown")
    parser.add_argument(
        "--record", metavar="PATH",
        help="pin a stage's input record instead of taking the newest under "
             "Artifacts/records/ — for debugging one stage in isolation")


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="holobike",
        description="Compose the declared HoloBike stack into a development "
        "environment or a release, for a device or for a server.")
    verbs = parser.add_subparsers(dest="verb", required=True)

    checker = verbs.add_parser(
        "check", help="read-only: is this workstation able to do the work?")
    _common(checker, artifacts=False)
    checker.add_argument(
        "--json", action="store_true",
        help="emit the report as JSON instead of a table")
    for kind in sorted(JUDGES):
        checker.add_argument(
            f"--validate-{kind}", metavar="PATH",
            help=f"judge one {kind} document and say nothing else")
    checker.add_argument(
        "--validate-only", action="store_true",
        help="judge the environment document and say nothing else")

    environment = verbs.add_parser(
        "env", help="bring the product up for development and hold it")
    _common(environment)
    _composition(environment)
    environment.add_argument(
        "--only", choices=env_verb.STAGES,
        help="run one stage instead of the whole composition")

    builder = verbs.add_parser(
        "build", help="stage a bundle, gate it, and admit a release")
    _common(builder)
    _composition(builder)
    builder.add_argument(
        "--version", help="admit the build as this release version")
    builder.add_argument(
        "--emulation", metavar="PATH",
        help="pin the emulation record the admit stage carries")
    builder.add_argument("--releases", default=str(DEFAULT_RELEASES))
    builder.add_argument(
        "--only", choices=build_verb.STAGES,
        help="run one stage instead of the whole pipeline")

    provisioner = verbs.add_parser(
        "provision", help="place a build on a device or on infrastructure")
    provisioner.add_argument(
        "destination", choices=provision_verb.DESTINATIONS)
    provisioner.add_argument(
        "--root", help="the offline root to write into")
    provisioner.add_argument(
        "--identity", help="a device identity document to install")
    provisioner.add_argument(
        "--verify", action="store_true",
        help="verify what is installed instead of installing")
    return parser


def _judge(loader, path):
    _, errors = loader(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print(f"{path}: valid")
    return 0


def _resolved_paths(arguments):
    return {
        "profile_path": arguments.profile_path or str(
            Path(arguments.profiles) / f"{arguments.profile}.json"),
        "revisions_path": arguments.revisions or str(
            DEFAULT_REVISIONS / f"{arguments.line}.json"),
    }


def _main(argv=None):
    arguments = _build_parser().parse_args(argv)

    if arguments.verb == "check":
        for kind, loader in sorted(JUDGES.items()):
            if loader is None:
                continue
            path = getattr(arguments, f"validate_{kind}")
            if path is not None:
                return _judge(loader, path)
        return check.run(
            environment_path=arguments.environment,
            stack_root=arguments.stack,
            validate_only=(
                arguments.validate_only
                or arguments.validate_environment is not None),
            validate_integration=None,
            validate_nonmembers=None,
            as_json=arguments.json,
            stdout=sys.stdout, stderr=sys.stderr)

    if arguments.verb == "env":
        return env_verb.run(
            **_resolved_paths(arguments),
            environment_path=arguments.environment,
            stack_root=arguments.stack,
            profiles_root=arguments.profiles,
            artifacts_root=arguments.artifacts,
            policy_root=arguments.policy,
            repo_root=REPO_ROOT,
            only=arguments.only,
            pinned_record=arguments.record,
            ready_timeout=arguments.ready_timeout,
            terminate_grace=arguments.terminate_grace,
            stdout=sys.stdout, stderr=sys.stderr)

    if arguments.verb == "build":
        return build_verb.run(
            **_resolved_paths(arguments),
            environment_path=arguments.environment,
            stack_root=arguments.stack,
            profiles_root=arguments.profiles,
            artifacts_root=arguments.artifacts,
            policy_root=arguments.policy,
            releases_root=arguments.releases,
            repo_root=REPO_ROOT,
            version=arguments.version,
            only=arguments.only,
            pinned_record=arguments.record,
            pinned_emulation=arguments.emulation,
            ready_timeout=arguments.ready_timeout,
            terminate_grace=arguments.terminate_grace,
            stdout=sys.stdout, stderr=sys.stderr)

    if arguments.verb == "provision":
        return provision_verb.run(
            destination=arguments.destination,
            identity_input=arguments.identity,
            root=arguments.root,
            verify=arguments.verify,
            stdout=sys.stdout, stderr=sys.stderr)
    raise AssertionError(f"unreachable verb: {arguments.verb}")


def main(argv=None):
    try:
        return _main(argv)
    except (OSError, filesystem.FilesystemContractError) as error:
        print(f"{type(error).__name__}: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130
