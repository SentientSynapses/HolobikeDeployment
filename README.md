# HoloBike Deployment

HoloBike Deployment is the integration and delivery repository for the HoloBike
software stack. It composes versioned outputs from the domain repositories into
developer environments, emulated systems, release candidates, and provisioned
HoloBike devices.

This is an aggregator, not a source monorepo. Each source repository remains
authoritative for its own implementation, tests, and domain decisions. This
repository owns the contracts between those repositories and the evidence that
a selected set of revisions works as one product.

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
| Operating system | [`uroborOS`](Spec/Stack/os/uroborOS/README.md) | Images, modes, services, boot policy, hardware integration |
| Geography | [`HexAtlas`](Spec/Stack/geo/HexAtlas/README.md), [`Assetscape`](Spec/Stack/geo/Assetscape/README.md) | World facts, asset palette, serving, and engine compatibility |
| Bike runtime | [`HolobikeCore`](Spec/Stack/bike/HolobikeCore/README.md) | Device services, firmware, health, and hardware-facing configuration |
| Athlete identity | [`AthleteIdentity`](Spec/Stack/id/AthleteIdentity/README.md) | On-device identity client, provider selection, and identity contracts |
| Intelligence | [`drAIs`](Spec/Stack/ai/drAIs/README.md) | Local assistant runtime, skills, models, and sandbox policy |
| Experience | [`HolobikeExperience`](Spec/Stack/ue/project/HolobikeExperience/README.md) | Packaged Unreal Engine product and project configuration |
| Unreal integrations | [`HolobikeDevice`](Spec/Stack/ue/plugins/HolobikeDevice/README.md), [`HolobikeRider`](Spec/Stack/ue/plugins/HolobikeRider/README.md), [`HolobikeWorlds`](Spec/Stack/ue/plugins/HolobikeWorlds/README.md) | Reusable engine plugins and compatibility with the experience |

## Repository Shape

```text
Spec/             intent: the specification of the deployed HoloBike software stack
  Schemas/          canonical shape of every declared kind
  Stack/            the integration roster and per-repository contracts
    os/
      uroborOS/
    geo/
      HexAtlas/
      Assetscape/
    id/
      AthleteIdentity/
    ue/
      plugins/
        HolobikeDevice/
        HolobikeRider/
        HolobikeWorlds/
      project/
        HolobikeExperience/
    ai/
      drAIs/
    bike/
      HolobikeCore/
Development/      process: workflows run before a release is admitted to production
  Assembly/      deterministic source selection, build invocation, and staging
  Emulation/     integrated simulated and virtualized product workflows
  Environment/   developer-host discovery, prerequisites, and local mapping
Production/       process: the admission and delivery boundary
  Provisioning/  release installation, enrollment, validation, and evidence
Releases/         fact: what was produced and what admitted it
```

The top level divides by nature — intent, process, fact. Two directories carry
the repository's stated purpose of owning "the contracts between those
repositories and the evidence that a selected set of revisions works as one
product": `Spec/` is the contracts, declared by a person and reviewed;
`Releases/` is the evidence, resolved by a run and never edited. Within the
Spec, one rule files everything: a document that names more than one
repository is a Spec kind; a document that describes how to drive one
repository belongs to that repository's adapter under `Spec/Stack/`.

Third-party toolchains are not stack members. The Unreal engine is located and
validated by environment preflight and recorded as a release fact; it is not
HoloBike software and has no integration directory under `Spec/Stack/`.

`Development/Assembly/` is the domain. A future `holobike-assemble` command
may serve as its CLI, but the implementation should remain a consumer of the
declared Spec and repository-owned tools rather than becoming another build
system.

## Growth Order

The order follows from `Development/Assembly/README.md`, which asks for "a
versioned manifest schema and a read-only preflight command" before anything
stages an artifact:

1. **Schemas and the environment mapping** — the first declared kind, so
   workstation paths become validated data instead of documentation.
2. **Read-only preflight** — discover checkouts, report revision and dirty
   state, validate tools. No side effects, so it is safe to build first.
3. **Revision selection and compatibility** — a release line becomes a
   reviewable diff.
4. **Assembly staging with an inventory and digests** — the first real release
   record.
5. **Emulation** orchestrated against a recorded assembly identity.
6. **Provisioning**, which its own README correctly blocks behind the uroborOS
   image, encrypted-root path, key custody, rollback, recovery, and hardware
   acceptance gates.

Every workflow emits a record from step 1 onward. The cheapest moment to make
provenance mandatory is before any workflow exists.

Two decisions are deliberately still open: the implementation language for the
executable layer, and exactly what a release record must contain. Neither is
blocked by the structure above, because schemas are language-neutral and the
record's schema lands with the first assembly that writes one.

## Initial State

This first commit establishes role boundaries and records the current source
repositories. It intentionally adds no submodules, source vendoring, deployment
credentials, or executable production workflow. Revision manifests and
automation should be introduced only after their schemas and release semantics
are decided.
