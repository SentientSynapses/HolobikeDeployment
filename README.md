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
organized by role (`Docs/Decisions/0001`).

## Responsibilities

HoloBike Deployment will own:

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
Policy/           declare the constraints: parity and admission gates
Schemas/          declare the shapes: canonical JSON Schema for every declared kind
Conformance/      prove the bindings: accepted and rejected fixtures per schema
Assembler/        realize: the one executable — preflight | resolve | assemble | emulate
Releases/         attest: admitted records, written by runs, never edited
Provisioning/     deliver: device-facing workflows behind the admission boundary
Docs/Decisions/   why the shape is what it is
```

Directories are created by their first content: `Revisions/`, `Policy/`, and
`Conformance/` are described here and in `Docs/Decisions/0001` rather than
scaffolded empty. `Profiles/` — named product and simulation topologies, the
declared answer to running the stack without a bike — and cross-repository
version constraints (`Compatibility/`) are future kinds on the same terms.

**The filing rule:** if it selects, it is a revision manifest under
`Revisions/`; if it constrains, it is policy; if it drives one repository, it
belongs to that repository's leaf under `Stack/`; if it shapes other
documents, it is a schema. Only the Assembler executes; only a run writes to
`Releases/`. Nothing else exists.

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
  `*-Lab` repositories are scaffolding, never load-bearing
  (`Docs/Decisions/0002`).
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

## Growth Order

The order follows from `Assembler/README.md`, which requires the versioned
manifest schema and the read-only preflight before anything stages an
artifact:

1. **Schemas and the environment mapping** — the first declared kind, so
   workstation paths become validated data instead of documentation.
2. **`preflight`** — the Assembler's first verb: discover checkouts, report
   revision and dirty state, validate tools. No side effects, so it is safe
   to build first.
3. **`bootstrap`** — materialize declared checkouts and repository-local
   tooling on a validated host; system tools are reported, never installed.
4. **Revision selection and compatibility** — a release line becomes a
   reviewable diff.
5. **`assemble` staging with an inventory and digests** — the first real
   release record.
6. **`emulate`** orchestrated against a recorded assembly identity.
7. **Provisioning**, which its own README correctly blocks behind the
   uroborOS image, encrypted-root path, key custody, rollback, recovery, and
   hardware acceptance gates.

Every workflow emits a record from step 1 onward. The cheapest moment to make
provenance mandatory is before any workflow exists.

## Current State

Documentation and schema only; the Assembler is not yet implemented. The
shape is settled by `Docs/Decisions/0001` and content arrives in growth
order. One decision remains deliberately open: exactly what a release record
must contain — its schema lands with the first `resolve` that writes one,
aligned with the uroborOS-Lab run-record idiom and SLSA provenance
vocabulary.
