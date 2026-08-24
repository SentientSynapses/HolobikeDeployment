"""Load the per-repository contracts declared under Stack/, and resolve
where each declared deployable actually ends up.

A `destination` is either a reserved terminal (`device`, `server`) or the name
of the member whose artifact carries this one. Resolution follows that chain
to its terminal (D-19), so the question a release record needs answered —
*everything that contributed to this device build* — is one walk rather than a
second list somebody maintains.
"""

from __future__ import annotations

from pathlib import Path

from . import integration as integration_contract

TERMINALS = integration_contract.TERMINALS


def load_stack(stack_root):
    """Return ``(documents, errors)`` for one Stack tree.

    Completeness remains check's reporting responsibility. Lifecycle verbs
    need the stricter shared guarantees that every discovered leaf agrees
    with its directory, no integration appears twice, and every declared
    destination reaches a terminal.
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

    errors.extend(_destination_errors(documents))
    if errors:
        return None, errors
    return documents, []


def resolve_destination(documents, integration, deployable):
    """Follow a deployable's destination chain to its terminal.

    Returns ``(terminal, hops, errors)``. `hops` names the members the chain
    passed through, so a caller can say *why* something lands on a device.
    """
    hops = []
    seen = []
    name, current = integration, deployable
    while True:
        leaf = documents.get(name)
        if leaf is None:
            return None, tuple(hops), [
                f"{integration}.{deployable}: destination names {name!r}, "
                "which has no Stack leaf"]
        found = leaf.deployable(current)
        if found is None:
            return None, tuple(hops), [
                f"{integration}.{deployable}: {name!r} declares no "
                f"deployable {current!r}"]
        if found.is_terminal:
            return found.destination, tuple(hops), []

        step = (name, current)
        if step in seen:
            cycle = " -> ".join(f"{a}.{b}" for a, b in seen + [step])
            return None, tuple(hops), [
                f"{integration}.{deployable}: destination cycle {cycle}"]
        seen.append(step)

        carrier = documents.get(found.destination)
        if carrier is None:
            return None, tuple(hops), [
                f"{integration}.{deployable}: destination "
                f"{found.destination!r} has no Stack leaf"]
        landing = [d for d in carrier.deployables if d.is_terminal]
        if len(landing) != 1:
            return None, tuple(hops), [
                f"{integration}.{deployable}: {found.destination!r} has "
                f"{len(landing)} deployables that land somewhere, so which "
                "one carries this is undecidable"]
        hops.append(found.destination)
        name, current = found.destination, landing[0].name


def _destination_errors(documents):
    errors = []
    for integration in sorted(documents):
        for deployable in documents[integration].deployables:
            _, _, problems = resolve_destination(
                documents, integration, deployable.name)
            errors.extend(problems)
    return errors


def carried_by(documents, terminal):
    """Every ``(integration, deployable)`` that reaches `terminal`.

    Direct or through any number of carriers — which is what makes a device
    release record able to name the plugin revisions inside the package.
    """
    reached = []
    for integration in sorted(documents):
        for deployable in documents[integration].deployables:
            resolved, _, problems = resolve_destination(
                documents, integration, deployable.name)
            if not problems and resolved == terminal:
                reached.append((integration, deployable.name))
    return tuple(reached)
