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
| `id` | [`AthleteIdentity`](id/AthleteIdentity/README.md), [`AthleteInsights`](id/AthleteInsights/README.md) |
| `ue` | [`HolobikeExperience`](ue/project/HolobikeExperience/README.md), [`HolobikeDevice`](ue/plugins/HolobikeDevice/README.md), [`HolobikeRider`](ue/plugins/HolobikeRider/README.md), [`HolobikeWorlds`](ue/plugins/HolobikeWorlds/README.md), [`HoloviewDisplay`](ue/plugins/HoloviewDisplay/README.md) |
| `ai` | [`drAIs`](ai/drAIs/README.md) |
| `bike` | [`HolobikeCore`](bike/HolobikeCore/README.md) |

If a document names more than one repository — which revisions compose, which
versions are compatible, which gates admit a release — it lives beside
`Stack/`, not inside it: a revision manifest under `Revisions/`, a constraint
under `Policy/`. What stays here is the contract for driving one repository
and what that repository exposes.

## What makes a repository a member

**A member's code reaches a deployment destination — as its own artifact, or
inside another member's.**

That is the whole test, and it is checkable rather than a matter of taste.
Every deployable declares a `destination`: `device`, `server`, or the name of
another member whose artifact carries it. The five UE plugins pass on the
second clause — UBT compiles them into HolobikeExperience's package, which is
why they have no artifacts of their own and why that is honest rather than an
omission.

A repository this repository merely *checks out* is not thereby a member.
Development tooling, migration scaffolding and anything with a deletion
condition ships nowhere, so it has no destination to declare and cannot be
expressed as one. Those are recorded in `nonmembers.json` with a reason, which
is a stronger statement than silence: it says someone looked.

The rule exists because it was missing. Thirteen members accumulated on
judgement alone, and the first case where "checked out" and "deployed"
genuinely diverged — `HolobikeMigration`, a plugin whose every module exists
to be deleted — was very nearly enrolled, because membership was the only way
to attach a parity gate to it. Gates follow from membership. Membership does
not follow from wanting a gate.

Third-party software is not a domain member either. Toolchains such as the
Unreal engine and vcpkg are located by environment preflight and recorded as
release facts; only HoloBike-owned software appears under `Stack/`.

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
