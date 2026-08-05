# Releases

`Releases/` holds what actually happened: for each release, the **resolved**
form of the declarations that composed it, plus the validation that admitted
it.

A release record is the declarations, resolved. The revision manifest under
`Revisions/` says `AthleteIdentity @ main`; the record says `AthleteIdentity
@ 5619c33, clean, sha256:…`. One is intent, reviewed in a pull request; the other is fact,
written by a run and never edited afterward. Correcting a record means
recording a new release, not amending an old one.

## What belongs here

**Release records, and nothing else.** If it is not a release, it is an
artifact: a development assembly produces provenance too, and that provenance
belongs under the untracked `Artifacts/` directory. The rule is deliberately
self-enforcing — it needs no policing, because the directory name answers the
question.

Two exclusions worth stating outright:

- **Logs and binaries never live here.** A record names artifacts by digest
  and says where they were staged; it does not contain them. This directory
  should stay small enough to read.
- **Per-device provisioning records are not committed.** Provisioning
  produces evidence about individual machines — device identities, hardware
  acceptance, health results. That is operational data: numerous,
  identifying, and growing with the fleet. It belongs in an operational store
  with a retention policy, not in version control. What is committed here is
  the release those devices received.

And, as everywhere in this repository: never a password, recovery material,
provider token, signing key, or raw Secret Keeper value.

## Shape

One directory per release, written by `admit` and by nothing else. A
release is self-contained — it copies the chain it was admitted from in,
because `Artifacts/` is untracked and ephemeral, and an attestation that
points at swept evidence attests nothing:

```text
Releases/<version>/
  release.json      the admission record: version, the chain, and what was
                    attested (gates, builds, selections, emulation)
  resolution.json   the resolved revisions and gate verdicts, copied in
  assembly.json     the built artifacts with digests, copied in
  emulation.json    present only when the release was admitted emulated
```

`release.json` binds each original run-record name to its SHA-256 digest;
assembly records bind their resolution, emulation records bind their assembly,
and admission re-hashes the complete chain and every staged artifact before
publication. The copied records therefore remain independently verifiable
after `Artifacts/` is swept.

Admission promotes only a clean chain: every gate passed, every selection
resolved, every profile member built and staged, and any incorporated
emulation healthy. A chain that fails any of these is refused — `Releases/`
is untouched and the reasons are reported. Records under `Artifacts/` state
facts; admission is the one step that decides, and the one writer here.

A version is immutable: `admit` prepares the complete release beside its
destination, publishes it atomically, and refuses a version whose directory
already exists. Correcting a release means admitting a new version, never
editing one. The record schema is `Schemas/record.schema.json` (the `release`
kind); toolchain versions such as Unreal Engine join the assembly record when
that integration begins staging product artifacts.
