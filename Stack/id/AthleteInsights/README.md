# AthleteInsights

The device service that takes durable custody of completed sessions and serves
an athlete's history back. It is the second half of the identity pair: rides
arrive carrying the qualified `(issuer, subject_id)` identity that
[AthleteIdentity](../AthleteIdentity/README.md) resolved, and this service is
what a device holds the only copy of a ride *until*.

## Why it is enrolled

It was not, for a while, and that was the gap: `InsightsIO` — the Unreal module
that hands rides across — was gated, parity-checked and pinned, while the
service on the other end of its socket was none of those things. A composition
that can pin one side of a wire and not the other cannot say what it deployed.

## No probe

Unlike AthleteIdentity, this repository builds no CLI, so there is no probe
entry point to declare. Recorded as an absence rather than improvised: the
service's own readiness is its endpoint appearing, and inventing a probe here
would mean inventing a client to run it.

## Serve

`serve` takes an identity endpoint as well as its own, because a ride cannot be
attributed until identity answers who recorded it. Composition therefore orders
identity ahead of insights; the declaration says so by naming the socket it
expects to find.
