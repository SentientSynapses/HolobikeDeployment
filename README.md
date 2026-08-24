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

**Where a new thing goes:** selects a version → `Revisions/`;
drives one repository → its `Stack/` leaf; shapes documents → `schemas/`;
executes → `Tool/`; written by a run → `Releases/`. Two tests keep the
boundary honest. The **nature test**: declared content is reviewable without
executing anything, realized content has side effects, attested content is
written by a run. The **scope test**: this repository specifies the *product*,
so a tool's own contract lives beside the tool (`Tool/README.md`), exactly
as each domain repository keeps its own documentation.

## Responsibilities

HoloBike Deployment owns, or is the designated owner as delivery expands:

- selection of compatible source revisions;
- cross-repository compatibility and the deployed-stack specification;
- developer environment discovery and check;
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
| Operating system | [`uroborOS`](Stack/os/uroborOS.md) | Images, modes, services, boot policy, hardware integration |
| Geography | [`HexAtlas`](Stack/geo/HexAtlas.md), [`Assetscape`](Stack/geo/Assetscape.md) | World facts, asset palette, serving, and engine compatibility |
| Bike runtime | [`HolobikeCore`](Stack/bike/HolobikeCore.md) | Device services, firmware, health, and hardware-facing configuration |
| Athlete identity | [`AthleteIdentity`](Stack/id/AthleteIdentity.md), [`AthleteInsights`](Stack/id/AthleteInsights.md) | On-device identity client, provider selection, identity contracts, and durable custody of completed sessions |
| Intelligence | [`drAIs`](Stack/ai/drAIs.md) | Local assistant runtime, skills, models, and sandbox policy |
| Experience | [`HolobikeExperience`](Stack/ue/project/HolobikeExperience.md) | Packaged Unreal Engine product and project configuration |
| Unreal integrations | [`HolobikeDevice`](Stack/ue/plugins/HolobikeDevice.md), [`HolobikeRider`](Stack/ue/plugins/HolobikeRider.md), [`HolobikeWorlds`](Stack/ue/plugins/HolobikeWorlds.md), [`HoloviewDisplay`](Stack/ue/plugins/HoloviewDisplay.md), [`OrielUI`](Stack/ue/plugins/OrielUI.md) | Reusable engine plugins and compatibility with the experience |

## Repository Shape

The top level partitions by function — every directory is one role, and
stages (development versus production) are properties of data, never
directories:

```text
Stack/            declare the members: roster, non-members, one file per repository
Revisions/        declare the versions: selected revisions per line
Profiles/         declare the slice: which deployables, and where they are going
Tool/             realize: check | env | build | provision
Releases/         attest: admitted records, written by runs, never edited
```

Two tiers declare the composition, one declares the members, one executes,
one records. `Policy/` retired with the parity gates it existed to hold: D-08
made dual-copy drift impossible rather than detectable, so there was nothing
left to gate. A constraint tier returns when a constraint exists that
revision selection cannot express. `Tool/` carries its own
contract — `src/holobike/schemas/` — and its own fixtures, because a tool's
contract lives beside the tool; that is the scope test applied to the thing
that enforces it. Provisioning is a verb of that tool rather than a tier
beside it.

Generated bundles, emulation state, logs, and pre-admission records live under
the gitignored `Artifacts/` output root. Cross-repository version constraints
will earn a separate `Compatibility/` declaration only when a concrete
constraint cannot be expressed by revision selection or policy.

**The filing rule:** if it selects a version, it is a revision manifest under
`Revisions/`; if it drives one repository, it
is that repository's leaf under `Stack/`; if it shapes other documents, it is
a schema and lives with the tool that enforces it; if it selects a runnable
product slice, it is a
profile. Only the tool executes; only `admit` writes to `Releases/`.

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

- Declarations never execute. Executable code lives in `Tool/`, as a
  consumer of the declarations and of repository-owned entry points.
- Validation ownership is tiered: each repository proves its own behavior
  in-repo; this repository proves only the composition; the transitional
  `*-Lab` repositories are scaffolding, never load-bearing.
- Schemas are canonical; a validator in any language is a binding that must
  agree with them, proven by fixtures under `Tool/tests/fixtures/`.
- "Manifest" names exactly one declared kind — the revision manifest. A
  release record resolves a manifest rather than being one.
- A declared document never contains a secret, a credential, or a private
  key — not even a path to one that would be meaningful off this machine.
- A mutable branch name is not a release identity. Declarations may select by
  branch for development lines; a release line resolves to exact commits.
- Machine-specific documents are not committed. `schemas/environment.schema.json`
  describes one workstation's checkout and toolchain paths; the document
  itself lives at the gitignored `.local/environment.json`.

Third-party toolchains are not stack members. The Unreal engine is located
and validated by check and recorded as a release fact; it is not HoloBike
software and has no integration directory under `Stack/`.

Located is not the same as correct. An integration that owns an Unreal project
declares it as `unreal_project`, and check holds that project's
`EngineAssociation` against the declared engine's own
`Engine/Build/Build.version`. A workstation carrying two engines answers
"present" to either of them, so presence alone once let the mapping name one
engine while the project asked for another — the agreement is the fact worth
reporting.

## Lifecycle

The lifecycle is ordered and evidence-carrying:

1. **`check`** validates declarations, checkouts, tools, and dirty state
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
Admission copies the complete record chain into `Releases/`; check is a
read-only report rather than an attestation.

## Current State

The complete lifecycle is implemented and covered through its CLI
seam. Schemas and conformance corpora cover environment, integration,
revision, policy, profile, and five run-record kinds. Parent records and
staged artifacts are digest-bound; admission rejects dirty source or
deployment state, failed or absent gates, incomplete builds, unhealthy
emulation, chain drift, and changed artifact bytes.

There are two profiles, one per destination: `device` selects the thirteen
deployables that reach a bike — five of them through HolobikeExperience's
package — and `server` selects the five that reach the estate. Emulation
exercises whichever of them declare a serve and a probe, today
AthleteIdentity's `IdentityClient`, in bounded host mode; the rest are
recorded absences and are skipped by name rather than silently.
HolobikeCore now declares repository-owned prove/package outputs in its Stack
leaf, but joins a profile only after its source checkout is clean enough to
produce meaningful provenance. OS, graphical, privileged, and hardware claims
remain VM or physical-device work, not host-service emulation claims.

Provisioning has one deliberately narrow executable: install or verify the
closed, public HoloBike device identity beneath an explicit offline root.
Image deployment, encrypted-root release delivery, key custody, rollback,
recovery, and physical acceptance remain later provisioning gates.
