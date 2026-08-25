# Unreal-Engine Integration

This integration connects the Unreal Engine product and its reusable HoloBike
plugins.

This domain carries a `<kind>` level because its artifacts deploy
differently: `plugins/` are libraries synchronized against a project, and
`project/` is the packaged product.

The engine itself is not here. Unreal is third-party software, not a HoloBike
integration: environment checking locates and validates it from the path
declared in `.local/environment.json`, and a release records the engine version
that produced the build.

Current source checkouts:

| Role | Repository |
|---|---|
| Product project | [`HolobikeExperience_uproject/`](project/HolobikeExperience.md) |
| Device transport | [`HolobikeDevice_uplugin/`](plugins/HolobikeDevice.md) |
| Rider systems | [`HolobikeRider_uplugin/`](plugins/HolobikeRider.md) |
| World composition | [`HolobikeWorlds_uplugin/`](plugins/HolobikeWorlds.md) |
| Stereoscopic display | [`HoloviewDisplay_uplugin/`](plugins/HoloviewDisplay.md) |
| Spatial UI | [`OrielUI_uplugin/`](plugins/OrielUI.md) |

Each repository holds its Unreal descriptor under a directory of the
descriptor's own name, and the project reaches the plugins as sibling
checkouts through `AdditionalPluginDirectories` (D-08) rather than through
copies under `Plugins/`:

```text
HolobikeExperience_uproject/HolobikeExperience/HolobikeExperience.uproject
HolobikeDevice_uplugin/HolobikeDevice/HolobikeDevice.uplugin
HolobikeRider_uplugin/HolobikeRider/HolobikeRider.uplugin
HolobikeWorlds_uplugin/HolobikeWorlds/HolobikeWorlds.uplugin
HoloviewDisplay_uplugin/HoloviewDisplay/HoloviewDisplay.uplugin
OrielUI_uplugin/OrielUI/OrielUI.uplugin
```

This integration owns revision compatibility, plugin synchronization checks,
Unreal build invocation, packaging, and product-level smoke tests. Until each
plugin contract declares a single synchronization direction, a mismatch
between a standalone plugin checkout and the project copy must fail visibly;
the assembler must not silently choose or overwrite either side.

Generated Unreal directories and packaged builds belong in ignored artifact
locations. The deployment repository must not vendor plugin source or Unreal
generated output.
