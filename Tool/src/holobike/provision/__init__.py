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
        # One server deployable builds — AthleteIdentity's IdentityServer —
        # and what it builds is a base image its own repository says cannot
        # start in production, because it deliberately contains no device
        # authenticator. Applying its Terraform module against that image is
        # refused by the module itself. The gap is a project decision, not a
        # missing verb, so this says which one rather than failing vaguely.
        print("provisioning a server is refused: the only server deployable "
              "that builds is AthleteIdentity.IdentityServer, and it builds a "
              "BASE image that cannot start in production — its Terraform "
              "module will not create Cloud Run until container_image names a "
              "derived image carrying a device authenticator. That derivation "
              "is one of seven project-owned readiness items AthleteIdentity "
              "lists and none of them exists yet. See "
              "Stack/id/AthleteIdentity.md.", file=stderr)
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
