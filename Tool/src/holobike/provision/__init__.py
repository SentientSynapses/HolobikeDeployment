"""The `provision` verb: put something on a thing that already exists.

This is the one verb that touches a live system. `build` stops at the bytes —
a container image has bytes, a Terraform apply has none, and applying mutates
state that outlives every release (D-10). Keeping provisioning a separate verb
is what makes that boundary real: applying is never a side effect of building.

It takes a profile, as `build` does (D-23): a profile is what is deployed
together, by one operation, to one place, and provisioning is that operation.
`device` installs the public device identity document into an offline root,
the only thing in this repository that already places something on a device.
A server profile is refused today, and the refusal is specific: for each of
its deployables, whether it builds to bytes here and that no way to place
them is declared — the reason being the leaf's to give, in its own `.md`.
Carrying an admitted build is Phase 5's work for `device` and Phase 6's for
the estate; until then this verb says so rather than pretending.
"""

from __future__ import annotations

from pathlib import Path

from .. import profiles as profiles_contract
from .. import stack as stack_contract
from . import device_identity


def _refuse_server(profile, selections, documents, stack_root, stderr):
    """Say, per deployable, what stands between its declaration and a
    provisioned estate. Nothing here is a verdict on the member: it reports
    the declaration, and points at the leaf's own account of the gap."""
    print(f"provisioning {profile.profile} is refused: nothing in it can be "
          "placed yet", file=stderr)
    for selection in selections:
        leaf = documents[selection.integration]
        deployable = leaf.deployable(selection.deployable)
        state = ("builds to bytes here, and declares no way to place them"
                 if deployable.artifacts else "declares no build here")
        # Named as a person would open it: from the repository, not from
        # wherever the stack root happens to be mounted.
        account = Path(Path(stack_root).name) / leaf.domain \
            / f"{leaf.integration}.md"
        print(f"  {selection.ref}: {state} — see {account}", file=stderr)
    return 2


def run(*, profile_path, stack_root, identity_input, root, verify, stdout,
        stderr):
    """Execute provisioning; returns the process exit code."""
    path = Path(profile_path)
    if not path.is_file():
        print(f"no profile {path.stem!r}: {path} does not exist", file=stderr)
        return 2
    profile, errors = profiles_contract.load_profile(path)
    if errors:
        for error in errors:
            print(f"{path}: {error}", file=stderr)
        return 2
    documents, errors = stack_contract.load_stack(stack_root)
    if not errors:
        selections, errors = stack_contract.select(documents, profile)
    if errors:
        for error in errors:
            print(error, file=stderr)
        return 2

    if profile.destination == "server":
        return _refuse_server(
            profile, selections, documents, stack_root, stderr)

    if verify:
        argv = ["verify", "--root", str(root)]
    elif identity_input is not None:
        argv = ["install", "--root", str(root), "--input", str(identity_input)]
    else:
        print("nothing to provision: pass --identity to install a device "
              "identity document, or --verify to check one", file=stderr)
        return 2
    return device_identity.main(argv)
