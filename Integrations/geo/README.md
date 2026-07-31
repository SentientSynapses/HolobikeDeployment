# Geography Integration

This integration connects `geo_kit/HexAtlas`.

HexAtlas remains authoritative for geographic ingestion, SourceAtlas and
MasterAtlas construction, atlas schemas, serving, client caching, and atlas
protocols. HoloBike Deployment selects compatible atlas software and data
revisions, stages only declared outputs, and validates their compatibility with
HolobikeWorlds and the target experience.

The deployment boundary should distinguish:

- executable versions for AtlasServer and AtlasClient;
- atlas root identity, layout version, and content revision;
- whether data is bundled, preloaded, streamed, or fetched after deployment;
- service endpoints and cache policy;
- HolobikeWorlds protocol compatibility; and
- data provenance and storage requirements.

Large atlas data and provider caches do not belong in this Git repository.
Assemblies should reference immutable manifests and verified artifact
locations.
