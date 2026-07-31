# Integrations

The first level under `Integrations/` is a short HoloBike software domain. Its
README owns compatibility among the repositories in that domain. The second
level uses exact repository names and owns one deployment-facing source
adapter.

```text
Integrations/<domain>/<Repository>/
```

Repository directories contain integration contracts, manifests, and adapter
code. They are not clone destinations, submodules, or copies of source trees.

| Domain | Repository integrations |
|---|---|
| `os` | [`uroborOS`](os/uroborOS/README.md) |
| `geo` | [`HexAtlas`](geo/HexAtlas/README.md), [`Assetscape`](geo/Assetscape/README.md) |
| `id` | [`AthleteIdentity`](id/AthleteIdentity/README.md) |
| `ue` | [`HolobikeExperience`](ue/HolobikeExperience/README.md), [`HolobikeDevice`](ue/HolobikeDevice/README.md), [`HolobikeRider`](ue/HolobikeRider/README.md), [`HolobikeWorlds`](ue/HolobikeWorlds/README.md) |
| `ai` | [`drAIs`](ai/drAIs/README.md) |
| `bike` | [`HolobikeCore`](bike/HolobikeCore/README.md) |

An integration may:

- locate or fetch an explicitly selected source revision;
- invoke documented repository-owned build and test commands;
- validate expected artifact and protocol versions;
- stage published outputs into an assembly;
- provide configuration through declared inputs; and
- run product-level health checks.

It must not duplicate domain implementation, reach into private source modules
when a public command or artifact exists, silently edit a source checkout, or
make generated copies authoritative.

Every executable repository adapter should eventually expose the same minimum
information: source identity, dirty state, build entry point, artifact
inventory, runtime requirements, compatibility version, deployment
destination, health result, and redacted diagnostics.
