# drAIs Repository Integration

## Source

- Repository: `ai_kit/drAIs`
- Integration domain: `ai`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns drAIs's declarative deployment contract, not adapter
implementation, agent runtime source, model weights, user context, or provider
credentials.

## Assembly Contract

The leaf currently exposes drAIs's repository-owned full evaluation surface as
its proof command. Future build artifacts will record the selected runtime,
protocol, skillset, model profile, and sandbox policy. External tools and
services are declared capabilities rather than copied into drAIs or this
integration.

## Validation

Acceptance requires redacted diagnostics, compatible product-facing transport,
available declared tools such as uroborOS service controllers, and explicit
development or production provider selection. User-derived context and secret
provider values must never enter a declared document, a release record, or a report.
