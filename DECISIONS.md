# Decisions

The standing decisions behind HoloBike Deployment, and their status.

D-07 sends a decision that has **landed** to the code it governs — the gates'
contract to `gates.py`, the filing rule to `README.md`, the seam rules to
`Conformance/README.md`. That rule gave landed decisions a home and left the
rest nowhere but the plan, where fourteen of them crowded out the planning.
This file is the home it never gave them.

What belongs here: a position taken, why, and what would overturn it. What
does not: the plan itself (`PLAN.md`), or a decision fully expressed by the
code that implements it — that one is documented where it lives, and its entry
here says so and stops.

Numbers are permanent. A superseded decision keeps its number and says what
replaced it, because the commits that cite it do not move.

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
- **D-19 `destination` chains; the terminal is derived** *(ruled
  2026-08-24)*. Five leaves — HolobikeDevice, HolobikeRider, HolobikeWorlds,
  HoloviewDisplay, OrielUI — declare no entry points and no artifacts,
  because UBT compiles them into HolobikeExperience's package. They name that
  package as their destination rather than a place. Chosen over a separate
  `compiled_into` field for one reason that outweighs the rest: a device
  release record must name the plugin revisions compiled into the package, or
  it describes half the build — the fault D-10 identified, one tier over.
  With one chaining field that is a transitive walk; with two fields it is
  two lists to keep in step. Three rules make it safe: `device` and `server`
  are reserved lowercase terminals and every other value is a member's exact
  PascalCase name (D-14), so the union is unambiguous by construction; the
  loader proves each chain resolves to an existing member, terminates, and
  has no cycles — a cross-document check, which is where Phase 1 puts those
  anyway; and consumers ask only for the resolved destination, confining the
  two-kinds knowledge to one resolver. Rejected alternative: the project
  listing its own plugins, which restates what `HolobikeExperience.uproject`
  already declares and creates a drift surface between two files that must
  agree. **Known evolution:** a second UE project makes a single value a lie,
  and the fix is to allow an array — a widening, not a break, and equally
  needed under any of the shapes considered.
- **D-20 `Releases/` stays before it holds a record** *(ruled 2026-08-24)*.
  Zero release records have ever been written, so the structure-born-by-
  content rule would delete the tier. It stays on the strength of Phase 5,
  which is what fills it. Recorded because the doctrine would otherwise be
  correctly applied to the wrong subject: the rule exists to stop directories
  being scaffolded for futures nobody has committed to, and this one has a
  phase.
- **D-21 The record chain stays; there is no single build record** *(ruled
  2026-08-24)*. The plan called for collapsing five record kinds into one
  written by `build`. Refused on evidence found while implementing it.
  `Artifacts/records/` holds 53 resolution records, 4 assembly, 3 emulation,
  1 admit and 0 bootstrap. The resolution record is not an internal artifact
  of a build — it is the daily cadence's product, written by a timer that
  resolves and does nothing else, and it is the whole of "drift anywhere in
  the stack is a recorded fact within a day". One build record written by that
  timer would be four-fifths empty, or resolution would stop being recordable
  alone and drift detection would end with it. Two supporting reasons: `--only`
  keeps every stage independently runnable, so a person can still assemble
  against a stale resolution and the digest binding between records is what
  catches it; and the `release` kind has zero instances, so redesigning it
  before Phase 5 writes one for real is designing from ignorance. **What this
  costs:** `admit.py`'s chain apparatus stays, and with it the line target
  that assumed its removal — the tool is 4,456 lines, not the ~2,700 estimated
  before any of this was built. **Revisit if** the chain's shape proves wrong
  when a record first travels between two machines in Phase 5, which is the
  event that would actually test it.
