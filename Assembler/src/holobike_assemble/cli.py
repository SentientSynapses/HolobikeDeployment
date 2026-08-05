"""The holobike-assemble command line.

The CLI is the Assembler's testable surface: suites drive these verbs and
nothing beneath them. Each verb delegates its domain work to its own module;
this file owns argument contracts and dispatch only.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from . import admit
from . import assemble
from . import bootstrap
from . import emulate
from . import filesystem
from . import policy as policy_contract
from . import profiles as profiles_contract
from . import preflight
from . import record as record_contract
from . import resolve
from . import revisions as revisions_contract

# .../Assembler/src/holobike_assemble/cli.py -> the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENVIRONMENT = REPO_ROOT / ".local" / "environment.json"
DEFAULT_STACK = REPO_ROOT / "Stack"


def _positive_seconds(value):
    try:
        parsed = float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a number") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError(
            "must be a finite number greater than zero")
    return parsed


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="holobike-assemble",
        description="Turn the declared HoloBike specification into staged "
        "artifacts and attested records.",
    )
    verbs = parser.add_subparsers(dest="verb", required=True)

    preflight_parser = verbs.add_parser(
        "preflight",
        help="read-only: validate the environment mapping and report every "
        "integration's revision, dirty state, and toolchain presence",
    )
    preflight_parser.add_argument(
        "--environment",
        default=str(DEFAULT_ENVIRONMENT),
        help="path to the environment mapping "
        "(default: .local/environment.json)",
    )
    preflight_parser.add_argument(
        "--stack",
        default=str(DEFAULT_STACK),
        help="path to the Stack tree of integration contracts "
        "(default: Stack/)",
    )
    preflight_parser.add_argument(
        "--validate-only",
        action="store_true",
        help="judge the environment document and say nothing else",
    )
    preflight_parser.add_argument(
        "--validate-integration",
        metavar="PATH",
        help="judge one integration contract document and say nothing else",
    )
    preflight_parser.add_argument(
        "--json",
        action="store_true",
        help="emit the report as JSON instead of a table",
    )

    bootstrap_parser = verbs.add_parser(
        "bootstrap",
        help="materialize the environment: clone missing checkouts from "
        "their declared origins, fast-forward clean on-branch ones; "
        "dirty or diverged trees are reported, never reset",
    )
    bootstrap_parser.add_argument(
        "--line",
        default="dev",
        help="the line to materialize: Revisions/<line>.json (default: dev)",
    )
    bootstrap_parser.add_argument(
        "--revisions",
        metavar="PATH",
        help="explicit revision manifest path (overrides --line)",
    )
    bootstrap_parser.add_argument(
        "--environment",
        default=str(DEFAULT_ENVIRONMENT),
        help="path to the environment mapping "
        "(default: .local/environment.json)",
    )
    bootstrap_parser.add_argument(
        "--stack",
        default=str(DEFAULT_STACK),
        help="path to the Stack tree of integration contracts "
        "(default: Stack/)",
    )
    bootstrap_parser.add_argument(
        "--artifacts",
        default=str(REPO_ROOT / "Artifacts"),
        help="untracked output root for records (default: Artifacts/)",
    )

    resolve_parser = verbs.add_parser(
        "resolve",
        help="pin a revision manifest against the workstation's checkouts "
        "and write the resolution record to Artifacts/",
    )
    resolve_parser.add_argument(
        "--line",
        default="dev",
        help="the line to resolve: Revisions/<line>.json (default: dev)",
    )
    resolve_parser.add_argument(
        "--revisions",
        metavar="PATH",
        help="explicit revision manifest path (overrides --line)",
    )
    resolve_parser.add_argument(
        "--environment",
        default=str(DEFAULT_ENVIRONMENT),
        help="path to the environment mapping "
        "(default: .local/environment.json)",
    )
    resolve_parser.add_argument(
        "--artifacts",
        default=str(REPO_ROOT / "Artifacts"),
        help="untracked output root for records (default: Artifacts/)",
    )
    resolve_parser.add_argument(
        "--policy",
        default=str(REPO_ROOT / "Policy"),
        help="directory of policy documents whose gates ride the record "
        "(default: Policy/)",
    )
    resolve_parser.add_argument(
        "--validate-revisions",
        metavar="PATH",
        help="judge one revision manifest and say nothing else",
    )
    resolve_parser.add_argument(
        "--validate-policy",
        metavar="PATH",
        help="judge one policy document and say nothing else",
    )
    resolve_parser.add_argument(
        "--validate-record",
        metavar="PATH",
        help="judge one run record and say nothing else",
    )

    assemble_parser = verbs.add_parser(
        "assemble",
        help="stage a product bundle: run each profile member's declared "
        "build steps and stage its artifacts, digested, into Artifacts/",
    )
    assemble_parser.add_argument(
        "--profile",
        default="services",
        help="the profile to assemble: Profiles/<profile>.json "
        "(default: services)",
    )
    assemble_parser.add_argument(
        "--profile-path",
        metavar="PATH",
        help="explicit profile path (overrides --profile)",
    )
    assemble_parser.add_argument(
        "--record",
        metavar="PATH",
        help="the resolution record to build from "
        "(default: the newest resolve record under Artifacts/records/)",
    )
    assemble_parser.add_argument(
        "--environment",
        default=str(DEFAULT_ENVIRONMENT),
        help="path to the environment mapping "
        "(default: .local/environment.json)",
    )
    assemble_parser.add_argument(
        "--stack",
        default=str(DEFAULT_STACK),
        help="path to the Stack tree of integration contracts "
        "(default: Stack/)",
    )
    assemble_parser.add_argument(
        "--artifacts",
        default=str(REPO_ROOT / "Artifacts"),
        help="untracked output root for bundles and records "
        "(default: Artifacts/)",
    )
    assemble_parser.add_argument(
        "--validate-profile",
        metavar="PATH",
        help="judge one profile document and say nothing else",
    )

    emulate_parser = verbs.add_parser(
        "emulate",
        help="run an assembly's members from the bundle, wait for their "
        "probes, prove coexistence, tear down, and record the verdicts",
    )
    emulate_parser.add_argument(
        "--record",
        metavar="PATH",
        help="the assembly record to emulate "
        "(default: the newest assemble record under Artifacts/records/)",
    )
    emulate_parser.add_argument(
        "--stack",
        default=str(DEFAULT_STACK),
        help="path to the Stack tree of integration contracts "
        "(default: Stack/)",
    )
    emulate_parser.add_argument(
        "--profiles",
        default=str(REPO_ROOT / "Profiles"),
        help="directory of profile documents (default: Profiles/)",
    )
    emulate_parser.add_argument(
        "--artifacts",
        default=str(REPO_ROOT / "Artifacts"),
        help="untracked root holding the bundle and receiving run "
        "directories and records (default: Artifacts/)",
    )
    emulate_parser.add_argument(
        "--ready-timeout",
        type=_positive_seconds,
        default=30.0,
        help="seconds to wait for a member's probe to pass (default: 30)",
    )
    emulate_parser.add_argument(
        "--terminate-grace",
        type=_positive_seconds,
        default=5.0,
        help="seconds between SIGTERM and SIGKILL at teardown (default: 5)",
    )

    admit_parser = verbs.add_parser(
        "admit",
        help="promote a clean chain into Releases/ — the one writer of the "
        "committed attestation tier, and the only step that refuses",
    )
    admit_parser.add_argument(
        "--version",
        required=True,
        help="the release version, also the Releases/<version>/ directory",
    )
    admit_parser.add_argument(
        "--record",
        metavar="PATH",
        help="the assembly record to admit "
        "(default: the newest assemble record under Artifacts/records/)",
    )
    admit_parser.add_argument(
        "--emulation",
        metavar="PATH",
        help="an emulation record whose health gates admission; omit to "
        "admit un-emulated (the release attests emulation: absent)",
    )
    admit_parser.add_argument(
        "--artifacts",
        default=str(REPO_ROOT / "Artifacts"),
        help="untracked root holding the chain records (default: Artifacts/)",
    )
    admit_parser.add_argument(
        "--releases",
        default=str(REPO_ROOT / "Releases"),
        help="tracked release tier (default: Releases/)",
    )
    return parser


def _newest_record(artifacts_root, pattern):
    records = sorted(
        Path(artifacts_root).glob(f"records/{pattern}"),
        key=lambda path: path.name)
    return records[-1] if records else None


def _judge(loader, path):
    _, errors = loader(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print(f"{path}: valid")
    return 0


def _main(argv=None):
    arguments = _build_parser().parse_args(argv)
    if arguments.verb == "preflight":
        return preflight.run(
            environment_path=arguments.environment,
            stack_root=arguments.stack,
            validate_only=arguments.validate_only,
            validate_integration=arguments.validate_integration,
            as_json=arguments.json,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if arguments.verb == "bootstrap":
        revisions_path = arguments.revisions if arguments.revisions \
            else str(REPO_ROOT / "Revisions" / f"{arguments.line}.json")
        return bootstrap.run(
            revisions_path=revisions_path,
            environment_path=arguments.environment,
            stack_root=arguments.stack,
            artifacts_root=arguments.artifacts,
            repo_root=REPO_ROOT,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if arguments.verb == "resolve":
        if arguments.validate_revisions is not None:
            return _judge(
                revisions_contract.load_revisions,
                arguments.validate_revisions)
        if arguments.validate_record is not None:
            return _judge(
                record_contract.load_record, arguments.validate_record)
        if arguments.validate_policy is not None:
            return _judge(
                policy_contract.load_policy, arguments.validate_policy)
        revisions_path = arguments.revisions if arguments.revisions \
            else str(REPO_ROOT / "Revisions" / f"{arguments.line}.json")
        return resolve.run(
            revisions_path=revisions_path,
            environment_path=arguments.environment,
            artifacts_root=arguments.artifacts,
            repo_root=REPO_ROOT,
            policy_root=arguments.policy,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if arguments.verb == "assemble":
        if arguments.validate_profile is not None:
            return _judge(
                profiles_contract.load_profile, arguments.validate_profile)
        profile_path = arguments.profile_path if arguments.profile_path \
            else str(REPO_ROOT / "Profiles" / f"{arguments.profile}.json")
        record_path = arguments.record
        if record_path is None:
            newest = _newest_record(arguments.artifacts, "resolve-*.json")
            if newest is None:
                print(
                    "no resolution record under Artifacts/records/ — "
                    "run resolve first", file=sys.stderr)
                return 2
            record_path = str(newest)
        return assemble.run(
            profile_path=profile_path,
            record_path=record_path,
            environment_path=arguments.environment,
            stack_root=arguments.stack,
            artifacts_root=arguments.artifacts,
            repo_root=REPO_ROOT,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if arguments.verb == "emulate":
        record_path = arguments.record
        if record_path is None:
            newest = _newest_record(arguments.artifacts, "assemble-*.json")
            if newest is None:
                print(
                    "no assembly record under Artifacts/records/ — "
                    "run assemble first", file=sys.stderr)
                return 2
            record_path = str(newest)
        return emulate.run(
            record_path=record_path,
            stack_root=arguments.stack,
            profiles_root=arguments.profiles,
            artifacts_root=arguments.artifacts,
            repo_root=REPO_ROOT,
            ready_timeout=arguments.ready_timeout,
            terminate_grace=arguments.terminate_grace,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    if arguments.verb == "admit":
        record_path = arguments.record
        if record_path is None:
            newest = _newest_record(arguments.artifacts, "assemble-*.json")
            if newest is None:
                print(
                    "no assembly record under Artifacts/records/ — "
                    "run assemble first", file=sys.stderr)
                return 2
            record_path = str(newest)
        return admit.run(
            version=arguments.version,
            assembly_record_path=record_path,
            emulation_record_path=arguments.emulation,
            artifacts_root=arguments.artifacts,
            releases_root=arguments.releases,
            repo_root=REPO_ROOT,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    raise AssertionError(f"unreachable verb: {arguments.verb}")


def main(argv=None):
    try:
        return _main(argv)
    except (OSError, filesystem.FilesystemContractError) as error:
        print(f"filesystem operation refused: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
