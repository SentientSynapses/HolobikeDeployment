"""Assembly bundle inventory and verification."""

from __future__ import annotations

from . import filesystem


def verify_bundle(artifacts_root, assembly):
    """Return ``(bundle_root, problems)`` after checking every staged byte."""
    problems = []
    try:
        bundle_root = filesystem.resolve_beneath(
            artifacts_root, assembly["bundle"], kind="directory")
    except (OSError, filesystem.FilesystemContractError) as error:
        return None, [f"bundle: {error}"]

    for name, entries in sorted(assembly["artifacts"].items()):
        for entry in entries:
            relative = entry["path"]
            try:
                parts = filesystem.relative_parts(relative)
                if parts[0] != name:
                    raise filesystem.FilesystemContractError(
                        f"artifact is filed under {parts[0]!r}, expected "
                        f"{name!r}")
                path = filesystem.resolve_beneath(
                    bundle_root, relative, kind="file")
            except (OSError, filesystem.FilesystemContractError) as error:
                problems.append(f"artifact {relative}: {error}")
                continue
            actual_size = path.stat().st_size
            if actual_size != entry["bytes"]:
                problems.append(
                    f"artifact {relative}: size is {actual_size}, "
                    f"recorded {entry['bytes']}")
                continue
            actual_digest = filesystem.sha256_file(path)
            if actual_digest != entry["sha256"]:
                problems.append(
                    f"artifact {relative}: digest does not match "
                    "the assembly record")
    return bundle_root, problems
