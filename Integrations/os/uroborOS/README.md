# uroborOS Repository Integration

## Source

- Repository: `os_kit/uroborOS`
- Integration domain: `os`
- Source identity: an exact Git commit selected by an assembly manifest

This directory owns deployment metadata and adapter logic for uroborOS. It is
not a checkout, submodule, or copy of the operating-system source.

## Assembly Contract

The adapter will consume a resolved uroborOS mode and release descriptor, call
uroborOS-owned build surfaces, and collect declared images, package closures,
runtime payload inventories, and release metadata. It must preserve the
distinction between development scaffolds and production-admissible modes.

## Validation

Acceptance requires a clean selected revision, deterministic mode resolution,
matching artifact digests, and the canonical uroborOS-Lab evidence required by
the selected release. HoloBike Deployment must not bypass uroborOS image,
installer, graphics, boot, account, or Secret Keeper policy.
