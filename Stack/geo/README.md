# Geography Integration

This integration connects the engine-neutral sources used to construct the
rideable world:

- [`HexAtlas/`](HexAtlas/README.md) owns geographic facts and atlas delivery.
- [`Assetscape/`](Assetscape/README.md) owns the classified asset palette and
  verified asset resolution.

HexAtlas remains authoritative for geographic ingestion, SourceAtlas and
MasterAtlas construction, atlas schemas, serving, client caching, and atlas
protocols. Assetscape remains authoritative for asset taxonomy, catalog and
vault contracts, curation, and resolution. HoloBike Deployment selects
compatible software and data revisions, stages only declared outputs, and
validates their joint compatibility with HolobikeWorlds and the target
experience.

The deployment boundary should distinguish:

- executable versions for AtlasServer and AtlasClient;
- atlas root identity, layout version, and content revision;
- Assetscape catalog, vault, and resolver compatibility;
- whether data is bundled, preloaded, streamed, or fetched after deployment;
- service endpoints and cache policy;
- HolobikeWorlds protocol compatibility; and
- data provenance and storage requirements.

Large atlas data and provider caches do not belong in this Git repository.
Assemblies should reference immutable manifests and verified artifact
locations.
