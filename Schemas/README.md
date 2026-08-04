# Schemas

Canonical JSON Schema for every kind of document this repository declares. The
schema is the contract; a validator written in any language is a binding that
must agree with it.

| Schema | Kind |
|---|---|
| `environment.schema.json` | One workstation's checkout and toolchain paths. Machine-specific: the document lives at the gitignored `.local/environment.json`, and `environment.example.json` shows its shape. |
| `integration.schema.json` | One Stack leaf's drive contract: roster identity, kit, repository name, and repository-owned entry points (`prove` first). Instances live at `Stack/<domain>/<Integration>/integration.json`. |

Schemas for profiles, revision manifests, compatibility, and policy arrive
with the workflows that read them — the first of those is the read-only
preflight described in `Assembler/README.md`.

## Rules

- **No binding without a fixture.** When a schema gains a validator, it gains
  accepted and rejected fixtures under `../Conformance/` at the same time,
  and every implementation runs the same ones. This is the discipline
  `AthleteIdentity/IdentityProtocol` uses to hold two languages to one
  contract.
- Validation is fail-closed: unknown properties are rejections, not
  tolerances. A misspelled integration name must fail rather than silently
  deselect an integration.
- A schema change that invalidates a document already recorded under
  `../Releases/` is a breaking change and needs a new `schema_version`,
  not an edit.
