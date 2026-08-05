"""Load the per-repository contracts declared under Stack/."""

from __future__ import annotations

from pathlib import Path

from . import integration as integration_contract


def load_stack(stack_root):
    """Return ``(documents, errors)`` for one Stack tree.

    Completeness remains preflight's reporting responsibility. Lifecycle
    verbs need the stricter shared guarantees that every discovered leaf
    agrees with its directory and no integration appears twice.
    """
    root = Path(stack_root)
    if not root.is_dir():
        return None, [f"{root}: Stack root is not a directory"]

    documents = {}
    errors = []
    for path in sorted(root.glob("**/integration.json")):
        document, leaf_errors = integration_contract.load_integration(path)
        if leaf_errors:
            errors.extend(f"{path}: {error}" for error in leaf_errors)
            continue
        directory_name = path.parent.name
        if document.integration != directory_name:
            errors.append(
                f"{path}: integration {document.integration!r} does not "
                f"match directory {directory_name!r}")
            continue
        previous = documents.get(document.integration)
        if previous is not None:
            errors.append(
                f"{path}: duplicate Stack leaf for {document.integration}")
            continue
        documents[document.integration] = document

    if errors:
        return None, errors
    return documents, []
