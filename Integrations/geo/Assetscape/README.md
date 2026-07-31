# Assetscape Repository Integration

## Source

- Repository: `geo_kit/Assetscape`
- Integration domain: `geo`
- Source identity: an exact Git commit selected by an assembly manifest

This directory owns the adapter to Assetscape, not source code, asset kits, or
the generated asset library.

## Assembly Contract

The adapter will record compatible AssetCurator and AssetResolver artifacts,
the selected taxonomy and schema versions, and the immutable AssetLibrary
catalog and vault identities. Large object payloads remain in their declared
artifact or Git LFS storage rather than this deployment repository.

## Validation

Acceptance requires valid catalog and vault manifests, content-addressed object
verification, and compatibility with the selected HolobikeWorlds
`AssetscapeIO` contract. Assetscape supplies the palette; HexAtlas supplies
world facts; neither integration may silently substitute for the other.
