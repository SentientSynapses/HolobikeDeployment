# HexAtlas Repository Integration

## Source

- Repository: `geo_kit/HexAtlas`
- Integration domain: `geo`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns HexAtlas's declarative deployment contract, not adapter
implementation, HexAtlas source, or generated atlas data.

## Assembly Contract

The adapter will invoke HexAtlas-owned build and validation commands and record
the selected AtlasServer and AtlasClient artifacts. AtlasCartographer is not a
deployable: it is the build machine that produces the corpus AtlasServer
streams, and its product is named by the deferred content-selection axis, not
by a profile (D-23). Atlas data inputs must identify their
`AtlasManifest.json`, layout version, content revision, and immutable artifact
location independently of executable revisions.

## Validation

Acceptance requires compatible atlas schemas and protocols, verified software
artifacts, declared data provenance, and compatibility with the selected
HolobikeWorlds integration. Provider caches, SourceAtlas roots, and MasterAtlas
payloads remain outside this Git repository.
