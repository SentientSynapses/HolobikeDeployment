# drAIs Repository Integration

## Source

- Repository: `ai_kit/drAIs`
- Integration domain: `ai`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns drAIs's declarative deployment contract, not adapter
implementation, agent runtime source, model weights, user context, or provider
credentials.

## Deployables

`DraisClient` reaches the device; `DraisServer` reaches the estate. The leaf
exposes drAIs's repository-owned full evaluation surface as its proof command.

### `DraisServer` builds to bytes, and is not yet packaged

The declared build is the one drAIs's own README documents — `drais.sh build`,
which configures and builds the default tree — and the artifact is
`drais_gateway`, the operated tier's stream relay. That is the standing
`IdentityServer` has: bytes `admit` can hash. The artifact path names the
Ninja build directory drAIs selects when `ninja` is on the PATH, which is the
only case this workstation exercises.

What it does not have is a way to be placed. drAIs's own plan says so
(register #17: "built and not packaged: no unit, no install rule") and names
the fix: Phase 10 takes the operated tier off the machine, Cloud Run first,
with the container as its packaging (10c). Until that lands, `provision
drais` refuses and says this is why. When it lands, the container build joins
this leaf the way `IdentityServer`'s image did — one declaration here, no
change to the tool.

Future build artifacts will record the selected runtime, protocol, skillset,
model profile, and sandbox policy. External tools and services are declared
capabilities rather than copied into drAIs or this integration.

## Validation

Acceptance requires redacted diagnostics, compatible product-facing transport,
available declared tools such as uroborOS service controllers, and explicit
development or production provider selection. User-derived context and secret
provider values must never enter a declared document, a release record, or a report.
