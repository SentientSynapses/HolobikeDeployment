# Development Integration

`Development/` owns repeatable integration workflows used before a product
release is admitted to production provisioning.

The domains are intentionally separate:

- `Environment/` discovers and validates the developer host.
- `Assembly/` resolves selected source revisions and stages their outputs.
- `Emulation/` runs an assembled stack against simulated or virtualized
  dependencies.

These workflows consume the product-wide contracts under top-level
`Stack/`. Integration contracts do not live under `Development/` because
production provisioning consumes the same boundaries.

Development workflows may use local checkouts and disposable credentials, but
they must not silently weaken production policy. Every generated file belongs
under a documented `Generated/` directory or the repository-level `Artifacts/`
directory and remains untracked.
