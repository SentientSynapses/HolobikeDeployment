# Manifests

`Manifests/` holds what this repository **declares**: the documents a person
writes and reviews to say which revisions compose into a HoloBike product,
which combinations are legal, and what a release must satisfy before it is
admitted.

The name is the repository's own. These documents are already called manifests
throughout: "cross-repository compatibility and deployment manifests",
"revision manifests", and — in every Stack leaf — "an exact Git commit selected
by an assembly manifest". They are deliberately not called contracts, because
that word is already spoken for: `Development/README.md` states that the
product-wide contracts live under `Stack/`.

## Declared and resolved

A manifest is an input. A release record is its **resolved** form: the
declaration says `AthleteIdentity @ main`, the record says
`AthleteIdentity @ 5619c33, clean, sha256:…`. Same subject, two states, and the
distinction is the reason both directories exist.

| | `Manifests/` | `Releases/` |
|---|---|---|
| Written by | a person, in a pull request | the assembler, from a run |
| States | intent | fact |
| Changes | when the product changes | never, once recorded |

## Manifests or Stack?

The dividing rule: **if it names more than one repository, it is a manifest; if
it describes how to drive one repository, it belongs to that repository's
adapter under `Stack/`.** A plugin's synchronization direction is a Stack
concern. Which plugin revision ships with which project revision is a manifest.

## Intended layout

`Schemas/` exists because it holds the first declared kind. The rest are
described here rather than scaffolded as empty directories, and each is created
by the change that first needs it:

| Directory | Holds |
|---|---|
| `Schemas/` | canonical JSON Schema for every declared kind |
| `Profiles/` | named product and development configurations |
| `Revisions/` | selected source revisions per release line |
| `Compatibility/` | cross-repository version constraints |
| `Policy/` | admission gates a release must satisfy |
| `Conformance/` | accepted and rejected fixtures for every schema |

`Policy/` sits slightly awkwardly under a directory called Manifests, since a
gate is not quite a declaration of composition. It stays here until it grows a
shape of its own rather than earning a sixth top-level directory for a handful
of files.

## Rules

- Schemas are canonical; any validator in any language is a binding that must
  agree with them, proven by fixtures under `Conformance/`.
- A manifest never contains a secret, a credential, or a private key — not even
  a path to one that would be meaningful off this machine.
- A mutable branch name is not a release identity. Declarations may select by
  branch for development profiles; a release line resolves to exact commits.
- Machine-specific documents are not committed. `environment.schema.json`
  describes one workstation's checkout and toolchain paths; the document itself
  lives at the gitignored `.local/environment.json`, and the example beside the
  schema shows its shape.
