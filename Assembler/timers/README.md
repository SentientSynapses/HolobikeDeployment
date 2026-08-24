# Timers

The declared cadence for the lifecycle's read-only truth: a daily
`resolve` per revision line, so drift anywhere in the stack becomes a
recorded fact within a day instead of a discovery. The Assembler gains no
scheduler — systemd is the scheduler; this directory only declares the
units, on the precedent `.local/environment.json` set: the tracked file
is the template, the per-host install is local.

The unit is a template; the instance name is the revision line
(`holobike-resolve@dev`, `holobike-resolve@ue57`, …), so enrolling a new
line in the cadence is one `enable`, not a new unit.

## Install (per Linux host)

1. Copy both files to `~/.config/systemd/user/`, pointing
   `WorkingDirectory` and `ExecStart` at this repository's checkout on
   that host — the two paths are the only per-host edits.
2. `systemctl --user daemon-reload`
3. `systemctl --user enable --now holobike-resolve@dev.timer` (repeat per
   line under `Revisions/`).

A red service unit means the last run exited nonzero: 1 when the written
record carries problems, 2 when an input was refused. Either way the
record under `Artifacts/records/` says why; the unit is the alarm, never
the evidence.
