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
| Operating system | [`uroborOS`](Integrations/os/uroborOS/README.md) | Images, modes, services, boot policy, hardware integration |
| Geography | [`HexAtlas`](Integrations/geo/HexAtlas/README.md), [`Assetscape`](Integrations/geo/Assetscape/README.md) | World facts, asset palette, serving, and engine compatibility |
| Bike runtime | [`HolobikeCore`](Integrations/bike/HolobikeCore/README.md) | Device services, firmware, health, and hardware-facing configuration |
| Athlete identity | [`AthleteIdentity`](Integrations/id/AthleteIdentity/README.md) | On-device identity client, provider selection, and identity contracts |
| Intelligence | [`drAIs`](Integrations/ai/drAIs/README.md) | Local assistant runtime, skills, models, and sandbox policy |
| Experience | [`HolobikeExperience`](Integrations/ue/HolobikeExperience/README.md) | Packaged Unreal Engine product and project configuration |
| Unreal integrations | [`HolobikeDevice`](Integrations/ue/HolobikeDevice/README.md), [`HolobikeRider`](Integrations/ue/HolobikeRider/README.md), [`HolobikeWorlds`](Integrations/ue/HolobikeWorlds/README.md) | Reusable engine plugins and compatibility with the experience |

## Repository Shape

```text
Integrations/
  os/
    uroborOS/
  geo/
    HexAtlas/
    Assetscape/
  id/
    AthleteIdentity/
  ue/
    HolobikeExperience/
    HolobikeDevice/
    HolobikeRider/
    HolobikeWorlds/
  ai/
    drAIs/
  bike/
    HolobikeCore/
Developer/
  Assembly/      deterministic source selection, build invocation, and staging
  Emulation/     integrated simulated and virtualized product workflows
  Environment/   developer-host discovery, prerequisites, and local mapping
Production/
  Provisioning/  release installation, enrollment, validation, and evidence
```

`Developer/Assembly/` is the domain. A future `holobike-assemble` command may
serve as its CLI, but the implementation should remain a consumer of declared
manifests and repository-owned tools rather than becoming another build
system.

## Initial State

This first commit establishes role boundaries and records the current source
repositories. It intentionally adds no submodules, source vendoring, deployment
credentials, or executable production workflow. Revision manifests and
automation should be introduced only after their schemas and release semantics
are decided.
