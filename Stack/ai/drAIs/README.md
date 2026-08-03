# drAIs Repository Integration

## Source

- Repository: `ai_kit/drAIs`
- Integration domain: `ai`
- Source identity: an exact Git commit selected by an assembly manifest

This directory owns the deployment adapter to drAIs, not agent runtime source,
model weights, user context, or provider credentials.

## Assembly Contract

The adapter will invoke drAIs-owned build, test, and evaluation surfaces and
record the selected runtime, protocol, skillset, model profile, and sandbox
policy. External tools and services are declared capabilities rather than
copied into drAIs or this integration.

## Validation

Acceptance requires redacted diagnostics, compatible product-facing transport,
available declared tools such as uroborOS service controllers, and explicit
development or production provider selection. User-derived context and secret
provider values must never enter an assembly manifest or report.
