# HolobikeDeployment Plan

Direction and pending decisions for the deployment tool. The README owns
identity and current state; the code and the nearest README own settled
rationale; this file owns where the tool is going and why. When a milestone
lands, its entry here shrinks to a line and its reasoning moves into the code
it governs — a plan that restates what the repository already proves is a
second copy waiting to drift, and so is a decision record kept beside it.

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

## Standing (2026-08-18)

The core build-out (M1–M8) is complete: all six verbs live, 78 Assembler +
13 Provisioning tests green, five run-record kinds digest-bound, admission
the only writer of tracked `Releases/`. M9 is complete: **all four parity
gates pass on the dev line and `resolve` exits 0** — the composition is
green for the first time, and the cadence that keeps it honest runs daily.
Enrollment of HoloviewDisplay as the twelfth integration exists on branch
`integrate/holoviewdisplay`, paired with a HolobikeExperience branch of the
same name; both are unlanded, and landing them is M10.

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
2. verify each plugin resolves through its declared
   `AdditionalPluginDirectories` entry — one tree, never a copy (D-08);
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
(M15) — earned by content, like every tier before it.

## Decisions established 2026-08-15/18

- **D-01 `linked` verdict.** `tree_parity` gains a third honest outcome:
  when both sites resolve to the same real path, the gate reports
  `linked` (parity by construction) instead of a vacuous `pass`. The
  verdict names the shared target, and admits exactly as a pass does.
  (Superseded in part by D-08: links were to have been the migration
  target for the dual copies, and are not — the copies go away entirely
  instead. The verdict stays correct for any site that is linked, and
  costs nothing to keep.)
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
  committed line. The Assembler gains no scheduler — systemd is the
  scheduler, and this repository declares the unit templates
  (`Assembler/timers/`) on the `environment.example.json` precedent:
  tracked template, per-host install into `~/.config/systemd/user/`.
- **D-07 Doctrine is written where it applies, not in a decision tier.**
  *(Revised 2026-08-19; `Docs/Decisions/` retired.)* A decision that has
  landed is stated in the code it governs or in the nearest README — the
  gates' contract lives in `gates.py`'s docstring, the filing rule in
  `README.md`, the seam rules in `Conformance/README.md`. A decision that
  has not landed lives here until it does. The four records this plan
  once scheduled had already drifted from the code they described while
  the code stayed correct, which is the failure mode the split prevents.
  Still owed a written home, as each lands: roster membership and why
  nonmembers carry reasons (M13); the record chain's digest binding,
  immutability, and `Releases/` as sole tracked writer; and per-host
  environments with producer-named records (M14).
- **D-08 One tree per repository; no mounts.** A project consumes a
  plugin where it lives, through the project descriptor's
  `AdditionalPluginDirectories` — the engine's supported mechanism for a
  plugin outside the project tree, honoured by the plugin manager, by
  UBT, and by the packaging step's plugin relocation. Copies and links
  are both retired: with one tree, dual-copy drift cannot occur rather
  than being detected afterwards. Two properties measured on 2026-08-18
  decided it over a link: binaries land in the *consuming project's*
  `Binaries/`, so the plugin repository stays clean and two projects
  cannot contend for one output directory; and module loading works,
  where a link broke it — UBT computes a dependency's RPATH from the
  output file's own directory, so binaries reached through a link
  resolved `${ORIGIN}` to the real path, got the hop count wrong, and
  failed to find an engine-plugin dependency at load. The parity gates
  retire per plugin as each converts. The `linked` verdict from M9 stays
  correct but becomes vestigial, which is the honest cost of D-08.
- **D-09 The workstation tree is canonical, and mirrors the Stack.**
  Checkouts live at `<root>/<domain>/…`, the same shape `Stack/` already
  has — `ue/plugins/` and `ue/projects/` included. Paths become derivable
  from tracked leaf data (`domain` + `repository`) instead of declared per
  machine, so a host document shrinks to a root, an identity, and any
  toolchain paths that cannot be derived. Because plugin discovery
  recurses and stops at the first descriptor in a hierarchy, one
  `AdditionalPluginDirectories` entry pointing at `ue/plugins` finds every
  plugin repository — so enrolling a new plugin needs no project edit.
  That is only safe because the split gives `ue/plugins` a directory
  containing nothing else; a flat `ue/` would also scan the legacy demo's
  vendored plugin copies.

## Implementation phases

Phases continue the milestone numbering from the completed build-out
(M1–M8). Each phase is a commit family carrying its own verification;
dependencies between phases are named, and nothing else blocks.

### M9 — gate truth — COMPLETE 2026-08-18

The `linked` verdict, its contract stated in `gates.py`, and the declared
resolve cadence landed as `0c1d4a8`. The worlds mount closed by one-way sync: 34 mismatches,
every one proven a stale mount (all 22 differing files byte-matched
older repository commits; all 8 mount-only files were deliberate
repository removals — the RidePathGraph rename, the junction-surface
deletion, the dead-actor purge), so the sync was lossless by
construction. **All four gates now pass on the dev line, 11/11
selections resolved, exit 0 — the first fully green resolution.**

### M10 — land the HoloView integration

Cross-repo sequencing. The rebase is done locally and verified; what
remains is landing it and the deployment side.

- **Done 2026-08-18 (local, unpushed).** `integrate/holoviewdisplay`
  rebased onto `main` — the identity trunk — in five commits. No binary
  asset overlapped, so constraint 1's pick-the-trunk rule never fired.
  Verified by build and launch, not by reading: editor builds, plugin
  loads, zero dlopen failures, zero CoreRedirects errors, zero
  `SimulatedRealityMock` mentions, provider selection falls back to
  `NullDisplayPlatform` by name.
- The mount is gone: HoloviewDisplay is consumed through
  `AdditionalPluginDirectories` (D-08), so there is one tree and the
  gitignore rule the link needed is deleted rather than fixed.
- **Found by doing it, and owed upstream:** the two commits carrying the
  packaging and 5.7 fixes were almost entirely edits to *mounted* plugin
  copies, never backported. Landing them as-is would have buried four
  real fixes where the next sync deletes them. Only the Experience-owned
  `Build.cs` change stayed; the rest are owed to `HolobikeWorlds`
  (`RidePathGraph::FindByWaylinkId`, an unguarded `UFUNCTION` over a
  `WITH_EDITOR` body — one of the pair is already fixed as `0770c09`),
  `HolobikeDevice` (a codec leak and two `AllowedClasses` headers), and
  `HolobikeRider` (the automation-context macro, in the file `main`
  renamed to `IdentityIOTests.cpp`).
- Re-stack `upgrade/ue57` on the landed result.
- HolobikeDeployment: land the enrollment commit (`92d32b1`) — twelfth
  integration — at the schema v1 spelling; the `kit` → `domain` rename is
  held for M11's single bump. Its parity gate is now pointless under
  D-08 and should not land with it.
- Fast-forward this workstation's `HoloviewDisplay_uplugin` checkout
  (done) and add its path to `.local/environment.json` on every host that
  carries it.

**Exit gate:** `resolve --line dev` resolves twelve of twelve with no
gate for HoloviewDisplay to fail, because it has no second copy; and
Experience `main` carries both workstreams under the load check.

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
- Collapse `Schemas/environment.example.json` into
  `Conformance/environment/accepted.full.json`. The two documents differ
  today by two toolchain path prefixes and nothing else — one shape held
  in two places, which is the drift this repository gates against
  elsewhere. The fixture proves the validator accepts a full document
  and the example teaches a human what to write; one file does both.
  Point the suite's `EXAMPLE` binding at the fixture, cite that path
  from `Schemas/README.md` and `Assembler/README.md`, and delete the
  example. Two further citations name the file as the tracked-template
  precedent — D-06 above and `Assembler/timers/README.md` — and must
  name its successor instead; the pattern outlives the filename. Folded
  in here because the v2 sweep rewrites both documents anyway —
  collapsing separately would touch them twice.

**Exit gate:** preflight cannot call the wrong engine "present"; no
schema accepts both spellings of anything; one tracked document carries
the environment shape; the suite is green at the new constants.

### M12 — the canonical tree

Depends on M11 (host identity), and wants a quiet moment: it moves every
checkout on a workstation while other agents hold working trees.

- Adopt the layout: `<root>/{ai,bike,geo,id,os,ue}`, with
  `ue/plugins/` and `ue/projects/` mirroring `Stack/ue/`. Rename the
  Stack's `ue/project/` to `ue/projects/` so the map and the territory
  agree; `plugins/` already sets the plural-container convention and the
  singular only reads correctly while there is exactly one project.
  HolobikeDeployment sits at the root, beside the domains it specifies.
- `Schemas/environment.schema.json`: `checkouts` gives way to a single
  `root`, with per-integration paths derived as
  `<root>/<domain>/<repository>` (UE gaining the `plugins`/`projects`
  level). Keep an optional per-integration override for a checkout that
  genuinely cannot sit in the tree, and record its use as a fact.
- `bootstrap` materializes the tree rather than cloning into declared
  paths — it already holds `domain`, `repository`, and `origin` for every
  leaf, so a fresh workstation becomes: clone this repository, write a
  host document, run bootstrap.
- Convert each remaining dual copy to `AdditionalPluginDirectories` and
  delete its parity gate as it converts; point the descriptor at
  `ue/plugins` once, not at each repository.
- Migration is an announced operation: absolute paths live in scripts,
  IDE configuration, and every host document, and other agents hold
  working trees in the repositories being moved.

**Exit gate:** a host document is a root plus an identity; no plugin
exists in two places; `bootstrap` can build the tree from nothing but the
Stack and a root.

### M13 — lines and roster

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
- The roster-membership rule — what makes a repository a stack member,
  and why nonmembers carry reasons — is written into `Stack/README.md`
  beside the roster it governs.

**Exit gate:** fourteen integrations resolve on two lines on cadence,
and an unenrolled repository adjacent to the stack is a named preflight
problem, not a discovery.

### M14 — the panel host

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
- The record chain's rules go into `Schemas/record.schema.json`'s own
  description fields and `Releases/README.md`; the host rules into
  `Schemas/environment.schema.json` and `Assembler/README.md`.

**Exit gate:** a release record admitted from evidence produced on the
machine where the product actually runs.

### M15 — the development composition

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
