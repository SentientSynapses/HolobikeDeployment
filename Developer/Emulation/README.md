# Emulation

Emulation validates an assembled HoloBike stack without requiring a complete
production bike.

Expected workflows include:

- booting uroborOS images in a VM;
- simulating drivetrain and handlebar telemetry;
- exercising HolobikeDevice transport against simulated bike services;
- running HexAtlas fixtures or bounded local atlas services;
- using AthleteIdentity's development provider;
- running drAIs with explicit development model and tool providers; and
- launching HolobikeExperience with a declared plugin and data set.

This domain orchestrates existing emulators, Labs, fixtures, and public control
surfaces. Test harness logic should remain with the repository that owns the
underlying behavior unless the behavior exists only at the cross-facet product
boundary.

An emulation run must record its assembly identity, configuration, results,
logs, and artifact locations. It must label simulated capabilities clearly and
must not be accepted as evidence for hardware behavior such as production
NVIDIA, display, drivetrain, or handlebar performance.
