# Profiles

Named compositions: which integrations a bundle carries and how its
composition validation runs. `integrations` is the exact assembly roster;
`topology` must address only members of that roster.

A profile may declare a non-secret environment overlay for each topology
member. `run: host` is the only implemented mode and is deliberately limited
to disposable, unprivileged user-space services running from staged bundle
artifacts with isolated state. OS, graphical, privileged, and hardware-facing
topologies require a future VM executor; they must not be represented as host
mode in the interim.

`services` currently contains the AthleteIdentity sidecar. HolobikeCore's
Stack leaf declares its repository-owned prove/package command and rootfs
artifact, but it does not join this profile until its source is clean and it
publishes the service/probe surface needed for composition emulation.
