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
- `Schemas/*.example.json` documents are validated as accepted fixtures in
  place, so an example can never drift from its own contract.
- Document decoding is strict across every binding: duplicate object members
  and non-finite numeric extensions are rejected before schema validation.
- Fixtures are data. Nothing here executes, and nothing here is a secret.
