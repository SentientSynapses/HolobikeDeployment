# uroborOS Repository Integration

## Source

- Repository: `os_kit/uroborOS`
- Integration domain: `os`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns uroborOS's declarative deployment contract. It is not an
adapter implementation, checkout, submodule, or copy of the operating-system
source.

## Assembly Contract

The current leaf exposes uroborOS's repository-owned static proof surface. A
later assembly contract will consume a resolved mode and release descriptor
and stage declared images, package closures, runtime payload inventories, and
release metadata. It must preserve the distinction between development
scaffolds and production-admissible modes.

## Validation

Acceptance requires a clean selected revision, deterministic mode resolution,
matching artifact digests, and the validation evidence uroborOS publishes for
the selected release — evidence owned by the repository itself, wherever it
is produced today. HoloBike Deployment must not bypass uroborOS image,
installer, graphics, boot, account, or Secret Keeper policy.
