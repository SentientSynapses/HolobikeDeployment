# Production

`Production/` owns the admission and delivery boundary for release-qualified
HoloBike assemblies.

Production workflows consume immutable source identities, verified artifacts,
release policy, and canonical validation evidence. They must fail closed on a
missing digest, incompatible integration, dirty source, unsigned artifact,
absent hardware capability, or incomplete release gate.

Development path mappings, mutable checkouts, emulation-only providers, test
credentials, and scaffold modes are not production inputs.
