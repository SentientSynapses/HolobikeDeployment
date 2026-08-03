# Production Provisioning

Provisioning turns an admitted HoloBike release into a configured physical
device and records evidence of the resulting state.

The intended high-level transaction is:

1. identify and validate the target hardware;
2. verify the release record, signatures, artifact digests, and compatibility;
3. install the release-qualified uroborOS image;
4. install mode-selected bike services and the packaged HoloBike experience;
5. provision public configuration and inject secrets through an external,
   audited secret channel;
6. perform boot, device, display, network, identity, geography, intelligence,
   and experience health checks;
7. record non-secret device and release provenance; and
8. seal the device for delivery or return it to a defined recovery state.

Provisioning must be resumable or safely restartable at every destructive
boundary. It must never log passwords, recovery material, provider tokens,
private signing keys, or raw Secret Keeper values.

This directory is documentation-only in the initial scaffold. Executable
production provisioning remains blocked until the owned uroborOS image,
authenticated encrypted-root release path, production key custody, rollback,
recovery, and hardware acceptance gates are complete.
