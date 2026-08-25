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
- `server` — the deployables that reach the estate. It splits into `identity`,
  `atlas`, and `drais` when a second of them has bytes to deploy; until then it
  is one document, not a claim that they share a host.
