# 0003 — Validation concentrates at declared seams

Status: accepted, 2026-08-04.

## Context

ADR 0002 settled who owns validation — each repository proves itself, this
repository proves the composition, Provisioning proves the device. It did
not settle where validation code lives *inside* a repository, and two
failure shapes have been observed on this stack:

- **The external lab.** uroboros_lab reached ~15,000 lines, of which ~2,900
  are a bespoke runner/CLI/record engine that standard runners replace, and
  much of the rest is internal-state fixture machinery — hand-built `/etc`
  trees, shadow doubles of system tools — that exists because uroborOS
  offered no drivable surface. Held below production standards while running
  privileged, it produced this month's host incident.
- **The sprinkled shadow tree.** One `Tests/` directory per submodule tracks
  module count, not seam count. The geography breeds per-suite mocks and
  fixture builders, and the test tree becomes a parallel structure that
  decays on its own schedule.

Operator direction: each repository submodule exposes a clean testable
surface — in many cases the same surface as its CLI/control integration —
and test logic is not sprinkled throughout.

## Decision

**The seam that earns a module is the seam that tests it.** This extends the
existing earned-boundary doctrine: a module boundary must be earned by a
real seam, and that same seam is where its validation lives.

- Tests touch declared seams only: schema/conformance fixtures, `Public/`
  library APIs, and control surfaces (CLI verbs, host and daemon surfaces,
  wire protocols). Never internals.
- **Test-location count is bounded by seam count, not module count.** A
  submodule without its own seam is validated through its owner's seam and
  gets no test directory.
- **Prefer the control surface.** It serves three consumers at once:
  developer validation, the repository's own gates, and deployment
  composition — the Assembler drives the same verbs. A repository's Stack
  leaf declares this one surface for both "prove me" and "drive me".
- **Doubles ship as in-product seam implementations** — the LocalMock
  pattern. Fault injection is a capability of the seam implementation, not a
  header in a test directory.
- **Reaching past a seam to test is a design finding**: a missing verb or an
  unearned boundary. Fix the surface; do not write the mock.
- The pyramid stands, every layer a seam: conformance fixtures at the
  bottom, library-seam vectors for algorithmic cores (fast, in-process),
  control surfaces on top.
- **Never a `Lab/` module.** A category directory for validation is a junk
  drawer with a fence around it; the fence legitimizes the junk.

## Consequences

- Migration is pull-driven and standard-raising: lab capabilities promote to
  surfaces per 0002's promotion rule; existing suites consolidate toward
  seams opportunistically. Green suites are never churned wholesale to
  comply — moves, not rewrites, and coverage never drops.
- A repository's published validation surface is what its Stack leaf cites;
  the uroborOS leaf is already worded this way.
- Where a control surface does not exist yet, its absence is the backlog
  item — not a license for internal fixtures.
- Bespoke test-runner machinery is presumed dead on arrival: standard
  runners execute suites, and the Assembler owns cross-repo run records.
