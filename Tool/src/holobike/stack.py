"""Load the per-repository contracts declared under Stack/, and resolve
where each declared deployable actually ends up.

A `destination` is either a reserved terminal (`device`, `server`) or the name
of the member whose artifact carries this one. Resolution follows that chain
to its terminal (D-19), so the question a release record needs answered —
*everything that contributed to this device build* — is one walk rather than a
second list somebody maintains.
"""

from __future__ import annotations

import pathlib
from pathlib import Path

from . import integration as integration_contract

TERMINALS = integration_contract.TERMINALS


#: Documents at the Stack root that are not leaves.
NOT_A_LEAF = ("nonmembers.json",)


def leaves(stack_root):
    """Every integration contract under a Stack tree.

    A leaf is `<domain>/<Integration>.json`, named for the integration it
    declares — the file name is the identity, which is why `load_stack` holds
    the two together.
    """
    root = pathlib.Path(stack_root)
    return sorted(
        path for path in root.rglob("*.json")
        if path.name not in NOT_A_LEAF)


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
    for path in leaves(root):
        document, leaf_errors = integration_contract.load_integration(path)
        if leaf_errors:
            errors.extend(f"{path}: {error}" for error in leaf_errors)
            continue
        if document.integration != path.stem:
            errors.append(
                f"{path}: integration {document.integration!r} does not "
                f"match its file name {path.stem!r}")
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


def select(documents, profile):
    """Resolve a profile's selections against the Stack.

    Returns ``(selections, errors)``. Every selected deployable must exist,
    and its own destination must resolve to the profile's — a profile that
    put a server deployable in a device build would otherwise be caught by
    nothing until something failed to run in the wrong place.
    """
    errors = []
    for selection in profile.selections:
        leaf = documents.get(selection.integration)
        if leaf is None:
            errors.append(
                f"{selection.ref}: no Stack leaf for "
                f"{selection.integration}")
            continue
        if leaf.deployable(selection.deployable) is None:
            declared = ", ".join(sorted(d.name for d in leaf.deployables))
            errors.append(
                f"{selection.ref}: {selection.integration} declares no such "
                f"deployable (it declares {declared})")
            continue
        terminal, _, problems = resolve_destination(
            documents, selection.integration, selection.deployable)
        if problems:
            errors.extend(problems)
            continue
        if terminal != profile.destination:
            errors.append(
                f"{selection.ref}: resolves to {terminal!r}, but the "
                f"{profile.profile!r} profile is for {profile.destination!r}")
    if errors:
        return None, errors
    return profile.selections, []
