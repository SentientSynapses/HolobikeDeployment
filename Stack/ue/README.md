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
| Product project | [`HolobikeExperience/`](project/HolobikeExperience/README.md) |
| Device transport | [`HolobikeDevice/`](plugins/HolobikeDevice/README.md) |
| Rider systems | [`HolobikeRider/`](plugins/HolobikeRider/README.md) |
| World composition | [`HolobikeWorlds/`](plugins/HolobikeWorlds/README.md) |
| Stereoscopic display | [`HoloviewDisplay/`](plugins/HoloviewDisplay/README.md) |

The corresponding project locations are:

```text
HolobikeExperience/Unreal/HolobikeExperience.uproject
HolobikeExperience/Unreal/Plugins/HolobikeDevice
HolobikeExperience/Unreal/Plugins/HolobikeRider
HolobikeExperience/Unreal/Plugins/HolobikeWorlds
HolobikeExperience/Unreal/Plugins/HoloviewDisplay
```

This integration owns revision compatibility, plugin synchronization checks,
Unreal build invocation, packaging, and product-level smoke tests. Until each
plugin contract declares a single synchronization direction, a mismatch
between a standalone plugin checkout and the project copy must fail visibly;
the assembler must not silently choose or overwrite either side.

Generated Unreal directories and packaged builds belong in ignored artifact
locations. The deployment repository must not vendor plugin source or Unreal
generated output.
