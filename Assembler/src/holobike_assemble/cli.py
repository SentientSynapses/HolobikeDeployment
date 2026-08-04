"""The holobike-assemble command line.

The CLI is the Assembler's testable surface: suites drive these verbs and
nothing beneath them. Verbs land in the growth order the repository README
records; today there is one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import policy as policy_contract
from . import preflight
from . import record as record_contract
from . import resolve
from . import revisions as revisions_contract

# .../Assembler/src/holobike_assemble/cli.py -> the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENVIRONMENT = REPO_ROOT / ".local" / "environment.json"
DEFAULT_STACK = REPO_ROOT / "Stack"


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
    return parser


def _judge(loader, path):
    _, errors = loader(path)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 2
    print(f"{path}: valid")
    return 0


def main(argv=None):
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
    raise AssertionError(f"unreachable verb: {arguments.verb}")


if __name__ == "__main__":
    sys.exit(main())
