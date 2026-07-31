# Unreal-Engine Integration

This integration connects the Unreal Engine product and its reusable HoloBike
plugins.

Current source checkouts:

| Role | Repository |
|---|---|
| Product project | [`HolobikeExperience/`](HolobikeExperience/README.md) |
| Device transport | [`HolobikeDevice/`](HolobikeDevice/README.md) |
| Rider systems | [`HolobikeRider/`](HolobikeRider/README.md) |
| World composition | [`HolobikeWorlds/`](HolobikeWorlds/README.md) |

The corresponding project locations are:

```text
HolobikeExperience/Unreal/HolobikeExperience.uproject
HolobikeExperience/Unreal/Plugins/HolobikeDevice
HolobikeExperience/Unreal/Plugins/HolobikeRider
HolobikeExperience/Unreal/Plugins/HolobikeWorlds
```

This integration owns revision compatibility, plugin synchronization checks,
Unreal build invocation, packaging, and product-level smoke tests. Until each
plugin contract declares a single synchronization direction, a mismatch
between a standalone plugin checkout and the project copy must fail visibly;
the assembler must not silently choose or overwrite either side.

Generated Unreal directories and packaged builds belong in ignored artifact
locations. The deployment repository must not vendor plugin source or Unreal
generated output.
