"""The declared non-members, and the stray scan they make possible.

`Stack/nonmembers.json` names repositories adjacent to the stack that are
deliberately not members, each with a reason. It closes the roster into a
loop: a checkout in neither the roster nor this file is a *named problem*
rather than a discovery, and recording a repository here is a stronger
statement than silence — it says someone looked.

Canonical contract: `schemas/nonmembers.schema.json`.
"""

from __future__ import annotations

from pathlib import Path

from . import document, schema

SCHEMA_VERSION = 1
#: Where a nonmembers document sits, relative to the Stack root.
FILENAME = "nonmembers.json"


def load_nonmembers(path):
    """Return ``({repository: entry}, errors)`` for one declaration."""
    root, errors = document.read(path, schema.contract("nonmembers"))
    if errors:
        return None, errors
    return dict(root["nonmembers"]), []


def scan(search_roots, members, declared):
    """Classify every git checkout under `search_roots`.

    `members` is the set of member repository directory names, `declared` the
    non-member names. Returns a sorted list of the repositories in neither —
    which is the whole point: the answer should normally be empty, and when it
    is not, the repository has a name rather than being noticed by accident.
    """
    strays = []
    seen = set()
    for search_root in search_roots:
        root = Path(search_root)
        if not root.is_dir():
            continue
        for candidate in sorted(root.iterdir()):
            if not (candidate / ".git").exists():
                continue
            name = candidate.name
            if name in members or name in declared or name in seen:
                continue
            seen.add(name)
            strays.append({"repository": name, "path": str(candidate)})
    return strays


def search_roots(checkouts):
    """The parent directories of the declared checkouts.

    A stray is found by looking where members already live, so enrolling a
    repository in a new place extends the scan without configuring it.
    """
    roots = []
    for path in checkouts.values():
        parent = str(Path(path).parent)
        if parent not in roots:
            roots.append(parent)
    return sorted(roots)
