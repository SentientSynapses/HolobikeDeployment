# Operating-System Integration

This integration connects `os_kit/uroborOS`.

Repository adapter:

- [`uroborOS/`](uroborOS/README.md)

uroborOS remains authoritative for operating modes, system images, boot and
encrypted-root policy, the shell, graphics integration, system services, and
OS-level installation — and for proving all of it: its validation surfaces
are repository-owned entry points, not Lab property.
HoloBike Deployment selects a compatible uroborOS revision and mode, invokes
its published build and validation surfaces, and consumes their versioned
artifacts and evidence.

The deployment boundary should eventually record:

- selected uroborOS revision and resolved mode;
- base-image snapshot and exact package closure;
- runtime payload and service contract versions;
- image, boot, and provisioning artifact digests;
- required hardware and firmware capabilities; and
- the validation evidence uroborOS publishes for the selected release.

This integration must not bypass uroborOS release gates or reproduce installer,
Secret Keeper, graphics, boot, or account policy in the aggregator.
