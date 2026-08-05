"""Gate evaluation: pure source comparisons, no side effects.

A gate's verdict is a fact block that rides the resolution record. Nothing
here refuses anything — refusal on a failed gate is admission's job. Where
a gate cannot be evaluated (a missing checkout, a missing subtree) the
verdict is skipped-with-reason, and a skip is a problem: a gate that
silently cannot run reads as coverage that does not exist.
"""

from __future__ import annotations

from pathlib import Path

from . import filesystem

# Mismatch listings are capped, loudly: the counts are always complete and
# the truncated figure says exactly what was withheld. No silent caps.
MISMATCH_LISTING_CAP = 50


def _tree_files(root, exclude):
    files = {}
    excluded = set(exclude)
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if excluded.intersection(relative.parts):
            continue
        files[str(relative)] = path
    return files


def _site_root(site, checkouts):
    if site.integration not in checkouts:
        return None, f"{site.integration}: no checkout declared"
    root = Path(checkouts[site.integration]) / site.path
    if not root.is_dir():
        return None, f"{site.integration}/{site.path}: not a directory"
    return root, ""


def evaluate_tree_parity(gate, checkouts):
    facts = {"kind": "tree_parity"}
    left_root, left_error = _site_root(gate.left, checkouts)
    right_root, right_error = _site_root(gate.right, checkouts)
    if left_root is None or right_root is None:
        facts["status"] = "skipped"
        facts["detail"] = left_error or right_error
        return facts

    left_files = _tree_files(left_root, gate.exclude)
    right_files = _tree_files(right_root, gate.exclude)
    only_left = sorted(set(left_files) - set(right_files))
    only_right = sorted(set(right_files) - set(left_files))
    differing = sorted(
        relative for relative in set(left_files) & set(right_files)
        if filesystem.sha256_file(left_files[relative])
        != filesystem.sha256_file(right_files[relative]))

    mismatches = (
        [f"only left: {path}" for path in only_left]
        + [f"only right: {path}" for path in only_right]
        + [f"differs: {path}" for path in differing]
    )
    facts["counts"] = {
        "compared": len(set(left_files) & set(right_files)),
        "only_left": len(only_left),
        "only_right": len(only_right),
        "differing": len(differing),
    }
    facts["mismatches"] = mismatches[:MISMATCH_LISTING_CAP]
    facts["truncated"] = max(0, len(mismatches) - MISMATCH_LISTING_CAP)
    facts["status"] = "fail" if mismatches else "pass"
    return facts
