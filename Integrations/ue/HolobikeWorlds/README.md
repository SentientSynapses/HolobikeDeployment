# HolobikeWorlds Repository Integration

## Source

- Repository: `ue_kit/HolobikeWorlds_uplugin`
- Plugin: `HolobikeWorlds/HolobikeWorlds.uplugin`
- Integration domain: `ue`
- Source identity: an exact Git commit selected by an assembly manifest

This directory owns plugin integration metadata, not plugin source, atlas
roots, asset libraries, or a project-local plugin copy.

## Assembly Contract

The adapter will record world-composition, HexAtlas protocol, Assetscape
contract, and Rider-to-World compatibility versions. It will compare the
standalone repository with the copy selected by HolobikeExperience and fail on
unexplained divergence.

## Validation

Acceptance requires successful compilation in the selected experience,
compatible HexAtlas and Assetscape inputs, and bounded tests for atlas access,
asset resolution, route/world composition, and rendering appropriate to the
target environment.
