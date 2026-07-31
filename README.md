# HoloBike Deployment

HoloBike Deployment is the integration and delivery repository for the HoloBike
software stack. It composes versioned outputs from the domain repositories into
developer environments, emulated systems, release candidates, and provisioned
HoloBike devices.

This is an aggregator, not a source monorepo. Each facet remains authoritative
for its own implementation, tests, and domain decisions. This repository owns
the contracts between those facets and the evidence that a selected set of
revisions works as one product.

## Responsibilities

HoloBike Deployment will own:

- selection of compatible facet revisions;
- cross-repository compatibility and deployment manifests;
- developer environment discovery and preflight;
- deterministic invocation of facet-owned build and test entry points;
- assembly of named artifacts into an inspectable product bundle;
- integrated emulation and end-to-end validation;
- production provisioning workflows and deployment evidence; and
- release provenance, including source revisions and artifact digests.

It does not own domain implementation, generated build trees, private signing
keys, athlete credentials, provider secrets, or device-specific secret values.

## Software Facets

| Facet | Authoritative repository | Deployment concern |
|---|---|---|
| Operating system | `uroborOS` | Images, modes, services, boot policy, hardware integration |
| Geography | `HexAtlas` | Atlas production, serving, client data, and world-data compatibility |
| Bike runtime | `HolobikeCore` | Device services, firmware, health, and hardware-facing configuration |
| Athlete identity | `AthleteIdentity` | On-device identity client, provider selection, and identity contracts |
| Intelligence | `drAIs` | Local assistant runtime, skills, models, and sandbox policy |
| Experience | `HolobikeExperience` | Packaged Unreal Engine product and project configuration |
| Unreal integrations | `HolobikeDevice`, `HolobikeRider`, `HolobikeWorlds` | Reusable engine plugins and compatibility with the experience |

## Repository Shape

```text
Developer/
  Assembly/      deterministic facet selection, build invocation, and staging
  Emulation/     integrated simulated and virtualized product workflows
  Environment/   developer-host discovery, prerequisites, and local mapping
  Facets/        one integration boundary per source domain
Production/
  Provisioning/  release installation, enrollment, validation, and evidence
```

`Developer/Assembly/` is the domain. A future `holobike-assemble` command may
serve as its CLI, but the implementation should remain a consumer of declared
manifests and facet-owned tools rather than becoming another build system.

## Initial State

This first commit establishes role boundaries and records the current source
repositories. It intentionally adds no submodules, source vendoring, deployment
credentials, or executable production workflow. Revision manifests and
automation should be introduced only after their schemas and release semantics
are decided.
