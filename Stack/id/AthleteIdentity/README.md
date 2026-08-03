# AthleteIdentity Repository Integration

## Source

- Repository: `id_kit/AthleteIdentity`
- Integration domain: `id`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns deployment metadata and adapter logic, not identity source
or athlete data.

## Assembly Contract

The adapter will invoke AthleteIdentity-owned build and test surfaces, collect
the selected IdentityClient artifacts, and record identity schema, action
surface, storage-policy, and provider-capability versions. Provider selection
is configuration; provider credentials are never declared data.

## Validation

Developer assemblies may select the explicit `LocalMock` provider. Production
acceptance requires the declared provider and transport, compatibility with the
HolobikeRider identity bridge, and proof that no credentials, refresh tokens,
private keys, or athlete records entered artifacts or reports.
