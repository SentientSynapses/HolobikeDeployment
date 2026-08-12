# HexAtlas Repository Integration

## Source

- Repository: `geo/HexAtlas`
- Integration domain: `geo`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns HexAtlas's declarative deployment contract, not adapter
implementation, HexAtlas source, or generated atlas data.

## Assembly Contract

The adapter will invoke HexAtlas-owned build and validation commands and record
the selected AtlasCartographer, AtlasServer, and AtlasClient artifacts. Atlas
data inputs must identify their `AtlasManifest.json`, layout version, content
revision, and immutable artifact location independently of executable
revisions.

## Validation

Acceptance requires compatible atlas schemas and protocols, verified software
artifacts, declared data provenance, and compatibility with the selected
HolobikeWorlds integration. Provider caches, SourceAtlas roots, and MasterAtlas
payloads remain outside this Git repository.
