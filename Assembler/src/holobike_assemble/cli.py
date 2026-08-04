"""The holobike-assemble command line.

The CLI is the Assembler's testable surface: suites drive these verbs and
nothing beneath them. Verbs land in the growth order the repository README
records; today there is one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import preflight

# .../Assembler/src/holobike_assemble/cli.py -> the repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ENVIRONMENT = REPO_ROOT / ".local" / "environment.json"


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
        "--validate-only",
        action="store_true",
        help="judge the environment document and say nothing else",
    )
    preflight_parser.add_argument(
        "--json",
        action="store_true",
        help="emit the report as JSON instead of a table",
    )
    return parser


def main(argv=None):
    arguments = _build_parser().parse_args(argv)
    if arguments.verb == "preflight":
        return preflight.run(
            environment_path=arguments.environment,
            validate_only=arguments.validate_only,
            as_json=arguments.json,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    raise AssertionError(f"unreachable verb: {arguments.verb}")


if __name__ == "__main__":
    sys.exit(main())
