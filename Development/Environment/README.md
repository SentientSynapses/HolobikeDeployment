# Development Environment

Environment integration discovers local source checkouts and validates the
tools required to assemble and emulate HoloBike.

## The mapping is data, not documentation

Checkout locations differ per workstation, so they are declared in
`.local/environment.json`, which is gitignored and never committed. The
committed artifacts are its schema and an example:

```text
Spec/Schemas/environment.schema.json    the contract
Spec/Schemas/environment.example.json   the shape, with example paths
.local/environment.json                      your machine (untracked)
```

To set up a workstation, copy the example to `.local/environment.json` and
correct the paths. The schema closes the integration roster deliberately: a
misspelled name fails validation rather than silently deselecting an
integration.

These paths are development defaults, not deployment contracts. Production
provisioning derives nothing from them.

## Preflight

Preflight is the first thing this repository should be able to execute, and it
is read-only by design: it must be safe to run before anything is trusted.

It should normalize and validate every declared path, report each integration's
source revision and dirty state before any build is invoked, and check the
tools a selected workflow needs — compilers, CMake, Ninja, vcpkg, Unreal
Engine, virtualization, GPU tooling, storage capacity, and access to any
explicitly selected development provider.

Third-party toolchains are declared under `toolchains` rather than as members
of the stack under `Spec/Stack/`, because they are not HoloBike software. The Unreal engine is the
clearest case: preflight locates and validates it, a release records the
version that produced the build, and no part of it is an integrated component.

Secrets must come from an external secret facility and must never be written
into an environment report.
