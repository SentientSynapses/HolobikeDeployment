# Conformance

Accepted and rejected fixtures for every declared kind, one subdirectory per
schema. The schema under `Schemas/` is the contract; a validator in any
language is a binding, and every binding runs the same fixtures — this is
what "no binding without a fixture" means in practice.

Rules:

- A fixture's verdict is its name: `accepted.*.json` must validate,
  `rejected.*.json` must refuse. The suite fails on any file it cannot
  classify — a fixture nobody runs is a contract nobody keeps.
- A rejected fixture exists per rule, not per bug: every constraint the
  schema states should have at least one fixture that violates only it.
- An accepted fixture doubles as the worked example a human copies:
  `environment/accepted.full.json` is what a new workstation starts
  from. One document teaches the shape and proves it, so an example
  cannot drift from its own contract by construction rather than by
  a test that compares two files.
- Document decoding is strict across every binding: duplicate object members
  and non-finite numeric extensions are rejected before schema validation.
- Fixtures are data. Nothing here executes, and nothing here is a secret.

## Where validation lives

Fixtures are the bottom of a pyramid whose every layer is a seam, and the rule
that places them is the same one that earns a module: **the seam that earns a
boundary is the seam that tests it.**

- Tests touch declared seams only — schema fixtures here, library APIs, and
  control surfaces (CLI verbs, daemon surfaces, wire protocols). Never
  internals.
- Test-location count is bounded by seam count, not module count. A submodule
  without its own seam is validated through its owner's and gets no test
  directory.
- Prefer the control surface: it serves developer validation, the repository's
  own gates, and deployment composition at once, which is why a `Stack/` leaf
  declares one surface for both "prove me" and "drive me".
- Doubles ship as in-product seam implementations. Fault injection is a
  capability of the implementation, not a header in a test directory.
- Reaching past a seam to test is a design finding — a missing verb or an
  unearned boundary. Fix the surface; do not write the mock.
- Never a `Lab/` module. A category directory for validation is a junk drawer
  with a fence around it, and the fence legitimizes the junk.
