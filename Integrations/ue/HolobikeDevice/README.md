# HolobikeDevice Repository Integration

## Source

- Repository: `ue_kit/HolobikeDevice_uplugin`
- Plugin: `HolobikeDevice/HolobikeDevice.uplugin`
- Integration domain: `ue`
- Source identity: an exact Git commit selected by an assembly manifest

This directory owns plugin integration metadata, not plugin source or a
project-local plugin copy.

## Assembly Contract

The adapter will record the standalone plugin revision, descriptor identity,
device-protocol compatibility, and HolobikeCore transport requirements. It
will compare the standalone repository with the copy selected by
HolobikeExperience and fail on unexplained divergence.

## Validation

Acceptance requires successful compilation in the selected experience,
compatible Syslink and typed device-message contracts, declared project
configuration, and either simulated or physical service evidence labeled by
capability.
