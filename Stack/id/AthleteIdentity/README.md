# AthleteIdentity Repository Integration

## Source

- Repository: `id/AthleteIdentity`
- Integration domain: `id`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns AthleteIdentity's declarative deployment contract, not
adapter implementation, identity source, credentials, or athlete data.

## Assembly Contract

The leaf invokes AthleteIdentity's repository-owned IdentityClient build and
stages the service and CLI artifacts. Its serve/probe pair runs the staged
service from disposable profile state and proves health through the service's
wire protocol. Provider selection is non-secret configuration; provider
credentials are never declared data.

## Validation

The current host topology uses the filesystem key provider only beneath its
disposable emulation state and makes no production-provider claim. Production
acceptance requires the declared provider and transport, compatibility with the
HolobikeRider identity bridge, and proof that no credentials, refresh tokens,
private keys, or athlete records entered artifacts or reports.
