# Facet Integrations

Each directory under `Facets/` owns the deployment-facing adapter and
compatibility contract for one HoloBike software domain.

A facet integration may:

- locate or fetch an explicitly selected source revision;
- invoke documented facet-owned build and test commands;
- validate expected artifact and protocol versions;
- stage published outputs into an assembly;
- provide configuration through declared inputs; and
- run product-level health checks.

It must not duplicate domain implementation, reach into private source modules
when a public command or artifact exists, silently edit a facet checkout, or
make generated copies authoritative.

Every executable facet adapter should eventually expose the same minimum
information: source identity, dirty state, build entry point, artifact
inventory, runtime requirements, compatibility version, deployment
destination, health result, and redacted diagnostics.
