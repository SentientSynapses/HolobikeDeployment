# Spec

`Spec/` is the specification of the deployed HoloBike software stack: every
document a person writes and reviews to say what the product is made of,
which combinations are legal, and what a release must satisfy before it is
admitted.

It specifies the stack, not the act. The workflows that build, emulate,
admit, and provision live under `Development/` and `Production/` and consume
this directory. What those runs produced lives under `Releases/`.

## Declared and attested

The Spec declares; `Releases/` attests. A declaration here says
`AthleteIdentity @ main`; the release record says `AthleteIdentity @ 5619c33,
clean, sha256:…`. Same subject, two states — and the same discipline the
protocol repositories enforce as "no binding without a fixture": a release
record is to the Spec what a conformance run is to a schema, evidence of
agreement.

| | `Spec/` | `Releases/` |
|---|---|---|
| Written by | a person, in a pull request | the assembler, from a run |
| States | intent | fact |
| Changes | when the product changes | never, once recorded |

## Filing rule

**If a document names more than one repository — which revisions compose,
which versions are compatible, which gates admit a release — it is a Spec
kind at this level. If it describes how to drive one repository, it belongs
to that repository's adapter under `Stack/`.** A plugin's synchronization
direction is a `Stack/` concern; which plugin revision ships with which
project revision is a revision manifest.

## Layout

`Stack/` and `Schemas/` exist because they hold content today. The remaining
kinds are described here rather than scaffolded as empty directories; each is
created by the change that first needs it:

| Directory | Holds |
|---|---|
| `Stack/` | the integration roster and per-repository contracts, grouped by domain |
| `Schemas/` | canonical JSON Schema for every declared kind |
| `Conformance/` | accepted and rejected fixtures for every schema |
| `Profiles/` | named product and development configurations |
| `Revisions/` | revision manifests: selected source revisions per release line |
| `Compatibility/` | cross-repository version constraints |
| `Policy/` | admission gates a release must satisfy |

The integration roster has one structural source of truth: the directories
under `Stack/`. The closed roster in `Schemas/environment.schema.json` and
the table in the root README are views of it and must agree.

## Rules

- The Spec binds; it never executes. If a `Stack/` contract needs executable
  adapter code, the code lands under `Development/Assembly/`, bound to the
  contract it implements.
- Schemas are canonical; a validator in any language is a binding that must
  agree with them, proven by fixtures under `Conformance/`.
- "Manifest" names exactly one declared kind — the revision manifest.
  Nothing else here is called one, and a release record resolves a manifest
  rather than being one.
- A Spec document never contains a secret, a credential, or a private key —
  not even a path to one that would be meaningful off this machine.
- A mutable branch name is not a release identity. Declarations may select by
  branch for development profiles; a release line resolves to exact commits.
- Machine-specific documents are not committed. `environment.schema.json`
  describes one workstation's checkout and toolchain paths; the document
  itself lives at the gitignored `.local/environment.json`, and the example
  beside the schema shows its shape.
