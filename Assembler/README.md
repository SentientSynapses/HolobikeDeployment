# Assembler

The Assembler is this repository's one executable: it turns the declarations
into staged artifacts and attested records. The CLI is `holobike-assemble`;
the implementation is a Python package under this directory (the uroborOS-Lab
idiom), growing one module per verb.

## Role

The Assembler is a consumer — of the declarations, and of the build, test,
package, and export commands each source repository documents and owns. It
must not copy their internal build logic, infer success from file existence
alone, silently edit a source checkout, or treat mutable branch names as
release identities. It is deliberately thin: the moment it starts resembling
a build system, the design has failed (`Docs/Decisions/0001`).

The first implementation begins with the versioned manifest schema and the
read-only `preflight`; artifact staging follows only after source identity
and compatibility checks are deterministic.

## Verbs

Verbs land in dependency order; each consumes the ones before it.

### `preflight` — read-only discovery

Validates `.local/environment.json` against
`Schemas/environment.schema.json`, normalizes and checks every declared path,
reports each integration's source revision and dirty state before any build
is invoked, and verifies the tools a selected workflow needs — compilers,
CMake, Ninja, vcpkg, Unreal Engine, virtualization, GPU tooling, storage
capacity, and access to any explicitly selected development provider. Safe to
run before anything is trusted, because it can change nothing.

### `resolve` — pin a declaration

Reads a revision manifest under `Revisions/`, pins exact commits, dirty
state, and digests, and writes a record into the untracked `Artifacts/`
directory. The record also carries this repository's own revision: a
resolution that cannot identify itself is not provenance.

### `assemble` — stage a product bundle

Consumes a resolved record and a profile; invokes repository-owned build
entry points declared in `Stack/`; stages artifacts without modifying any
source working tree; and produces a machine-readable inventory of source
revisions and artifact digests, build and integration results, a
compatibility report, and enough provenance to reproduce or reject the
assembly.

### `emulate` — validate an assembly without a bike

Runs an assembled bundle against simulated and virtualized dependencies:
booting uroborOS images in a VM, simulating drivetrain and handlebar
telemetry, exercising HolobikeDevice transport against simulated bike
services, running HexAtlas fixtures or bounded local atlas services, using
AthleteIdentity's development provider, running drAIs with explicit
development providers, and launching HolobikeExperience with a declared
plugin and data set.

Emulation orchestrates existing emulators, Labs, fixtures, and public
control surfaces — harness logic stays with the repository that owns the
underlying behavior unless the behavior exists only at the cross-repository
product boundary. **Emulation targets virtual machines only, never the
host** — a rule this ecosystem paid to learn. A run must record its assembly
identity, configuration, results, logs, and artifact locations, must label
simulated capabilities clearly, and is never evidence for hardware behavior
such as production NVIDIA, display, drivetrain, or handlebar performance.

### Admission

Admission is the Assembler promoting a validated record from `Artifacts/`
into `Releases/`, and it happens only when every gate under `Policy/`
passes. There is no other writer of `Releases/`.

## The environment mapping is data, not documentation

Checkout locations differ per workstation, so they are declared in
`.local/environment.json`, which is gitignored and never committed. The
committed artifacts are its schema and an example:

```text
Schemas/environment.schema.json    the contract
Schemas/environment.example.json   the shape, with example paths
.local/environment.json            your machine (untracked)
```

To set up a workstation, copy the example to `.local/environment.json` and
correct the paths. The schema closes the integration roster deliberately: a
misspelled name fails validation rather than silently deselecting an
integration. These paths are development defaults, not deployment contracts —
provisioning derives nothing from them.

## Rules

- Development runs may use local checkouts and disposable credentials, but
  must not silently weaken production policy.
- Generated files belong under the untracked repository-level `Artifacts/`
  directory (or a documented `Generated/` beneath this one) and are never
  committed.
- Secrets come from an external secret facility and are never written into a
  report or record.
