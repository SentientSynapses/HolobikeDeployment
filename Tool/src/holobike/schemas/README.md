# Schemas

Canonical JSON Schema for every kind of document this repository declares. The
schema is the contract; a validator written in any language is a binding that
must agree with it.

| Schema | Kind |
|---|---|
| `environment.schema.json` | One workstation's checkout and toolchain paths. Machine-specific: the document lives at the gitignored `.local/environment.json`, and `tests/fixtures/environment`/accepted.full.json` shows its shape. |
| `integration.schema.json` | One Stack leaf's drive contract: roster identity, source origin, repository-owned prove/build/serve/probe entry points, and staged artifact paths. Instances live at `Stack/<domain>/<Integration>/integration.json`. |
| `revisions.schema.json` | One line's declared composition: branch selections for development lines, full 40-hex commits for release lines, exactly one of the two per integration. Instances live at `Revisions/<line>.json`. |
| `record.schema.json` | The five lifecycle facts: resolution, bootstrap, assembly, emulation, and release. Parent records carry SHA-256 bindings; assemblies inventory staged bytes; releases carry the admitted chain. Pre-admission records live under `Artifacts/records/`; admitted copies live under `Releases/`. |
| `policy.schema.json` | Declared constraints: named gates evaluated by `resolve`, verdicts riding every record. Instances live at `Policy/<policy>.json`; today's kind is `tree_parity`. |
| `profiles.schema.json` | A named composition of integrations and its non-secret execution topology. Instances live at `Profiles/<profile>.json`; the current executor supports bounded host service members. |

A compatibility schema arrives with the workflow that reads it; everything
else declared so far is above, each held by its corpus under
`../Conformance/`.

## Rules

- **No binding without a fixture.** When a schema gains a validator, it gains
  accepted and rejected fixtures under `../Conformance/` at the same time,
  and every implementation runs the same ones. This is the discipline
  `AthleteIdentity/IdentityProtocol` uses to hold two languages to one
  contract.
- Validation is fail-closed: unknown properties are rejections, not
  tolerances. A misspelled integration name must fail rather than silently
  deselect an integration.
- JSON decoding is part of the contract: bindings reject duplicate object
  members and non-finite numeric extensions. Cross-field rules that JSON
  Schema cannot express directly — such as unique policy gate names and
  topology keys being profile members — remain mandatory binding semantics
  held by rejected fixtures.
- A schema change that invalidates a document already recorded under
  `../Releases/` is a breaking change and needs a new `schema_version`,
  not an edit.
