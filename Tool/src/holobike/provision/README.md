> **The code moved.** Device identity provisioning is now
> `holobike provision device`, implemented under
> `Tool/src/holobike/provision/`. Provisioning is a verb of the
> one tool rather than a second executable beside it; this document keeps the
> workflow it always described. `Provisioning/` retires as a tier when Phase 4
> moves the tree (D-14).

# Provisioning

Provisioning turns an admitted HoloBike release into a configured physical
device and records evidence of the resulting state. It sits behind the
admission boundary: its inputs are immutable source identities, verified
artifacts, release policy, and canonical validation evidence, and it must
fail closed on a missing digest, incompatible integration, dirty source,
unsigned artifact, absent hardware capability, or incomplete release gate.
Development path mappings, mutable checkouts, emulation-only providers, test
credentials, and scaffold modes are not provisioning inputs.

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

The first executable primitive is deliberately narrower than production
provisioning:

```bash
./a separate executable install \
  --root /path/to/offline-target-root \
  --input /path/to/device-identity.json
./a separate executable verify \
  --root /path/to/offline-target-root
```

It always targets `/etc/holobike/device-identity.json` beneath an explicit
offline root. The live root, including a bind-mounted alias of it, is refused.
Inputs use the closed, non-secret HolobikeCore device-identity v1 vocabulary;
the canonical domain schema remains owned by HolobikeCore. Reads are bounded,
single-link, descriptor-based, and checked for concurrent mutation. Writes use
descriptor-relative no-follow operations, a per-target advisory lock, atomic
replacement, fsync, mode and ownership verification, and a monotonically
increasing provisioning revision. Untrusted writable target directories,
intermediate links, final links, hard links, malformed existing state, and
arbitrary output paths are refused. The implementation has no account-database
or secret-store API.

This primitive is a deployment binding, not a second owner of the identity
contract. The full release provisioner must consume the schema packaged by the
admitted HolobikeCore artifact rather than allowing this copy of the v1 field
set to evolve independently.

The broader production workflow remains blocked until the owned uroborOS
image, authenticated encrypted-root release path, production key custody,
rollback, recovery, and hardware acceptance gates are complete.
