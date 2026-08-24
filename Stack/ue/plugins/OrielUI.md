# OrielUI Repository Integration

## Source

- Repository: `ue_kit/OrielUI_uplugin`
- Plugin: `OrielUI/OrielUI.uplugin`
- Integration domain: `ue`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns plugin integration metadata, not plugin source or a
project-local plugin copy.

OrielUI is the spatial UI framework: a core composer module
(`OrielComposer`) and a reusable component module (`OrielComponentLibrary`),
for assembling volumetric UI compositions. It is a framework rather than a
design language — the distinction is the repository's own, and it is why
this leaf declares no opinions about what a composition should look like.

## Assembly Contract

The deployable is `OrielUI`, and its destination is `HolobikeExperience`: UBT
compiles the plugin into the packaged product, so it produces no artifact of
its own and that is the honest statement rather than an omission. The adapter
will record composer and component-library compatibility versions against the
experience that consumes them.

## Validation

Acceptance requires compilation in the selected experience and product tests
covering the declared composer and component surfaces. Until D-08's conversion
lands, the `orielui-dual-copy` parity gate compares the standalone repository
with the copy HolobikeExperience carries and fails on unexplained divergence.
