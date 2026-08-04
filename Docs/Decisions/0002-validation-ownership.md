# 0002 — Validation ownership: repositories prove themselves, deployment proves the composition

Status: accepted, 2026-08-04.

## Context

The stack reached this point with sibling `*-Lab` repositories —
HolobikeCore-Lab, uroborOS-Lab, AthleteIdentity-Lab, HexAtlas-Lab, and
others — proving individual services in isolation. They were the right
scaffolding: young repositories lacked internal gates, and the Labs supplied
executable contracts, spoofs, and VM harnesses without disturbing the
sources.

They are not the long-term owners of validation. The operator's direction is
explicit: the Labs are disposable, and structural dependence on them would
make scaffolding load-bearing. The ecosystem's own maturity gradient already
shows the durable pattern — AthleteIdentity proves itself with co-located
in-repo tests, in-repo conformance fixtures, and an in-repo LocalMock
provider; the Unreal plugins carry their own verify commandlets. The
repositories that still need external Labs are the youngest, not the model.
Recent host-safety incidents also originated in privileged Lab fixtures —
which is what disposable scaffolding running with production privileges
looks like.

## Decision

Validation is owned in three tiers, and the tiers are the separation of
roles:

| Tier | Question | Owner |
|---|---|---|
| Isolation | does one repository honor its own contracts? | that repository, in-repo — tests, fixtures, simulators of its own hardware |
| Composition | do the repositories work as one product? | this repository — emulate profiles, `Policy/` gates, `Conformance/` |
| Acceptance | does the real device meet the release? | `Provisioning/` gates |

Rules:

- Deployment consumes only public, documented entry points, declared per
  repository in its `Stack/` leaf. It never reaches into a repository's
  private test scaffolding — and never into a Lab.
- Simulators of a repository's own hardware ship inside that repository as
  first-class development capabilities — the LocalMock pattern. Simulated
  drivetrain and handlebar ports belong in HolobikeCore the way LocalMock
  belongs in AthleteIdentity.
- Needing a capability that only a Lab holds today is a promotion signal:
  move it into the repository if it proves that repository; build it in the
  Assembler if it is composition machinery. Either way the Lab does not
  become a dependency.
- Copying an idiom from a Lab — the run-record shape, the Python package
  layout — is not a dependency; a copied pattern becomes this repository's
  own.

## Consequences

- `emulate` names no Lab. Its inputs are Stack-declared entry points and
  profile-declared topologies.
- `integration.json` carries both faces per repository: how to prove it in
  isolation (its own gate command) and what it exposes for composition
  (services, simulators, health probes).
- HolobikeCore-Lab's SimulationRig kinetics fakes are migration candidates
  into HolobikeCore as development ports as the per-service Host refactor
  lands.
- The Labs can be archived one by one as their duties are absorbed, with no
  change required here.
