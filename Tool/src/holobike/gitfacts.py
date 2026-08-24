"""Read-only git queries shared by the verbs.

Every function here observes; none mutates. A verb that needs to change a
checkout does not belong in this module.
"""

from __future__ import annotations

import subprocess


def git_query(checkout, *arguments):
    """Run one read-only git command; returns (stdout or None, first stderr line)."""
    result = subprocess.run(
        ["git", "-C", str(checkout), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        first = result.stderr.strip().splitlines()[0] if result.stderr else ""
        return None, first
    return result.stdout.strip(), ""
