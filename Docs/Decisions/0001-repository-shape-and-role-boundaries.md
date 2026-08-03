# 0001 — Repository shape: partition by function, not stage

Status: accepted, 2026-08-03.

## Context

The scaffold went through three forms in quick succession. The initial sketch
was `Manifests/ Stack/ Development/ Production/ Releases/` — stage and nature
labels. The word *manifest* kept needing legislation because common usage
puts it on both sides of the declared/resolved line (a Kubernetes manifest is
intent, a ship's manifest is fact), so `Manifests/` was renamed `Spec/` and
`Stack/` folded inside it. That exposed the real problem: nearly everything
in a deployment repository is declarative, so the Spec wrapper was on course
to hold ~90% of the substance. A directory that contains nearly everything
distinguishes nothing — a boundary must be earned by the partition it makes.

Prior art consulted: AOSP `platform/manifest` and Fuchsia `integration`
(manifest-only aggregators), Zephyr `west` (thin driver + manifest),
`openstack/releases` (PR-reviewed declarations, in-repo validation tooling),
GitOps environment repositories (declared state, drift fails), Yocto layers
(per-upstream recipes, generic engine), Nix flakes (declared/locked), SLSA
and in-toto (attestation). None wraps its declarations in a spec directory:
**the repository is the specification.** Executors are thin, delegate builds
to the sources they compose, and either live at arm's length (west, repo) or
in-repo when single-purpose (openstack/releases tooling).

## Decision

The top level partitions by function. Every directory is one role:

| Directory | Role |
|---|---|
| `Stack/` | declare the members — roster + per-repository integration contracts |
| `Revisions/` | declare the composition — selected revisions per release line |
| `Policy/` | declare the constraints — parity and admission gates |
| `Schemas/` | declare the shapes — canonical schema for every declared kind |
| `Conformance/` | prove the bindings — accepted/rejected fixtures per schema |
| `Assembler/` | realize — the one executable |
| `Releases/` | attest — admitted records, written by runs, never edited |
| `Provisioning/` | deliver — device-facing workflows behind admission |

**The filing rule:** selects → `Revisions/`; constrains → `Policy/`; drives
one repository → its `Stack/` leaf; shapes documents → `Schemas/`; executes →
`Assembler/`; written by a run → `Releases/`.

Stages are data, not directories. Development-versus-production lives in
profiles, policies, and record status — there is no `Development/` or
`Production/` floor of the building.

The executable lives in-repo as a named tool — `Assembler/`, CLI
`holobike-assemble`, a Python package in the uroborOS-Lab idiom. This is a
deliberate deviation from the arm's-length executor pattern, justified while
the tool is single-purpose; extraction is cheap if it ever generalizes. It
remains a consumer of the declarations and of repository-owned entry points —
build heterogeneity (Unreal packaging, CMake/vcpkg, npm workspaces, Debian
packaging, Python) rules out any owning engine.

Two tests garrison the boundaries:

- **Nature test** — declared content is reviewable without executing
  anything; realized content has side effects; attested content is written
  by a run.
- **Scope test** — this repository specifies the *product*. A tool's own
  contract lives beside the tool (`Assembler/README.md`), exactly as each
  domain repository keeps its own documentation.

## Consequences

- Directories are created by their first content. `Revisions/`, `Policy/`,
  and `Conformance/` are described, not scaffolded; `Profiles/` and
  `Compatibility/` are future kinds on the same terms.
- The declared/attested vocabulary survives the flatten: *manifest* names
  exactly one declared kind (the revision manifest), and a release record
  resolves declarations rather than restating them.
- The release-record schema is adopted, not invented: uroborOS-Lab's
  run-record idiom (`run.json`, `source.json`, `steps/*.json`) hardened with
  digests and SLSA provenance vocabulary.
- Emulation targets virtual machines only, never the host.
- This was the last cheap restructure: the first Assembler verb hardcodes
  paths, and every path it reads is one this layout decided.
