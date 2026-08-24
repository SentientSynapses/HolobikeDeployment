# HoloBike Deployment — Plan

## What this is for

One CLI tool that turns declarations spanning thirteen repositories into
either a running development environment or a production build, for either
the HoloBike device or the server side.

That 2×2 is the whole product:

|  | device | server |
|---|---|---|
| **development** | `holobike env device` | `holobike env server` |
| **production** | `holobike build device` → `holobike provision device` | `holobike build server` → `holobike provision server` |

The value delivered is subtraction: thirteen repositories, six domains, two
operating systems, two engine versions and two deployment tiers, reduced to
one command with one argument. Every part of this repository earns its place
by making that command shorter, more honest, or more repeatable. Nothing
earns its place by making the declarations more elaborate.

## Where it stands (2026-08-23)

The machine works. `preflight → bootstrap → resolve → assemble → emulate →
admit` runs green, the dev line resolves 13/13 with its four parity gates
passing, a daily cadence keeps it honest, and 96 tests pass. M1–M10 of the
previous plan are complete and that numbering is retired here.

What it does not do is any of the four cells above.

| measured | |
|---|---|
| Declarations — the specification itself | **334 lines** |
| Tool source (Assembler + Provisioning) | 4,601 lines |
| Tests | 2,234 lines, 96 tests |
| Schemas | 842 lines |
| Conformance fixtures | 105 files |
| Prose | 1,800 lines |
| Tracked files | 194 |
| Declared artifacts | 4 |
| Release records ever written | **0** |

Roughly 23:1 machinery to specification. Three specific faults explain it,
and this plan is mostly about them.

**1. The specification is written twice, and the canonical half is inert.**
Every contract module opens with *"Canonical contract:
`Schemas/X.schema.json`."* Nothing loads those files — there is no schema
library anywhere in the source or the tests. Enforcement is 1,419 lines of
hand-written Python validators, and the 105-fixture corpus exists to keep the
inert canonical half agreeing with the live secondary half. One field change
costs a JSON edit, a Python edit, a fixture sweep and a version constant, in
six places. That, not the preciousness of a version constant, is why the
previous plan queued four milestones behind one batched schema sweep.

**2. The verbs are a pipeline exposed as an interface.** Six verbs are six
stages of one operation, and a person is made to drive them individually.
Nobody wants to run `admit` by hand. Meanwhile there is no verb for the thing
a developer needs daily, and no verb for putting a build on a bike —
`provision-device-identity` is a separate executable that installs an
identity document and nothing else.

**3. The tiers outgrew the content.** Nine top-level directories for 334
lines of declaration. `Revisions/`, `Profiles/` and `Policy/` hold one
document each, and `Policy/`'s is scheduled for deletion. The filing rule,
the nature test and the scope test exist to route documents between tiers
that hold a single file apiece.

## The shape

Five top-level directories: three declare, one executes, one records.

```text
HolobikeDeployment/
├── README.md            what this is, the four verbs, the membership rule
├── PLAN.md              this file — forward only
├── DECISIONS.md         the ledger of decisions not yet landed in code
│
├── Stack/               WHAT the parts are — one file per repository
│   ├── README.md            roster + membership rule
│   ├── nonmembers.json      adjacent repositories deliberately out, with reasons
│   ├── ai/drAIs.json .md
│   ├── bike/HolobikeCore.json .md
│   ├── geo/HexAtlas.json .md   Assetscape.json .md
│   ├── id/AthleteIdentity.json .md   AthleteInsights.json .md
│   ├── os/uroborOS.json .md
│   └── ue/
│       ├── projects/HolobikeExperience.json .md
│       └── plugins/{HolobikeDevice,HolobikeRider,HolobikeWorlds,
│                    HoloviewDisplay,OrielUI}.json .md
│
├── Profiles/            WHICH parts, and how they wire — one per destination
│   ├── device.json
│   └── server.json
│
├── Revisions/           AT WHAT VERSION — one candidate composition per file
│   ├── dev.json
│   └── ue57.json
│
├── Tool/                the CLI, its contract included
│   ├── holobike
│   ├── src/holobike/
│   │   ├── cli.py
│   │   ├── check.py  env.py  build.py  provision/
│   │   ├── stack.py  profiles.py  revisions.py      loaders
│   │   ├── git.py  run.py  fs.py                    mechanics
│   │   └── schemas/*.schema.json                    the contract, now loaded
│   └── tests/  tests/fixtures/
│
└── Releases/            provenance written by `build`

    gitignored: Artifacts/  .local/
```

The three declaration tiers answer three different questions, and all three
are needed to build anything: `Stack/` — what exists and how to build it, one
repository per file. `Profiles/` — which of it is included and how it is
wired, one destination per file. `Revisions/` — at what version, one
candidate composition per file. Only the third varies with every re-pin,
which is why it is a tier and not a field: `dev` and `ue57` are the same
thirteen repositories at different refs, and either can back either profile.

### `destination` carries the 2×2

Every deployable declares where it goes. The value is `device`, `server`, or
**the name of another integration** — for code that reaches a destination
inside someone else's artifact.

```json
// Stack/id/AthleteIdentity.json
{
  "schema_version": 2,
  "integration": "AthleteIdentity", "domain": "id",
  "origin": "git@github.com:Saga-Holographic/AthleteIdentity.git",
  "deployables": {
    "IdentityClient": {
      "destination": "device",
      "build": [{ "argv": ["./IdentityClient/identityclient.sh", "build"] }],
      "artifacts": ["Builds/.../athleteidentity_service", ".../athleteidentity_cli"],
      "serve": { "argv": ["..."] }, "probe": { "argv": ["..."] }
    },
    "IdentityServer": {
      "destination": "server",
      "build": [{ "argv": ["./IdentityServer/build-image.sh"] }],
      "artifacts": ["Builds/identityserver-image.tar"]
    }
  }
}
```

```json
// Stack/ue/plugins/HolobikeWorlds.json — ships inside the package
{ "deployables": { "HolobikeWorlds": { "destination": "HolobikeExperience" } } }
```

One field does four jobs: it is the second axis of the 2×2; it is what a
profile selects on; it is where `provision` sends bytes; and it is the
**membership test** — *a stack member's code reaches a deployment
destination, as its own artifact or inside another member's.* All thirteen
current members pass. A repository that ships nowhere becomes inexpressible
rather than merely disallowed.

Deployable names belong to the repositories that own them. This plan gathers
them; it does not assign them.

### One profile per destination

```json
// Profiles/device.json
{
  "schema_version": 2, "profile": "device", "destination": "device",
  "deployables": [
    { "integration": "uroborOS",           "deployable": "..." },
    { "integration": "HolobikeCore",       "deployable": "..." },
    { "integration": "AthleteIdentity",    "deployable": "IdentityClient" },
    { "integration": "drAIs",              "deployable": "..." },
    { "integration": "HolobikeExperience", "deployable": "..." }
  ],
  "dev": { "topology": { "AthleteIdentity.IdentityClient": { "transport": "unix" } } }
}
```

There is no `device-dev.json` beside a `device-release.json`. The verb
chooses the posture; the `dev` block holds only what the development posture
*adds*. This is standing doctrine, not a new idea: the development
composition is the release composition run in a persistent, developer-facing
mode — not a parallel system.

### Four verbs

```
holobike check                 environment sanity: toolchains, engine demand, roster
holobike env <profile>         check out, build, serve, wire up, report ready
holobike build <profile>       → Artifacts/ + a release record
holobike provision <profile>   place a build on a device or on infrastructure
```

`resolve`, `bootstrap`, `assemble`, `emulate` and `admit` become **stages**,
reachable as `--only` for debugging but not the surface. `env` materializes a
missing checkout tree rather than requiring a separate verb first. `build`
ends by writing its record — a build either produces provenance or fails.
`--line <name>` selects the revision manifest; `dev` is the default.

## Phases

Each phase closes with something a person can run or a body of code that is
gone. Phases 1–3 are sequential; 4, 5 and 6 depend on 3 and not on each
other.

### Phase 1 — One specification

Subtraction only. No behaviour changes.

- Vendor the validator (D-18): ~200 lines under `Tool/src/holobike/`,
  covering the twenty keywords these schemas use, resolving `$ref` as a JSON
  pointer into the same document. It **refuses to load a schema that uses a
  keyword it does not implement** — under-enforcement must be an error, never
  a silent pass.
- Prove it against the corpus before deleting anything. The tests assert
  accept/reject over the 105 fixtures rather than error text, so the existing
  corpus is a ready-made harness: the new validator must agree with the
  hand-written one on every fixture. Keep that agreement as a permanent test
  that runs `jsonschema` alongside when it is importable and skips when it is
  not — conformance assurance without the dependency.
- Delete the six `validate_*_text` bodies. What survives per document type is
  a typed loader plus the **cross-document** checks a schema cannot express
  — "every deployable a profile names exists in some leaf". Estimate:
  1,419 lines → ~240.
- Reduce `Conformance/` to a regression set: a few accepted and rejected
  shapes per document type. Estimate: 105 fixtures → ~30.
- Collapse `Schemas/environment.example.json` into the accepted full
  fixture. Four documents cite it — `Schemas/README.md`,
  `Assembler/README.md`, D-06, and `Assembler/timers/README.md` — and a
  fifth, `Conformance/README.md`, carries the rule *"`Schemas/*.example.json`
  documents are validated as accepted fixtures in place"*, whose only
  subject is that file. All five change together or the rule outlives its
  subject.
- Extract the decision ledger from this file into `DECISIONS.md`, preserving
  the D-numbers. Landed decisions continue to live in the code they govern
  (D-07); this is the home that rule never gave the unlanded ones.

**Exit:** one place defines each document shape, the docstrings that call the
schemas canonical are true, and a field change is a one-file edit.

### Phase 2 — One vocabulary

The specification learns to describe both tiers and to refuse what does not
deploy. Cheap now, because Phase 1 made a schema change cheap.

- `kit` → `domain` across the integration schema, every leaf, and the loader.
- `entry_points` → named `deployables`, each with `destination`, its own
  build/serve/probe and its own artifacts. Profiles select deployables;
  topology keys them.
- Write the membership rule into `Stack/README.md` **before** any roster
  change, and enforce it in the schema.
- `Stack/nonmembers.json` with its schema. **HolobikeMigration is recorded
  here, not enrolled** — its single remaining module is `UncookedOnly` and
  cannot enter a cooked package, both substitute modules are retired
  (`c6a28e9` 2026-08-13, `62ad2f8` 2026-08-19), and by its own written
  condition the plugin is deletable. Its reason names that condition and
  points at the `HolobikeExperience.uproject` entry that retires it. Record
  HolobikeIntelligence and the Lab repositories likewise.
- `check` gains the stray scan: a repository adjacent to the stack and in
  neither set is a named problem, not a discovery.
- Fix the roster's one live inconsistency: **OrielUI** is selected in
  `Revisions/dev.json`, present in all twelve roster enums and carries a
  passing `orielui-dual-copy` gate, yet appears in neither roster table and
  is the only leaf without a README. The stray scan catches the opposite
  failure; nothing catches this one.
- Name the server deployables in the leaves that already own them:
  `IdentityServer`, `InsightsServer`, `AtlasServer`, `AtlasCartographer`, and
  the drAIs router when its refactor lands. Record honest absences — two of
  those have no deployment surface today, and the first act for them is to
  say so, not to invent packaging on their behalf.

**Exit:** every deployable states where it goes; a repository that ships
nowhere cannot be declared a member; and both ends of every contract that
crosses the network are named or their absence is recorded.

### Phase 3 — One tool

- `check` / `env` / `build` / `provision`. `cli.py` 430 → ~150.
- `emulate` splits: its bring-up-and-probe machinery is what `env` holds
  persistent; a slice becomes a `build` gate; the record-emission plumbing
  goes.
- `admit` collapses into `build`'s last step — digest and verify survive; the
  five-kind chain apparatus does not. One record kind, written by `build`.
- `bootstrap` folds into `env`.
- `provision/` gains `device_identity.py` unchanged — it is the only code
  here that already puts something on a device, and it becomes the verb's
  first act rather than a second executable.
- Generate per-host connection configuration from declared topology into a
  gitignored location the plugins read by convention. The plugin-side handoff
  is settled with the plugin repositories before the generator is written.

**Cell closed: development × device.** `holobike env device` on Linux yields
an error-free editor session — services up, probed, connected.

**Exit:** four verbs; the tool under ~2,700 lines including the vendored
validator; one command replaces six.

### Phase 4 — One tree

Needs a quiet moment: it moves checkouts while other agents hold working
trees.

- Convert each remaining dual copy to `AdditionalPluginDirectories` (D-08),
  pointing the descriptor at `ue/plugins` once rather than at each
  repository.
- Adopt the canonical workstation tree `<root>/<domain>/…` mirroring `Stack/`
  (D-09), with `ue/plugins/` and `ue/projects/`. A host document shrinks to a
  root, an identity, and any toolchain path that cannot be derived. `env`
  builds the tree from nothing but the Stack and a root.
- **Delete `Policy/`**, not empty it: `gates` carries `minItems: 1`, proven by
  `rejected.no_gates.json`, so an emptied `parity.json` stops validating.
  `gates.py` goes with it — `evaluate_tree_parity` is its only function and
  D-08 retires tree parity entirely.
- File moves, once the code no longer cares: `Schemas/` → `Tool/src/holobike/
  schemas/` (a tool's own contract lives beside the tool — the scope test),
  `Conformance/` → `Tool/tests/fixtures/`, `Assembler/` → `Tool/`,
  `Provisioning/` → the verb. Flatten the thirteen leaf directories to
  sibling `.json`/`.md` files; the 24–28-line leaf READMEs stay.

**Exit:** no plugin exists in two places; a host document is a root plus an
identity; five top-level directories.

### Phase 5 — Device production

First work executed on Windows, where the packaged product is actually built.

- Clone on the panel host; write its host document — subset checkouts, both
  engines, `os: windows`. `check` gains host identity and Windows paths.
- HolobikeExperience gains `Tools/Package-Win64.ps1`, the packaging recipe
  the HoloView port validated, made repository-owned; its leaf declares the
  build entry and the packaged artifact.
- `build device` runs where the bundle bytes are; the record travels by push
  through this repository. Partial resolution on a subset host records
  "unresolvable here" as fact, never refusal.
- `provision device` carries software onto a bike, alongside the identity
  document it already installs.

**Cell closed: production × device**, end to end.

**Exit:** a bike runs a build this repository produced, from a release record
admitted where the product runs.

### Phase 6 — The server side

- `env server` — `IdentityServer` is the one exercisable today: it has a
  Dockerfile, a parameterized Terraform module, and a development composition
  that refuses to bind anything but loopback by construction.
- `build server` — admit the image by digest.
- `provision server` — apply. This is the one verb that mutates a live system
  whose state outlives every release, which is exactly why it is a separate
  verb and never a side effect of a build (see D-10 below).

**Cells closed: development × server, production × server.**

**Exit:** all four cells run with one command each.

## Decisions this plan stands on

The full arguments move to `DECISIONS.md` in Phase 1; these are the standing
positions and their current status.

- **D-01 `linked` verdict** — vestigial under D-08; dies with `gates.py` in
  Phase 4.
- **D-02 Engine as a versioned fact** — *partly landed at v1.* An
  integration declaring `unreal_project` has its `EngineAssociation` held
  against the declared engine's `Engine/Build/Build.version`. This was not
  academic: the mapping pointed at 5.7.4 while `main` asked for 5.3, and
  because both engines exist here the old presence check called it healthy.
  Still owed: the version-keyed map, and `build` refusing a mismatch.
- **D-03 One v2 schema sweep** — **superseded.** Its premise was that
  batching saves version constants. There are six independent
  `SCHEMA_VERSION` constants, one per contract; batching saves nothing and
  cost a four-way dependency bottleneck.
- **D-04 Roster completeness** — survives as the membership rule and
  `nonmembers.json` (Phase 2). Its own first example was routed to the wrong
  side; see HolobikeMigration above.
- **D-05 The panel host joins the chain** — Phase 5.
- **D-06 The machine runs on a timer** — keep. systemd is the scheduler; this
  repository declares the unit templates. The Assembler gains no scheduler.
- **D-07 Doctrine is written where it applies** — keep, and complete it:
  retiring `Docs/Decisions/` gave landed decisions a home in the code and
  left unlanded ones nowhere but this file. `DECISIONS.md` is that home.
- **D-08 One tree per repository; no mounts** — keep. Decided on two measured
  properties: binaries land in the consuming project's `Binaries/`, and a
  link broke module loading because UBT computes RPATH from the output file's
  own directory, so `${ORIGIN}` resolved through the link with the wrong hop
  count.
- **D-09 The workstation tree is canonical, mirroring `Stack/`** — Phase 4.
  Plugin discovery recurses and stops at the first descriptor, so one
  `AdditionalPluginDirectories` entry finds every plugin repository — safe
  only because `ue/plugins` contains nothing else.
- **D-10 Specification spans both tiers; `build` stops at the bytes** —
  keep, **with its conclusion revised.** The insight holds: a container image
  has bytes and a Terraform apply has none; it mutates a live system whose
  state outlives every release. The old conclusion put estate delivery
  outside this tool entirely. It is now `provision`, a verb of this tool —
  because the stated goal names provisioning both ends. What the insight
  buys is that `provision` is *separate*: `build` never applies, and applying
  is never a side effect of building.
- **D-11 A leaf may name more than one deployable** — lands in Phase 2 as
  `deployables` + `destination`.
- **D-12 Updating a HoloBike is not the OS updating itself** — keep.
  uroborOS owns its own layer's mechanism and must not learn HoloBike
  composition. A device service reads the release and delegates the OS layer.
- **D-13 Build the update hub, do not become it** — keep. An OTA authority is
  a service; this is a tool that is run. The first honest feed is a signed
  static manifest per line.
- **D-14 Casing convention** — keep: PascalCase names a top-level tier, every
  level below that classifies is lowercase, and only a level naming a real
  thing carries that thing's exact name. `Provisioning/` as a tier is
  retired — provisioning is a verb — but the naming rule stands.
- **D-15 The schemas are the contract, and the tool loads them.** The
  hand-written validators were a second specification, and the fixture corpus
  was the cost of keeping two specifications in step.
- **D-16 One profile per destination; the verb chooses the posture.** A
  `dev` block holds what development adds. Two postures never fork into two
  documents.
- **D-17 A member reaches a destination.** As its own artifact, or inside
  another member's. This is the membership test the roster never had.
- **D-18 The validator is vendored, not depended on** *(ruled 2026-08-24)*.
  The tool keeps its zero-dependency install — clone and run — on both
  operating systems Phase 5 puts in play. Affordable because the surface is
  small and was measured, not guessed: Draft 2020-12, **twenty** validation
  keywords in use, all **81** `$ref`s local (`#/$defs/…`) so there is no
  registry and no remote resolution, `if`/`then` without `else`, one `allOf`
  and one `oneOf`, and none of `not`, `format`, `patternProperties`,
  `unevaluatedProperties`, `dependentSchemas`, `contains`, `anyOf`,
  `maximum`, `maxLength` or `multipleOf` present anywhere. The install story
  is worth more here than in a normal project: `pip` is not available on this
  workstation's Python (`No module named pip`, PEP 668 externally-managed),
  so a dependency is a setup step on Linux and a second one on the panel
  host — friction inside the tool whose purpose is removing friction.
  Two rules make it safe: **refuse unknown keywords at schema load**, which
  turns the silent-under-enforcement failure mode into a loud error and is
  safe because this repository owns the closed set of schemas; and **keep the
  differential test against `jsonschema`**, skipped where it is absent.
  **Revisit when the first rule fires** — a schema needing an unimplemented
  keyword. Implement the keyword, or take the dependency then, with the
  evidence in hand. Rejected alternatives: `jsonschema` as a hard dependency
  (lower maintenance over years, but pays the setup cost on two operating
  systems); and deleting the schemas to let Python be the single spec, which
  resolves the duplication in the wrong direction — it keeps all 1,419 lines,
  loses a contract other tools can read, and puts this repository's central
  artifact in imperative code against its own doctrine.

## Constraints this plan preserves

1. **The AthleteIdentity integration work is the trunk.** HoloView branches
   rebase onto it, never the reverse. Where both lines touched the same
   binary asset, `main`'s asset wins and the CoreRedirects rebind is
   re-applied.
2. **UE 5.3 now, 5.7 retained as an option.** `dev` stays on 5.3; `ue57`
   pins HolobikeExperience to its upgrade branch and resolves on the same
   cadence, so migrating is a line flip taken when its resolve runs clean.
   `origin/upgrade/ue57` is parked, not abandoned — rebase it before the
   upgrade begins, not after. Nobody should prune it as stale.
3. **Standing doctrine holds:** declarations never execute; repositories
   prove their own behaviour and this repository proves only the
   composition; structure is born by content, never scaffolded ahead of it.
   That last rule governs *directories*, not decisions — it is not a licence
   to defer knowing what a thing is.

## Deferred, with triggers

- **Signing** — when a release first leaves machines we control. That is the
  same event as the first published feed; the two decide together.
- **The update feed** — a signed static manifest per line, published where
  devices can reach it, artifacts fetched by digest. A service is earned only
  when cohort targeting, rollout telemetry, or remote kill/rollback exist
  (D-13).
- **Artifact store** — when two hosts need the same bundle bytes and ad-hoc
  copying stops being honest.
- **Content as a selection axis** — `Revisions/` selects code, and nothing
  selects the MasterAtlas corpus a device actually rides. For a geography
  product the content *is* the product. Trigger: when HexAtlas publishes a
  corpus version this repository can name. If it lands, `Revisions/` stops
  being a revision manifest and earns a broader name — not before.
- **A `Compatibility/` tier** — when a cross-repository constraint cannot be
  expressed by revision selection.
- **CI** — the timer (D-06) is the whole of it until an event a workstation
  cannot produce demands more.

## Open questions

- **`destination` for compiled-in code.** Overloading the value with
  integration names is compact; a separate `compiled_into` field is more
  explicit at the cost of one more concept.
- **Which repository owns the device-side update agent.** HolobikeCore is the
  natural owner under D-12, but the layer boundaries it must respect are the
  point, not the address. Settle it with that repository before the first
  feed, not after.
- **`Releases/` before it holds anything.** Zero records have ever been
  written. It survives this plan on the strength of Phase 5; if that slips,
  it is a directory holding a README.

## Definition of success

1. All four cells of the 2×2 run with one command each.
2. The tool is under ~2,700 lines — including the ~200 it now owns for
   validation — down from 4,601, and the fixture corpus under ~40, down
   from 105.
3. A new repository joins the stack by adding one file.
4. A schema change is a one-file edit.
5. Drift anywhere in the stack is a recorded fact within a day.
6. The 5.7 migration, when taken, is a line flip whose safety the records
   already proved.
