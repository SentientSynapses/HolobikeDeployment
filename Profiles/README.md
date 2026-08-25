# Profiles

A profile is a named composition: which deployables a build carries and where
they are going. `holobike env <profile>` and `holobike build <profile>` take
its name; the document is `Profiles/<name>.json`, validated against
`Tool/src/holobike/schemas/profiles.schema.json`.

A profile groups what is deployed together — by one operation, to one place
(D-23). Posture is never a profile's business: development and release runs of
the same composition use the same document, and the verb chooses (D-16).
`destination` is one of the two terminals, `device` or `server`, and every
selected deployable's own destination must resolve to it (D-19) — a
cross-document fact that `stack.select` proves against the whole Stack.

`topology` says how `emulate` runs a selected deployable. `host` is the only
mode, and it is deliberately limited to disposable, unprivileged user-space
processes run from staged bundle artifacts with isolated state. OS, graphical,
privileged, and hardware-facing members wait for a VM executor and must not be
described as `host` in the interim. A non-secret environment overlay may
accompany each entry.

Today:

- `device` — everything that reaches the bike, the five plugins compiled into
  `HolobikeExperience` included.
- `identity` — `IdentityServer` and `InsightsServer`: one runtime, one
  cloud, one Terraform module.
- `atlas` — `AtlasServer`, the corpus streamer.
- `drais` — `DraisServer`, the intelligence gateway.

The three server profiles share a destination and nothing else — not a host,
not a runtime, not a cadence — which is why they are three documents.
