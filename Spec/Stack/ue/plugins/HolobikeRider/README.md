# HolobikeRider Repository Integration

## Source

- Repository: `ue_kit/HolobikeRider_uplugin`
- Plugin: `HolobikeRider/HolobikeRider.uplugin`
- Integration domain: `ue`
- Source identity: an exact Git commit selected by a revision manifest under `Spec/`

This directory owns plugin integration metadata, not plugin source or a
project-local plugin copy.

## Assembly Contract

The adapter will record rider physics, analytics, identity-bridge, and
Rider-to-World compatibility versions. It will compare the standalone
repository with the copy selected by HolobikeExperience and fail on unexplained
divergence.

## Validation

Acceptance requires compilation in the selected experience, compatibility with
AthleteIdentity and HolobikeWorlds, and product tests covering the declared
rider, identity, telemetry, and environment-input surfaces.
