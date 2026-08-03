# Bike-Runtime Integration

This integration connects `bike_kit/HolobikeCore`.

Repository adapter:

- [`HolobikeCore/`](HolobikeCore/README.md)

HolobikeCore remains authoritative for on-device services, firmware,
hardware-facing configuration, device protocols, and aggregate bike health.
HoloBike Deployment selects compatible service and firmware artifacts,
coordinates their installation with uroborOS, and validates the public
transport consumed by HolobikeDevice.

The deployment boundary should eventually record:

- service and firmware revisions;
- supported hardware revisions;
- protocol and configuration schema versions;
- uroborOS service/package requirements;
- firmware flashing and rollback policy;
- simulated versus physical-device test results; and
- aggregate readiness and health evidence.

Emulation may substitute deterministic drivetrain and handlebar simulators.
Those results must remain distinct from physical firmware, latency, safety, and
hardware acceptance evidence.
