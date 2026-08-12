# HoloviewDisplay Repository Integration

## Source

- Repository: `ue_kit/HoloviewDisplay_uplugin`
- Plugin: `HoloviewDisplay/HoloviewDisplay.uplugin`
- Integration domain: `ue`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns plugin integration metadata, not plugin source or a
project-local plugin copy.

HoloviewDisplay is the product-owned autostereoscopic display integration for
the HoloBike panel (a Dimenco/Leia SR unit). It replaces the retired
`Leia_5.3` plugin, keeping the installed Simulated Reality Platform as the
first provider behind product-owned seams rather than a dependency of the
product surface. The plugin supports UE 5.3 and UE 5.7 from one codebase — a
`Rendering/EngineVersions/` seam compiles one stereo-output file per engine
version — so it can move HolobikeExperience across engine versions without a
fork.

## Assembly Contract

The adapter will record the standalone plugin revision, descriptor identity,
supported engine versions, and Simulated Reality Platform provider
requirements. It will compare the standalone repository with the copy selected
by HolobikeExperience and fail on unexplained divergence: the plugin mounts
into the experience through one canonical link, never a parallel copy.

The Simulated Reality SDK is a third-party dependency located by path, not
vendored here; on hosts without it the plugin selects its in-product
`NullDisplayPlatform` fallback (the sanctioned seam-implementation double,
`Docs/Decisions/0003`), which also covers the non-Windows role.

## Validation

Acceptance requires successful compilation in the selected experience on the
declared engine version, a monoscopic Null-provider path that runs without the
SR Platform, and — where an SR panel is present — stereo startup and rendering
evidence labeled by capability. The plugin proves its own projection,
tracking, and adapter behaviour in-repo through its published seams
(`Public/` APIs and console control surfaces), per `Docs/Decisions/0002`; the
transitional `HoloviewDisplay-Lab` scaffolding is not load-bearing and its
suites promote toward those seams.
