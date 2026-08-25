# HolobikeExperience Repository Integration

## Source

- Repository: `ue_kit/HolobikeExperience_uproject`
- Project: `HolobikeExperience/HolobikeExperience.uproject`
- Integration domain: `ue`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns Unreal project assembly metadata, not project source,
content, generated Unreal state, or packaged builds.

## Assembly Contract

The adapter will select an Unreal Engine/toolchain profile, verify the required
plugin revisions, invoke project-owned build and packaging surfaces, and record
the packaged application, build configuration, plugin inventory, and artifact
digests.

## Validation

Acceptance requires a clean source identity, no stale generated output as an
input, successful project compilation and packaging, declared map/content
selection, and product-level startup and rendering evidence appropriate to the
target environment.
