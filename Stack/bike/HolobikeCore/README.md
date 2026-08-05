# HolobikeCore Repository Integration

## Source

- Repository: `bike_kit/HolobikeCore`
- Integration domain: `bike`
- Source identity: an exact Git commit selected by a revision manifest under `Revisions/`

This directory owns HolobikeCore's declarative deployment contract, not adapter
implementation, device-service source, firmware source, generated
configuration, or physical device state.

## Assembly Contract

The leaf invokes HolobikeCore's repository-owned `holobikecore.sh prove` and
`holobikecore.sh package` surfaces and stages the declared Linux rootfs archive.
The Assembler owns only invocation, source-state checks, staging, and digests;
package contents and behavior remain HolobikeCore's responsibility. Firmware
flashing remains a production provisioning action rather than an assembly
side effect.

## Validation

Acceptance distinguishes simulated services from physical hardware evidence.
It requires compatible HolobikeDevice transport, declared rollback behavior,
service health, firmware identity where applicable, and redacted aggregate
readiness evidence. This leaf does not yet declare a serve/probe pair, so it is
buildable but not a runnable member of host-service emulation.
