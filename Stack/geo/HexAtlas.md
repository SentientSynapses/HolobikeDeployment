# HexAtlas Repository Integration

## Source

- Repository: `geo_kit/HexAtlas`
- Integration domain: `geo`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns HexAtlas's declarative deployment contract, not adapter
implementation, HexAtlas source, or generated atlas data.

## Assembly Contract

`AtlasClient` reaches the device; `AtlasServer` reaches the estate.
AtlasCartographer is not a deployable: it is the build machine that produces
the corpus AtlasServer streams, and its product is named by the deferred
content-selection axis, not by a profile (D-23).

`AtlasServer` declares the build HexAtlas's own README documents —
`./AtlasServer/atlasserver.sh build hexatlasserver` — and its artifact is the
`HexAtlasServer` executable in the Ninja build directory that script selects
when `ninja` is on the PATH. It builds to bytes here and declares no way to
be placed: no container, no unit, and no host named anywhere in HexAtlas.
`provision atlas` refuses on exactly that. It also declares no `serve` or
`probe`, deliberately: serving wants an atlas root, and the honest corpus for
that is the deferred content axis rather than a local directory of provider
data. Atlas data inputs must identify their
`AtlasManifest.json`, layout version, content revision, and immutable artifact
location independently of executable revisions.

## Validation

Acceptance requires compatible atlas schemas and protocols, verified software
artifacts, declared data provenance, and compatibility with the selected
HolobikeWorlds integration. Provider caches, SourceAtlas roots, and MasterAtlas
payloads remain outside this Git repository.
