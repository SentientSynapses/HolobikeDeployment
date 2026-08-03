# HolobikeCore Repository Integration

## Source

- Repository: `bike_kit/HolobikeCore`
- Integration domain: `bike`
- Source identity: an exact Git commit selected by an assembly manifest

This directory owns the deployment adapter to HolobikeCore, not device-service
source, firmware source, generated configuration, or physical device state.

## Assembly Contract

The adapter will invoke HolobikeCore-owned build and test commands, collect
declared service and firmware artifacts, and record protocol, configuration,
hardware-revision, and uroborOS requirements. Firmware flashing remains a
production provisioning action rather than an assembly side effect.

## Validation

Acceptance distinguishes simulated services from physical hardware evidence.
It requires compatible HolobikeDevice transport, declared rollback behavior,
service health, firmware identity where applicable, and redacted aggregate
readiness evidence.
