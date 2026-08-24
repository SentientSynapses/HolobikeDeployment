"""The `provision` verb: put something on a thing that already exists.

This is the one verb that touches a live system. `build` stops at the bytes —
a container image has bytes, a Terraform apply has none, and applying mutates
state that outlives every release (D-10). Keeping provisioning a separate verb
is what makes that boundary real: applying is never a side effect of building.

Today it installs the public device identity document into an offline root,
which is the only thing in this repository that already places something on a
device. Carrying an admitted build is Phase 5's work for `device` and Phase
6's for `server`; until then this verb says so rather than pretending.
"""

from __future__ import annotations

from . import device_identity

DESTINATIONS = ("device", "server")


def run(*, destination, identity_input, root, verify, stdout, stderr):
    """Execute provisioning; returns the process exit code."""
    if destination == "server":
        print("provisioning a server is not built yet — no server deployable "
              "in this repository has an artifact to place (see PLAN.md, "
              "Phase 6)", file=stderr)
        return 2

    if verify:
        argv = ["verify", "--root", str(root)]
    elif identity_input is not None:
        argv = ["install", "--root", str(root), "--input", str(identity_input)]
    else:
        print("nothing to provision: pass --identity to install a device "
              "identity document, or --verify to check one", file=stderr)
        return 2
    return device_identity.main(argv)
