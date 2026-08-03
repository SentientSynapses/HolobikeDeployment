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
- cross-repository compatibility and deployment manifests;
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

```text
Stack/            the integrated software, grouped by domain
  os/
    uroborOS/
  geo/
    HexAtlas/
    Assetscape/
  id/
    AthleteIdentity/
  ue/
    engine/
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
Development/      workflows run before a release is admitted to production
  Assembly/      deterministic source selection, build invocation, and staging
  Emulation/     integrated simulated and virtualized product workflows
  Environment/   developer-host discovery, prerequisites, and local mapping
Production/       the admission and delivery boundary
  Provisioning/  release installation, enrollment, validation, and evidence
```

`Development/Assembly/` is the domain. A future `holobike-assemble` command may
serve as its CLI, but the implementation should remain a consumer of declared
manifests and repository-owned tools rather than becoming another build
system.

## Initial State

This first commit establishes role boundaries and records the current source
repositories. It intentionally adds no submodules, source vendoring, deployment
credentials, or executable production workflow. Revision manifests and
automation should be introduced only after their schemas and release semantics
are decided.
