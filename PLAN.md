# HolobikeDeployment Plan

Direction and pending decisions for the deployment tool. The README owns
identity and current state; `Docs/Decisions/` owns settled rationale; this
file owns where the tool is going and why. When a milestone lands, its entry
here shrinks to a line and its rationale moves to an ADR — a plan that
restates what the repository already proves is a second copy waiting to
drift.

## Objective

HolobikeDeployment is the consolidated development and deployment
environment for the HoloBike software stack: one set of declarations that
manages the stack across its repositories, in both of the tool's postures.

- **Development.** A developer on any enrolled workstation — Windows or
  Linux — can launch HolobikeExperience in the Unreal editor without
  errors: plugin mounts correct, redirects clean, the demanded engine
  version present, and the companion background services running and probed
  before the editor asks for them. Plugins connect to their services with
  minimal configuration, because connection facts are generated from
  declared topology rather than hand-maintained on each machine.
- **Deployment.** The record chain (`preflight` → `bootstrap` → `resolve` →
  `assemble` → `emulate` → `admit`) turns the same declarations into
  admitted, self-contained releases whose source revisions, artifact
  digests, and gate verdicts are recorded facts.

The two postures deliberately share everything: the same Stack leaves, the
same schemas, the same environment documents, the same gates. The
development composition is the release composition run in a persistent,
developer-facing mode — not a parallel system.

## Standing (2026-08-16)

The core build-out (M1–M8) is complete: all six verbs live, 76 Assembler +
13 Provisioning tests green, five run-record kinds digest-bound, admission
the only writer of tracked `Releases/`. Live gate truth: rider, device, and
orielui dual-copy gates pass; worlds fails on 25 mismatches proven to be a
stale mount (every difference is the standalone repository having moved
ahead), closable by one-way sync with nothing to lose. Enrollment of
HoloviewDisplay as the twelfth integration exists on branch
`integrate/holoviewdisplay`, paired with a HolobikeExperience branch of the
same name; both are unlanded.

## Constraints this plan preserves

1. **The AthleteIdentity integration work is the trunk.** The identity and
   insights workstream on HolobikeExperience `main` is not merged *into*
   the HoloView branches; the HoloView branches rebase *onto* it. Where
   both lines touched the same binary asset, `main`'s asset wins and the
   CoreRedirects rebind is re-applied — redirects are configuration and
   compose over content; binary merges are a pick-one and must always pick
   the trunk. Verification is the nullrhi load check already used for the
   mock retirement.
2. **UE 5.3 now, UE 5.7 retained as an option.** The engine posture is
   expressed as revision lines, not long-lived branches: `dev` stays on
   5.3; a `ue57` line pins HolobikeExperience to its upgrade branch and is
   resolved on the same cadence as `dev`, so the migration option's health
   is a recorded fact rather than a hope. Migrating is a line flip taken
   when its resolve runs clean — an event the records predict, not one
   they discover.
3. **Standing doctrine holds**: declarations never execute; gates annotate
   and only admission refuses; structure is born by content, never
   scaffolded ahead of it; repositories prove their own behavior and this
   repository proves only the composition.

## Environments: platform postures, host documents

There are two development *postures* — Windows (editor plus panel plus
Simulated Reality Platform) and Linux (editor with the Null display
platform, services over local sockets, uroborOS packaging). There are more
than two *machines*, already: this Linux workstation and the Windows panel
host, with any future workstation joining by writing one file.

The shape that keeps those apart:

- **Tracked, per-posture**: what the stack composes on each OS — profile
  membership, service topology, transport selection, demanded toolchains.
  This is product truth and lives where composition already lives
  (`Profiles/`, Stack leaves, schemas).
- **Gitignored, per-host**: where things are on one machine — checkout
  paths, engine install paths, host identity (`host`, `os`). This is
  workstation truth and stays in `.local/environment.json`, whose schema
  already permits partial checkouts (`accepted.single_checkout` is a
  fixture): a host declares the subset of the stack it carries.

A per-OS *file* would conflate the two: it would start as platform truth
and accrete machine paths until it was really a per-host file with merge
pain. The schema/`.local` split made this separation correctly once; the
multi-host step extends it rather than replacing it.

Records name their producer (`run.host`, `run.os`), and the tracked
repository is the transport between hosts: the Windows host clones this
repository, runs the same verbs, and pushes the release records it is
uniquely able to produce — admission runs where the artifact bytes are,
because it re-hashes them. No artifact store, no record transport
machinery.

Service reachability is where the postures genuinely differ, and the stack
has already paid for the answer: transport is not topology (HolobikeCore
ADR 0011). On Linux the plugins reach their services over unix sockets; on
Windows they reach the same services over the websocket wire. Either way
the plugin consumes an endpoint, which is exactly what a generated
development configuration can supply.

## The development composition

Proposed verb: `develop` (name open). It composes existing seams rather
than adding machinery:

1. `preflight` — including the engine-demand check — so a broken
   environment is named before anything launches;
2. ensure canonical plugin mounts (links, never copies);
3. bring up the declared development profile's services from their
   repository-owned `serve` entries and hold them, reusing the `emulate`
   machinery in a persistent mode;
4. `probe` until healthy;
5. generate the per-host connection configuration (endpoints per declared
   topology) into a gitignored location the plugins read by convention;
6. report ready — or launch the editor where that is scriptable.

"Minimal configuration" means: convention over configuration, generated
never hand-written, host-specific therefore gitignored. The handoff
mechanism on the plugin side (file, environment variable, or existing
config layer) is an open decision owned jointly with the plugin
repositories.

This verb is described here but built only when its first posture lands
(M14) — earned by content, like every tier before it.

## Decisions established 2026-08-15/16

- **D-01 `linked` verdict.** `tree_parity` gains a third honest outcome:
  when both sites resolve to the same real path, the gate reports
  `linked` (parity by construction) instead of a vacuous `pass`. The
  mount path is gitignored in HolobikeExperience so a link can never
  silently become a tracked copy. Links become the migration target for
  the existing dual copies: convert a mount, and its drift class stops
  existing instead of being reconciled forever.
- **D-02 Engine as versioned fact.** The `unreal_engine` toolchain slot
  becomes a map keyed by version (`"5.3"`, `"5.7"`). Preflight reads
  `Engine/Build/Build.version` and reports a declared-vs-installed
  mismatch; the engine *demand* is read from the project checkout's
  `EngineAssociation` (the source repository stays authoritative for its
  own requirement). Resolve records demanded/satisfied; admission refuses
  anything else.
- **D-03 One v2 schema sweep.** All pending breaking changes land as a
  single coordinated `schema_version` bump with its conformance corpus:
  `kit` → `domain`, the engine map, host identity (`host`, `os`) in
  environment documents, `run.host`/`run.os` in records, and an
  `absolutePath` definition that admits Windows paths. Closed schemas
  spend their version constant once, not three times.
- **D-04 Roster completeness as a closed loop.** A tracked
  `Stack/nonmembers.json` lists adjacent repositories that are
  deliberately not stack members, each with a reason; preflight scans the
  declared checkouts' parent directories and reports any repository in
  neither set as `unenrolled_repository`. First candidates the sweep
  forces: HolobikeMigration (mounted, dual-copy, already drifted) and
  AthleteInsights (deployed device software consumed as
  AthleteInsightsIO).
- **D-05 The panel host joins the chain.** The Windows machine gets a
  clone and runs the same verbs; the UE bundle is assembled from a
  repository-owned packaging entry point declared on the
  HolobikeExperience leaf, in a profile of its own. Emulation for UE
  waits until there is something honest to probe; assembly evidence is
  enough to admit against, per the chain's existing optional-emulation
  shape.
- **D-06 The machine runs on a timer.** A scheduled `resolve` per
  committed line, owned by `helgafell_operator` (workstation operations),
  not by this repository — the Assembler gains no scheduler.
- **D-07 The doctrine gets ADRs.** 0004 gates annotate / admission
  refuses (skips are problems; `linked` is parity by construction). 0005
  roster membership and why nonmembers carry reasons. 0006 the record
  chain: digest binding, immutability, `Releases/` as the only tracked
  writer. 0007 hosts: per-host environments, producer-named records, the
  tracked repository as transport.

## Implementation phases

Phases continue the milestone numbering from the completed build-out
(M1–M8). Each phase is a commit family carrying its own verification;
dependencies between phases are named, and nothing else blocks.

### M9 — gate truth

This workstation; no schema breaks; no cross-repo dependency.

- `Assembler/src/holobike_assemble/gates.py`: after both site roots
  resolve, compare their `Path.resolve()` results; equal means
  `status: "linked"` with the shared target recorded as a fact. Distinct
  real paths compare exactly as today — a link to *somewhere else* is
  not parity.
- `Schemas/record.schema.json`: the gate `status` enum gains `linked`.
- `resolve`'s problem collector and `admit`: `linked` is a passing
  verdict, never a problem.
- `Assembler/tests/test_policy_gates.py`: symlink-to-left yields
  `linked`; symlink-elsewhere is compared; one accepted record fixture
  carries a `linked` gate.
- Close the worlds mount: one-way sync, repository onto mount, over
  exactly the gate's compared surface (the same exclude list), then a
  `resolve` to confirm. Every mismatch is proven stale-mount, so
  nothing is lost.
- ADR 0004 lands here (gates annotate, admission refuses; skips are
  problems; `linked` is parity by construction).
- Start the D-06 timer on the dev line — the cadence is already
  meaningful.

**Exit gate:** every gate verdict on the dev line is honest and green,
and the suite proves a link cannot report a vacuous `pass`.

### M10 — land the HoloView integration

Cross-repo sequencing. Depends on M9: the `linked` verdict must exist
before the fifth gate can meet a linked mount.

- HolobikeExperience: rebase `integrate/holoviewdisplay` onto `main`
  (the identity trunk), under constraint 1's binary rule; inspect
  `BP_MainRiderHUD` by hand — the one asset plausibly touched by both
  workstreams. Verify with the nullrhi load check; land.
- Convert the HoloviewDisplay mount to the canonical link and gitignore
  the mount path in the same change.
- Re-stack `upgrade/ue57` on the landed result.
- HolobikeDeployment: land the enrollment commit (`92d32b1`) — twelfth
  integration, fifth gate — at the schema v1 spelling; the
  `kit` → `domain` rename is held for M11's single bump.
- Fast-forward this workstation's `HoloviewDisplay_uplugin` checkout
  (still at the scaffold commit) and add its path to
  `.local/environment.json` on every host that carries it.

**Exit gate:** `resolve --line dev` reports the holoviewdisplay gate
`linked` with twelve of twelve selections resolved, and Experience
`main` carries both workstreams under the nullrhi check.

### M11 — the v2 sweep

One commit family; each schema spends its version constant once. The
corpus sweep is programmatic with a re-scan — roster sites hide in
wrapped enum lines.

- `kit` → `domain` across the integration schema, every Stack leaf, and
  the bindings (adapting the held rename commit).
- `unreal_engine` becomes a version-keyed map in
  `Schemas/environment.schema.json` and `.local/environment.json`.
- `preflight.py`: `_inspect_toolchain` parses
  `Engine/Build/Build.version` and reports declared-versus-installed
  mismatch; a new engine-demand check reads `EngineAssociation` from
  the `Stack/ue/project/` checkouts — the source repository stays
  authoritative for its own requirement.
- Environment documents gain `host` and `os`; records gain `run.host`
  and `run.os`; `$defs.absolutePath` admits Windows paths.
- `resolve` records the engine join (demanded / path / build_version /
  status); `admit` refuses anything unsatisfied.
- Fixtures: accepted two-engines; rejected unversioned-engine; rejected
  `kit` spelling; wrong-version rejections refreshed throughout.

**Exit gate:** preflight cannot call the wrong engine "present"; no
schema accepts both spellings of anything; the suite is green at the
new constants.

### M12 — lines and roster

Depends on M10 (the re-stacked upgrade branch) and M11 (v2 documents).

- `Revisions/ue57.json` pins HolobikeExperience to the re-stacked
  upgrade branch; the committed-lines test covers it the moment the
  file exists. Add the line to the timer's cadence.
- `Stack/nonmembers.json` with `Schemas/nonmembers.schema.json` and its
  corpus; the preflight stray scan walks the declared checkouts' parent
  directories and names any repository in neither set.
- Enroll HolobikeMigration (mounted, dual-copy, already drifted — gains
  the sixth gate) and AthleteInsights (deployed device software,
  consumed as AthleteInsightsIO); record HolobikeIntelligence and the
  Lab repositories as nonmembers with reasons.
- ADR 0005 lands here (roster membership; why nonmembers carry
  reasons).

**Exit gate:** fourteen integrations resolve on two lines on cadence,
and an unenrolled repository adjacent to the stack is a named preflight
problem, not a discovery.

### M13 — the panel host

First phase with work executed on Windows. Depends on M11 (host
identity, Windows paths).

- Clone HolobikeDeployment on the panel host; write its host document —
  subset checkouts, both engines, `os: windows`.
- HolobikeExperience gains `Tools/Package-Win64.ps1`, the packaging
  recipe the HoloView Phase 6 validated, made repository-owned; its
  Stack leaf declares the `build` entry and the packaged artifact.
- `Profiles/experience.json`; assemble → admit run where the bundle
  bytes are; the release record travels by push through the tracked
  repository.
- Shape partial-resolution semantics from the first real subset-host
  `resolve`: "unresolvable here" as recorded fact, never refusal — the
  M3 tradition.
- ADRs 0006 (the record chain) and 0007 (hosts) land here.

**Exit gate:** a release record admitted from evidence produced on the
machine where the product actually runs.

### M14 — the development composition

The Linux posture depends only on M9; the Windows posture on M13.

- The development verb (name open), composing existing seams: preflight
  with the engine-demand check → canonical mounts ensured → services up
  from repository-owned `serve` entries, the emulate machinery held in
  a persistent mode → probe to healthy → generate the per-host endpoint
  configuration (gitignored, convention-read) → report ready, or launch
  the editor where that is scriptable.
- Linux posture first, over unix sockets; Windows follows over the
  ADR-0011 websocket wire.
- The plugin-side handoff decision is resolved with the plugin
  repositories before the generator is written, not after.

**Exit gate:** on an enrolled workstation of either OS, one command
yields a ready, error-free editor session — services up, probed, and
auto-connected.

## Deferred, with triggers

- **Signing** — when a release first leaves machines we control.
- **Artifact store** — when two hosts need the same bundle bytes and
  ad-hoc copying stops being honest.
- **Fleet / Compatibility tiers** — when there is a second bike.
- **CI as an institution** — the timer (D-06) is the whole of it until an
  event a workstation cannot produce demands more.

Each of these built early would be structure held up by a refusal;
described here, they are born when their content arrives.

## Open decisions

- The development verb's name, and the exact plugin-side handoff for
  generated connection configuration (owned jointly with the plugin
  repositories).
- Whether per-posture composition lives as separate profiles
  (`develop-linux`, `develop-windows`) or one profile with per-OS
  topology — decide when the first `develop` posture is built, from what
  the topology actually needs to express.
- Partial resolution semantics for subset hosts: a host that carries
  three checkouts resolving a twelve-member line should record
  "unresolvable here" as fact, in the M3 tradition of recorded mismatch
  over refusal — shape it when the Windows host first runs `resolve`.

## Definition of success

A developer on a fresh workstation of either OS reaches a working,
error-free editor session — services running and connected — with one
host document and two commands (`bootstrap`, then the development verb).
Releases are admitted only from digest-bound evidence produced where the
product runs. Drift anywhere in the stack is a recorded fact within a
day, not a discovery. And the 5.7 migration, when taken, is a line flip
whose safety was already proven by the records.
