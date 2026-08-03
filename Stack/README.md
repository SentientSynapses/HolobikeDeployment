# Stack

`Stack/` is the per-repository chapter of the specification: the software
this repository composes. The first level is a short HoloBike software domain,
mirroring the kit repositories that hold those sources (`ai_kit`, `bike_kit`,
`geo_kit`, `id_kit`, `os_kit`, `ue_kit`); its README owns compatibility among
the repositories in that domain. The leaf uses exact repository names and
owns one deployment-facing source adapter contract.

```text
Stack/<domain>/<Repository>/
Stack/<domain>/<kind>/<Repository>/
```

A domain may insert one `<kind>` level, and only when its artifacts are
deployed differently rather than merely numerous. `ue/` is the case that earns
it: an engine is a build dependency, plugins are libraries synchronized against
a project, and the project is the packaged product — three deployment
behaviours, not one list. A domain whose repositories all deploy the same way
stays flat.

Repository directories contain integration contracts and declared integration
metadata. They are not clone destinations, submodules, or copies of source
trees — and they hold no executable adapter code. Declarations bind; the
Assembler executes. An adapter implementation lands under `Assembler/`, bound
to the contract it implements here.

| Domain | Repository integrations |
|---|---|
| `os` | [`uroborOS`](os/uroborOS/README.md) |
| `geo` | [`HexAtlas`](geo/HexAtlas/README.md), [`Assetscape`](geo/Assetscape/README.md) |
| `id` | [`AthleteIdentity`](id/AthleteIdentity/README.md) |
| `ue` | [`HolobikeExperience`](ue/project/HolobikeExperience/README.md), [`HolobikeDevice`](ue/plugins/HolobikeDevice/README.md), [`HolobikeRider`](ue/plugins/HolobikeRider/README.md), [`HolobikeWorlds`](ue/plugins/HolobikeWorlds/README.md) |
| `ai` | [`drAIs`](ai/drAIs/README.md) |
| `bike` | [`HolobikeCore`](bike/HolobikeCore/README.md) |

If a document names more than one repository — which revisions compose, which
versions are compatible, which gates admit a release — it lives beside
`Stack/`, not inside it: a revision manifest under `Revisions/`, a constraint
under `Policy/`. What stays here is the contract for driving one repository
and what that repository exposes.

Third-party software is not a domain member. Toolchains such as the Unreal
engine and vcpkg are located by environment preflight and recorded as release
facts; only HoloBike-owned software appears under `Stack/`.

An integration contract may commit its adapter to:

- locate or fetch an explicitly selected source revision;
- invoke documented repository-owned build and test commands;
- validate expected artifact and protocol versions;
- stage published outputs into an assembly;
- provide configuration through declared inputs; and
- run product-level health checks.

It must not duplicate domain implementation, reach into private source modules
when a public command or artifact exists, silently edit a source checkout, or
make generated copies authoritative.

Every repository adapter should eventually expose the same minimum
information: source identity, dirty state, build entry point, artifact
inventory, runtime requirements, compatibility version, deployment
destination, health result, and redacted diagnostics.
