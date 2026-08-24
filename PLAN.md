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

### Phase 2 — One vocabulary — COMPLETE 2026-08-24

`19a7d65` → `1ec8742`. The membership rule went in **first**, before any
roster change, which is the whole lesson of what the previous plan got wrong.

Integration schema v2: `kit` → `domain`, `entry_points` → named
`deployables`, `prove` at the leaf because it proves the repository rather
than any one deployable. **Eighteen deployables across thirteen leaves**, and
every name is a top-level directory in the repository that owns it rather
than a coinage here; a repository producing exactly one names it after
itself. `DraisAgent` is deliberately absent — it has no README, and this
repository does not name what it cannot describe.

**Fifteen of the eighteen are recorded absences** — named, with nothing here
able to build them. That was the point: `AtlasServer` and `InsightsServer`
are now visible as unbuilt rather than invisible as unmentioned.

Destinations chain and resolve (D-19). The five UE plugins name
HolobikeExperience, which is the first honest statement of why they have no
artifacts of their own. `resolve_destination` refuses cycles, missing leaves,
and a carrier with more than one landing deployable; `carried_by` answers what
a release record needs — **thirteen deployables reach `device`, five of them
through HolobikeExperience, and five reach `server`** — with no second list.

The roster is closed into a loop. `Stack/nonmembers.json` records seventeen
adjacent repositories with reasons; thirteen members plus seventeen
non-members accounts for all thirty git checkouts under the kits, and
`preflight` says so. **HolobikeMigration is recorded, not enrolled**, its
entry naming the fact that decides it — one `UncookedOnly` module, which
cannot enter a cooked package. **HolobikeIntelligence is recorded as a
candidate**: it would pass the rule and is simply not enrolled while the drAIs
integration is in flight, so preflight names it every run rather than letting
it sit. Two entries say plainly that the question is unsettled rather than
dressing a guess as a decision.

The scan found something on its first run — HolobikeDeployment itself, in
neither set. It is declared rather than skipped by teaching the scan where it
is running from.

OrielUI has the README it never had and its row in both roster tables, with
two tests holding that shut.

**Exit met:** every deployable states where it goes; a repository that ships
nowhere is inexpressible as a member; and both ends of every contract that
crosses the network are named or their absence is recorded. 97 tests green,
124 fixtures, `preflight` exit 0.

**Moved to Phase 3:** *profiles select deployables, topology keys them.*
Selecting a deployable only means something once the verbs consume
deployables, and they still select whole integrations. Landing it here would
have created exactly the transitional double-shape Phase 1 spent itself
removing. The leaf side carries a transitional `producer` that refuses a leaf
where it would be ambiguous, and says in its own docstring that Phase 3
deletes it.

### Phase 3 — One tool — COMPLETE 2026-08-24

`c7eae7e` → `39791a8`. Four verbs; `cli.py` 430 → 260; the launcher is
`holobike`.

```
holobike check                     can this workstation do the work?
holobike env device                up, probed, and held
holobike build device              stage a bundle, gate it
holobike build device --version V  ...and admit it
holobike provision device          place something on a thing
```

`resolve`, `bootstrap`, `assemble`, `emulate` and `admit` are stages behind
`--only`. `build` without `--version` reports what it *would* admit, because a
version is a decision. `env` is the same composition stopping where a
developer wants to be, with `bootstrap` folded in — someone missing a checkout
wants it materialized, not diagnosed. The hold is emulate's own machinery:
`env` waits after the settle pass and teardown is still the same `finally`, so
an interrupt tears down exactly as a completed run does.

`provision` stayed separate rather than becoming `build`'s last step, which is
D-10 made real: `build` stops at the bytes, and applying is never a side
effect of building. `device_identity.py` moved in unchanged as its first act,
and `provision server` refuses with the reason rather than pretending.

Profiles v2 and record v2 landed first (`c7eae7e`), the second forced by the
first: `Profiles/server.json` needs both `AtlasServer` and
`AtlasCartographer`, and a record keyed by integration could not describe that
run. `resolved` and `actions` stay keyed by integration — a checkout is per
repository — while `builds`, `artifacts` and `members` key by deployable.
**That retired four roster enums: the roster is spelled out in eight places,
down from twelve.** Both transitional constraints from Phase 2 are gone.

**Exit met**, with one correction below: four verbs, every stage reachable in
isolation, one command replacing six, and the daily drift record still
standing alone. 109 tests green.

#### The record collapse was refused, and the line target was wrong

This phase was written to say *"admit collapses into build's last step... One
record kind, written by `build`,"* and to exit under ~2,700 lines. The tool is
**4,456**. Both were my estimate, made before implementation; the evidence
found while implementing argues against the collapse, so the estimate that
depended on it is what changes.

`Artifacts/records/` holds **53 resolution records, 4 assembly, 3 emulation,
1 admit, 0 bootstrap** — and `Releases/` is still empty. The resolution record
is not an internal artifact of `build`. It is the *product* of the daily
cadence, written 53 times by a timer that resolves and does nothing else, and
it is how Definition of Success #5 is met at all. A single build record
written by that timer would be four-fifths empty, which is a dishonest
document, or resolution would stop being recordable on its own, which ends
drift detection.

Two more reasons the chain stays. `--only` keeps every stage independently
runnable — that is this phase's own doing — so a person can still assemble
against a stale resolution, and the digest binding between records is exactly
what catches it. And the `release` kind has **zero** instances: redesigning
the one record nobody has ever written, before Phase 5 writes one for real,
is designing from ignorance, which this repository forbids.

So the exit gate is what the phase should have measured in the first place —
four verbs, stages reachable in isolation, the drift record standing alone —
and not a line count that assumed a change the work disproved.

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
2. No shape is defined twice. That was the real cost the 23:1 ratio was
   measuring, and it is what Phase 1 removed — the six bindings fell
   1,419 → 451 by deleting a second specification, not by writing less
   code. The tool is 4,456 lines and does more than it did: it validates,
   composes four verbs, and provisions. A line target here was a proxy for
   duplication, and a bad one; the check that matters is that adding a
   field costs one edit.
3. A new repository joins the stack by adding one file.
4. A schema change is a one-file edit.
5. Drift anywhere in the stack is a recorded fact within a day.
6. The 5.7 migration, when taken, is a line flip whose safety the records
   already proved.
