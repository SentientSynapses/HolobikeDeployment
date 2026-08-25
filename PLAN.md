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
├── Profiles/            WHICH parts, and how they wire — one per thing deployed together
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

### Phase 4 — One tree — COMPLETE 2026-08-24

`bdad274` → here, plus `20304b5` in HolobikeExperience — two repositories,
two commits, which is D-22 in practice.

**The tool tier.** `Assembler/` → `Tool/`, the package `holobike_assemble` →
`holobike`, launcher `Tool/holobike`. `Schemas/` → `Tool/src/holobike/schemas/`
and `Conformance/` → `Tool/tests/fixtures/`, because a tool's own contract
lives beside the tool. The schema loader resolves its directory as a sibling
rather than by climbing to the repository root, so the tool no longer needs to
know where it is installed. `Provisioning/` is gone as a tier; its README moved
beside the verb that replaced it.

**Flat leaves.** Thirteen directories holding one or two files each became
`Stack/<domain>/<Integration>.json` and `.md`. The file name is the identity,
and `load_stack` refuses a leaf whose document names something else.

**The dual copies, in HolobikeExperience's own commit.** Four plugins reached
through `AdditionalPluginDirectories` instead of being carried twice: 602
files and 230,920 lines removed, including committed `Binaries/Win64` DLLs
that had no business in a project tree. Verified before deletion rather than
after — all four gates passed at the moment of the change, and each mounted
copy was diffed against its upstream; the only differences were empty
`Content/` directories the gates exclude by design. RidePaths work was in
flight, the same `WaypathsResolve.h` edit hand-synchronised into both copies,
and it survives untouched in the repository that owns it. Not verified here: a
full editor build. The pattern is HoloviewDisplay's, which M10 proved by build
and launch, and every `.uplugin` resolves at its declared path — but the first
editor launch is the real test.

**`Policy/` retired, and with it more than expected.** `parity.json` and
`gates.py` were the plan's whole expectation. What actually went: the policy
contract, its schema, its fixture corpus, its conformance suite, gate
evaluation in `resolve`, the `gates` field in every record, and the release
attestation's `gates` line — because a tier with no content does not get to
keep a binding, a schema and a record field. Records are at **v3**.

That forced one rule to change. `admit` refused any resolution with no gates
evaluated, which after D-08 would have made every future release
unadmittable. A release now attests what it actually has, and the absence of
gates is visible in the record rather than fatal — the same shape emulation
already had with `healthy` / `absent`.

**The roster is spelled out in seven places, down from twelve** at the start
of Phase 2.

**Found by doing it:** flattening the leaves broke thirteen markdown links,
silently. A test now walks every link in the repository, so a tree that moves
cannot leave its own prose behind.

100 tests green; `check` exit 0; `build --only resolve` resolves 13/13.

**Deferred to Phase 5, on a real dependency:** the canonical workstation tree
(D-09) and `checkouts` → `root`. These are this repository's own work, but
deriving `<root>/<domain>/<repository>` requires the checkouts to be in the
tree it describes, and today they are at `ue_kit/HolobikeExperience_uproject`. The move
is an announced operation — absolute paths live in scripts, IDE configuration
and every host document — and it belongs with the phase that first writes a
host document on a second machine.

### Phase 5 — Device production — STARTED 2026-08-24

The prerequisite is in; the rest needs machines this workstation is not.

**Done — host identity.** A host document now says which machine it describes:
`host` and `os` are required, `$defs.absolutePath` admits Windows paths
(`C:\...` and `C:/...`) beside POSIX ones, and every record's `run` block names
its producer. Environment documents are at **v2**, records at **v4**. `check`
prints the host first, because on a second machine that is the first thing a
person needs to know.

That last piece has a shape worth keeping: the identity stamp is one shared
`environment.producer()`, so no verb invents its own idea of who ran
something. `emulate` and `admit` gained the host document they did not
previously read — `admit` especially, since admission runs where the artifact
bytes are, and a release record that cannot say where that was describes half
of what happened.

A live resolution now records `"host": "mjolnir", "os": "linux"`.

**Needs the panel host** — a Windows machine this session cannot reach: the
clone, its host document (subset checkouts, both engines, `os: windows`), and
`build device` running where the bundle bytes are. The contracts are ready for
all three; nothing else here can be honestly written until a real Windows
`check` has run.

**Owed by HolobikeExperience (D-22):** `Tools/Package-Win64.ps1`, the packaging
recipe the HoloView port validated, made repository-owned. That is its commit,
and it cannot be validated from Linux — a PowerShell packaging script written
here and never run would be scaffolding with a plausible shape.

**Needs a bike:** `provision device` carrying software rather than only the
identity document.

**Still to decide, and now the blocker for the canonical tree:** moving the
workstation checkouts to `<root>/<domain>/<repository>` (D-09) is an announced
operation — it breaks absolute paths in scripts, IDE configuration, other
agents' sessions, and the `AdditionalPluginDirectories` relative paths that
20304b5 just wrote. It is this repository's own work and it is ready to write,
but it reorganises the whole workspace and wants a deliberate moment rather
than being folded into a phase.

### Phase 6 — The server side — STARTED 2026-08-24

Most of what this phase was written to do landed in Phase 2: the server
deployables are named in the leaves that own them, `Profiles/server.json`
selects the five that reach the estate, and four of them are recorded
absences. What remained was to decide what this repository does with the one
that can be exercised — and reading it changed the answer.

**`IdentityServer` declares the build its own repository documents**, producing
`athleteidentity-server:base` and saving it to a tar so the bundle carries
bytes and `admit` has something to hash.

**And a base image does not deploy.** AthleteIdentity says so itself: the image
"intentionally contains no device authenticator", and its Terraform module
refuses to create Cloud Run until `container_image` names a derived image that
has one. The repository lists seven further readiness items as *project-owned*
rather than its own — the derived image, a reviewed device credential format
with manufacturing enrolment and rotation, provisioned registry entries, the
athlete-facing pairing approval experience, operator revocation and key-rotation
procedures, and observability. **None of them exists.**

So the honest Phase 6 result is not `build server` producing a deployable. It
is: this repository can build the base image and record its digest, it cannot
deploy it, and `provision server` refuses by *naming which decision is
missing* rather than failing vaguely. `Stack/id/AthleteIdentity.md` records
the gap where a person looking at the leaf will find it. Deriving the
production image is not AthleteIdentity's to do and is not packaging this
repository may invent on its behalf — it is a decision the project owes, and
the release record keeps saying the estate half is unbuilt until it is made.

**Found by running it.** This workstation has no docker, and `build server`
crashed with an unhandled `FileNotFoundError` instead of recording anything. A
build tool a host does not have is now a recorded fact — status `unavailable`
with the reason — so a Linux workstation that cannot build a container image
says so in the record rather than in a traceback. `check` reports docker among
its PATH tools for the same reason. That bug was invisible until a deployable
needed a tool this machine lacks, which is exactly what the server tier is.

`build server` on this host now produces a truthful record: one `unavailable`,
four `skipped`, no artifacts, exit 1.

**Still needed, and none of it is code:** the seven readiness items above, and
the project decision about who derives the production image. Until then the
server column of the 2×2 is specified, buildable in part, and honestly
undeployable.

## What remains, and who owns it

Collected because the defining feature of the remaining work is that most of
it is not this repository's to do (D-22). Nothing here is blocked on the
tooling.

### This repository's own

- **The canonical workstation tree (D-09)** and `checkouts` → `root`. Ready to
  write; deliberately not done. Moving checkouts to
  `<root>/<domain>/<repository>` breaks absolute paths in scripts, IDE
  configuration, other agents' live sessions, and the
  `AdditionalPluginDirectories` relative paths written in HolobikeExperience
  `20304b5`. It reorganises the whole workspace and wants a chosen moment
  rather than being folded into a phase.

### Owed by other repositories

- **HolobikeExperience — `Tools/Package-Win64.ps1`**, the packaging recipe the
  HoloView port validated, made repository-owned. Its commit, and it cannot be
  validated from Linux. Until it exists, `HolobikeExperience`'s leaf declares
  no build steps, which is why `build device` stages nothing for the product
  itself.
- **HolobikeExperience — two Blueprint assets fail to compile on 5.7** where
  they are clean on 5.3: `BP_CompanionAvatar` and `BP_MainRider` both report
  *"Switch on (bad enum) must have a valid enum"*, an enum import failing
  across the version boundary. Found by launching the rebuilt branch on
  5.7.4; the only known blocker in the upgrade itself.
- **HolobikeDevice_uplugin — `FHolobikeDeviceMsgSpec::SpecId` is an
  uninitialized struct member.** Reported by `LogClass` on both engines and
  echoed as an automation failure; 5.7 additionally suggests
  `UPROPERTY(Meta = (IgnoreForMemberInitializationTest))`. Found by launch,
  pre-existing, unrelated to any change here.
- **AthleteIdentity — the seven project-owned readiness items** its
  `IdentityServer/Deployment/README.md` lists, none of which exists. The
  derived image carrying a device authenticator is the one that blocks
  `provision server`; three of the seven are the same subject seen three ways
  — device credential format, registry enrolment, and revocation — which is
  also what D-13 said the update feed must not duplicate. Decide credentials
  and both unblock together.

### Needs a machine this session cannot reach

- **The Windows panel host** — the clone, its host document, and `build
  device` running where the bundle bytes are. Every contract is ready;
  nothing further can be honestly written until a real Windows `check` has
  run.
- **A bike** — `provision device` carrying software rather than only the
  identity document.

### Decisions owed

- **HolobikeIntelligence.** Recorded as a *candidate* non-member: it would
  pass the membership rule exactly as the other five UE plugins do, and is
  simply not enrolled while the drAIs integration is in flight. `check` names
  it every run rather than letting it sit.
- **Whether `HolobikeMigration_uplugin` is deleted outright.** Its retirement
  condition is met and HolobikeExperience no longer enables it; the
  repository's own fate is that repository's call.

### Proposed and declined — recorded so they are not re-proposed blindly

- **`Revisions/ue57.json`, a second revision line.** Declined 2026-08-24. A
  daily `resolve` records existence, cleanliness and a SHA — it would have
  reported the parked `upgrade/ue57` as green every day for the two weeks it
  rotted. It becomes worth having once HolobikeExperience declares a build
  entry, because then a green record means the project still compiles on 5.7.
  Until then it is a file whose daily record proves almost nothing.
- **A distance/staleness fact on each selection.** Declined 2026-08-24.
  Recency is not what matters — a release line may pin deliberately old,
  stable commits and be doing exactly its job. The tooling is not to be
  overbuilt.

## Decisions this plan stands on

The ledger lives in [`DECISIONS.md`](DECISIONS.md) — twenty-three entries, their
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
   `origin/upgrade/ue57` is parked, not abandoned. **Rebuild it rather than
   rebasing it** (assessed 2026-08-24): of its 237 files, ~208 are vendored
   SDK upgrades that replay cleanly, ~10 are project-side, and the rest edit
   in-house plugin mounts `main` has since deleted — conflicts a rebase
   cannot resolve, because their destination is a different repository.
   **Done 2026-08-24.** The harvest completed — every in-house change was
   already upstream, verified line by line — and the branch was rebuilt as
   `upgrade/ue57-rebuilt` (HolobikeExperience `c38d69c`), carrying the nine
   vendored SDK trees and the project-side changes onto current `main`. Two
   local machine artifacts were dropped rather than carried: `LumaAIPlugin`
   and `VisualStudioTools` were disabled because they are not installed on
   the workstation that made that commit, and `main` both builds and launches
   with them enabled. **It builds against UE 5.7.4, `Result: Succeeded`, zero
   compile errors**, and the editor starts with no dlopen, plugin-load,
   CoreRedirects or assertion failures. The original `upgrade/ue57` is kept
   as the reference ref; nobody should prune it.
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
  product the content *is* the product. `AtlasCartographer` produces that
  corpus and is not a deployable (D-23); this axis is where its product gets
  named. Trigger: when HexAtlas publishes a corpus version this repository
  can name. If it lands, `Revisions/` stops being a revision manifest and
  earns a broader name — not before.
- **Splitting `Profiles/server.json`** — into profiles that group what is
  deployed together (D-23): `identity`, `atlas`, and `drais`. The single
  document is not a claim that those share a host. Trigger: a second server
  deployable with bytes; today only `IdentityServer` has any. `provision`
  then takes a profile instead of a terminal.
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
