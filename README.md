# HoloBike Deployment

HoloBike Deployment is the integration and delivery repository for the HoloBike
software stack. It composes versioned outputs from the domain repositories into
developer environments, emulated systems, release candidates, and provisioned
HoloBike devices.

This is an aggregator, not a source monorepo. Each source repository remains
authoritative for its own implementation, tests, and domain decisions. **This
repository is the specification of the deployed HoloBike software stack, the
machine that realizes it, and the record of what it realized.** There is no
wrapper directory holding "the spec" — the declarations are the repository,
organized by role.

**Where a new thing goes:** selects → `Revisions/`; constrains → `Policy/`;
drives one repository → its `Stack/` leaf; shapes documents → `Schemas/`;
executes → `Assembler/`; written by a run → `Releases/`. Two tests keep the
boundary honest. The **nature test**: declared content is reviewable without
executing anything, realized content has side effects, attested content is
written by a run. The **scope test**: this repository specifies the *product*,
so a tool's own contract lives beside the tool (`Assembler/README.md`), exactly
as each domain repository keeps its own documentation.

## Responsibilities

HoloBike Deployment owns, or is the designated owner as delivery expands:

- selection of compatible source revisions;
- cross-repository compatibility and the deployed-stack specification;
- developer environment discovery and preflight;
- deterministic invocation of repository-owned build and test entry points;
- assembly of named artifacts into an inspectable product bundle;
- integrated emulation and end-to-end validation;
- production provisioning workflows and deployment evidence; and
- release provenance, including source revisions and artifact digests.

It does not own domain implementation, generated build trees, private signing
keys, athlete credentials, provider secrets, or device-specific secret values.

## Integrated Software

| Domain | Authoritative repository | Deployment concern |
|---|---|---|
| Operating system | [`uroborOS`](Stack/os/uroborOS/README.md) | Images, modes, services, boot policy, hardware integration |
| Geography | [`HexAtlas`](Stack/geo/HexAtlas/README.md), [`Assetscape`](Stack/geo/Assetscape/README.md) | World facts, asset palette, serving, and engine compatibility |
| Bike runtime | [`HolobikeCore`](Stack/bike/HolobikeCore/README.md) | Device services, firmware, health, and hardware-facing configuration |
| Athlete identity | [`AthleteIdentity`](Stack/id/AthleteIdentity/README.md) | On-device identity client, provider selection, and identity contracts |
| Intelligence | [`drAIs`](Stack/ai/drAIs/README.md) | Local assistant runtime, skills, models, and sandbox policy |
| Experience | [`HolobikeExperience`](Stack/ue/project/HolobikeExperience/README.md) | Packaged Unreal Engine product and project configuration |
| Unreal integrations | [`HolobikeDevice`](Stack/ue/plugins/HolobikeDevice/README.md), [`HolobikeRider`](Stack/ue/plugins/HolobikeRider/README.md), [`HolobikeWorlds`](Stack/ue/plugins/HolobikeWorlds/README.md) | Reusable engine plugins and compatibility with the experience |

## Repository Shape

The top level partitions by function — every directory is one role, and
stages (development versus production) are properties of data, never
directories:

```text
Stack/            declare the members: roster + per-repository integration contracts
Revisions/        declare the composition: selected revisions per release line
Profiles/         declare the product slice and its emulation topology
Policy/           declare the constraints: parity and admission gates
Schemas/          declare the shapes: canonical JSON Schema for every declared kind
Conformance/      prove the bindings: accepted and rejected fixtures per schema
Assembler/        realize: preflight | bootstrap | resolve | assemble | emulate | admit
Releases/         attest: admitted records, written by runs, never edited
Provisioning/     deliver: device-facing workflows behind the admission boundary
```

Generated bundles, emulation state, logs, and pre-admission records live under
the gitignored `Artifacts/` output root. Cross-repository version constraints
will earn a separate `Compatibility/` declaration only when a concrete
constraint cannot be expressed by revision selection or policy.

**The filing rule:** if it selects, it is a revision manifest under
`Revisions/`; if it constrains, it is policy; if it drives one repository, it
belongs to that repository's leaf under `Stack/`; if it shapes other
documents, it is a schema; if it selects a runnable product slice, it is a
profile. Only the Assembler executes; only `admit` writes to `Releases/`.

## Declared and attested

The declarations state intent; `Releases/` attests fact. A revision manifest
says `AthleteIdentity @ main`; the release record says `AthleteIdentity @
5619c33, clean, sha256:…`. Same subject, two states — and the same discipline
the protocol repositories enforce as "no binding without a fixture": a
release record is to the declarations what a conformance run is to a schema,
evidence of agreement.

| | declarations | `Releases/` |
|---|---|---|
| Written by | a person, in a pull request | the assembler, from a run |
| States | intent | fact |
| Changes | when the product changes | never, once recorded |

## Rules

- Declarations never execute. Executable code lives in `Assembler/`, as a
  consumer of the declarations and of repository-owned entry points.
- Validation ownership is tiered: each repository proves its own behavior
  in-repo; this repository proves only the composition; the transitional
  `*-Lab` repositories are scaffolding, never load-bearing.
- Schemas are canonical; a validator in any language is a binding that must
  agree with them, proven by fixtures under `Conformance/`.
- "Manifest" names exactly one declared kind — the revision manifest. A
  release record resolves a manifest rather than being one.
- A declared document never contains a secret, a credential, or a private
  key — not even a path to one that would be meaningful off this machine.
- A mutable branch name is not a release identity. Declarations may select by
  branch for development lines; a release line resolves to exact commits.
- Machine-specific documents are not committed. `Schemas/environment.schema.json`
  describes one workstation's checkout and toolchain paths; the document
  itself lives at the gitignored `.local/environment.json`.

Third-party toolchains are not stack members. The Unreal engine is located
and validated by preflight and recorded as a release fact; it is not HoloBike
software and has no integration directory under `Stack/`.

## Lifecycle

The lifecycle is ordered and evidence-carrying:

1. **`preflight`** validates declarations, checkouts, tools, and dirty state
   without mutation.
2. **`bootstrap`** clones missing checkouts and fast-forwards only clean,
   on-branch repositories; everything else is recorded and left untouched.
3. **`resolve`** turns a revision manifest into exact source facts and policy
   verdicts.
4. **`assemble`** rechecks those facts around repository-owned builds and
   stages a digested profile bundle.
5. **`emulate`** verifies the staged bytes, runs the declared topology, and
   records health and teardown.
6. **`admit`** verifies the digest-bound chain and is the sole publisher of an
   immutable, self-contained release record.
7. **Provisioning** consumes admitted releases for physical-device delivery;
   its current executable scope is the bounded public device-identity
   primitive described in `Provisioning/README.md`.

`bootstrap` through `emulate` write immutable run records under `Artifacts/`.
Admission copies the complete record chain into `Releases/`; preflight is a
read-only report rather than an attestation.

## Current State

The complete Assembler lifecycle is implemented and covered through its CLI
seam. Schemas and conformance corpora cover environment, integration,
revision, policy, profile, and five run-record kinds. Parent records and
staged artifacts are digest-bound; admission rejects dirty source or
deployment state, failed or absent gates, incomplete builds, unhealthy
emulation, chain drift, and changed artifact bytes.

The current `services` profile contains AthleteIdentity and exercises its
repository-owned package, service, and health surfaces in bounded host mode.
HolobikeCore now declares repository-owned prove/package outputs in its Stack
leaf, but joins a profile only after its source checkout is clean enough to
produce meaningful provenance. OS, graphical, privileged, and hardware claims
remain VM or physical-device work, not host-service emulation claims.

Provisioning has one deliberately narrow executable: install or verify the
closed, public HoloBike device identity beneath an explicit offline root.
Image deployment, encrypted-root release delivery, key custody, rollback,
recovery, and physical acceptance remain later provisioning gates.
