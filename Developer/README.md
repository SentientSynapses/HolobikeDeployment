# Developer Integration

`Developer/` owns repeatable integration workflows used before a product
release is admitted to production provisioning.

The domains are intentionally separate:

- `Environment/` discovers and validates the developer host.
- `Assembly/` resolves selected facet revisions and stages their outputs.
- `Emulation/` runs an assembled stack against simulated or virtualized
  dependencies.
- `Facets/` defines how the aggregator interacts with each authoritative
  repository.

Developer workflows may use local checkouts and disposable credentials, but
they must not silently weaken production policy. Every generated file belongs
under a documented `Generated/` directory or the repository-level `Artifacts/`
directory and remains untracked.
