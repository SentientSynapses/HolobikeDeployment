# Athlete-Identity Integration

This integration connects `id_kit/AthleteIdentity`.

Repository adapter:

- [`AthleteIdentity/`](AthleteIdentity/README.md)

AthleteIdentity remains authoritative for identity schemas, provider-neutral
client behavior, authentication flows, local identity storage, cryptography,
and provider adapters. HoloBike Deployment selects a compatible client
artifact and provider profile, supplies deployment configuration through a
secure external channel, and validates the public identity surface consumed by
HolobikeRider and HolobikeExperience.

Developer emulation may use the explicit `LocalMock` provider. Production
assemblies must identify their selected provider and transport without
embedding provider credentials, athlete credentials, refresh tokens, or
private key material in Spec documents, reports, or images.

Compatibility checks should cover identity schema, client action surface,
provider capability, local-storage policy, and the Unreal identity bridge.
