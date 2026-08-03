# Releases

`Releases/` holds what actually happened: for each release, the **resolved**
form of the manifests that declared it, plus the validation that admitted it.

A release record is a resolved manifest. The declaration under `Manifests/`
says `AthleteIdentity @ main`; the record says `AthleteIdentity @ 5619c33,
clean, sha256:…`. One is intent, reviewed in a pull request; the other is fact,
written by a run and never edited afterward. Correcting a record means
recording a new release, not amending an old one.

## What belongs here

**Release records, and nothing else.** If it is not a release, it is an
artifact: a development assembly produces provenance too, and that provenance
belongs under the untracked `Artifacts/` directory. The rule is deliberately
self-enforcing — it needs no policing, because the directory name answers the
question.

Two exclusions worth stating outright:

- **Logs and binaries never live here.** A record names artifacts by digest and
  says where they were staged; it does not contain them. This directory should
  stay small enough to read.
- **Per-device provisioning records are not committed.** Provisioning produces
  evidence about individual machines — device identities, hardware
  acceptance, health results. That is operational data: numerous, identifying,
  and growing with the fleet. It belongs in an operational store with a
  retention policy, not in version control. What is committed here is the
  release those devices received.

And, as everywhere in this repository: never a password, recovery material,
provider token, signing key, or raw Secret Keeper value.

## Shape

The layout is one directory per release, and the file names keep the declared
and resolved senses apart — `manifest` always means a declared document under
`Manifests/`, so a record does not reuse the word:

```text
Releases/<version>/
  resolved.json     exact revisions and artifact digests
  validation.json   which gates ran and what they returned
```

**What a record must contain is still open**, and deliberately so. It needs to
carry at minimum the source identity and dirty state of every integration, the
artifact inventory with digests, the toolchain versions that produced them
(including the Unreal engine version, which is a release fact rather than a
Stack member), and the policy that admitted it. Fixing the exact fields is the
job of the schema that lands with the first assembly that writes one.
