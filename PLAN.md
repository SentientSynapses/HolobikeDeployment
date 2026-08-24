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

**Destinations chain, and the terminal one is derived (D-19).** `device` and
`server` are reserved lowercase terminals; any other value is the exact name
of a roster member, which is PascalCase under D-14, so the two kinds never
collide. `HolobikeWorlds → HolobikeExperience → device` resolves in one walk.
Consumers ask for the *resolved* destination, never the declared one — which
is how a device release record names the five plugin revisions compiled into
the package without anyone maintaining a second list.

One field does five jobs: it is the second axis of the 2×2; it is what a
profile selects on; it is where `provision` sends bytes; it is how provenance
finds everything that contributed to a build; and it is the **membership
test** — *a stack member's code reaches a deployment destination, as its own
artifact or inside another member's.* All thirteen current members pass. A
repository that ships nowhere becomes inexpressible rather than merely
disallowed.

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

### Phase 1 — One specification — COMPLETE 2026-08-24

Subtraction only; no behaviour changes. `ca8222b` → `c70db2c`.

The validator is vendored at 303 lines (`schema.py`), draft 2020-12, local
`$ref` only, and refuses a schema using a keyword it does not implement. All
six schemas compile, so the subset is not aspirational.

It was proven before anything was deleted: 104 of 104 parseable fixtures
agree with `jsonschema`, no accepted fixture is refused, and all seventeen
live declarations validate. That agreement is now a permanent test, running
`jsonschema` where it is installed and skipping where it is not — D-18's
whole shape.

The six bindings fell **1,419 → 451**, past the ~240 estimate only because a
typed view of five record kinds is real work. The Assembler is **4,173 →
3,536** including the validator. What a schema cannot say turned out to be
five rules, and naming them was the point:

- a profile's `topology` may only key integrations it carries;
- policy gate names are unique (`uniqueItems` compares whole gates);
- artifact **file names** must be unique, since `assemble` stages them flat;
- an assembly's `builds` and an emulation's `members` must key exactly the
  integrations the same record claims;
- a `linked` gate verdict must name its target.

`revisions` and `environment` kept **nothing** — the eighteen-line git
ref-name check was a lookahead pattern in the schema all along.

Two things went further than planned, and one went the other way:

- **The roster and the kit set are now read out of the schema** rather than
  declared in Python and held in agreement by a test. Structural agreement
  beats tested agreement. A new test walks all six schemas for roster sites —
  there are twelve — and fails if they disagree, so a member enrolled in
  eleven of them can no longer be live in some mechanisms and invisible to
  others.
- **Three of the five surviving rules had no fixture.** They were being
  enforced on trust, against this repository's own "no binding without a
  fixture". Each has one now.
- **`Conformance/` was not reduced to ~30; it grew to 108.** The planned
  pruning assumed the corpus existed only to keep two specifications in step.
  It now does something better: it is the evidence that the vendored
  validator matches a reference implementation, which is the mechanism making
  D-18 safe. Cutting it would weaken the reason vendoring was affordable.
  **This is a deliberate departure from the plan as written.**

`Schemas/environment.example.json` is deleted, collapsed into
`Conformance/environment/accepted.full.json`, with all five citations moved —
including `Conformance/README.md`'s rule about `*.example.json`, whose only
subject was the deleted file. The decision ledger moved to `DECISIONS.md`,
D-numbers preserved.

**Exit met:** one place defines each document shape, the docstrings calling
the schemas canonical are true, and a field change is a one-file edit. 92
tests green; `preflight` clean against all thirteen live checkouts.

### Phase 2 — One vocabulary

The specification learns to describe both tiers and to refuse what does not
deploy. Cheap now, because Phase 1 made a schema change cheap.

- `kit` → `domain` across the integration schema, every leaf, and the loader.
- `entry_points` → named `deployables`, each with `destination`, its own
  build/serve/probe and its own artifacts. Profiles select deployables;
  topology keys them.
- The destination resolver (D-19): the loader proves every chain reaches a
  reserved terminal without cycles, and consumers take the resolved value.
  The five UE plugins get their first honest declaration — they name the
  package they compile into, which is why they have no artifacts of their
  own.
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

The ledger lives in [`DECISIONS.md`](DECISIONS.md) — twenty entries, their
status, and what would overturn each. The ones this plan leans on hardest:
**D-10** (the specification spans both tiers; `build` stops at the bytes and
`provision` is the separate verb that does not), **D-15** (the schemas are the
contract), **D-17** (a member reaches a destination — the membership test),
and **D-19** (destinations chain; the terminal is derived).

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

- **Which repository owns the device-side update agent.** HolobikeCore is the
  natural owner under D-12, but the layer boundaries it must respect are the
  point, not the address. Settle it with that repository before the first
  feed, not after.

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
