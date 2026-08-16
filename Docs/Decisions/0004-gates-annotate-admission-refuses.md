# 0004 — Gates annotate; only admission refuses

Status: accepted, 2026-08-16.

## Context

The parity gates (M4) and admission (M8) landed with their division of
authority decided but recorded only in commit messages. Since then the
gate vocabulary has grown a third verdict, and the reasoning behind the
division keeps being re-derived, which is what an ADR exists to stop.

The stack's recurring failure mode is dual-copy drift: a plugin living in
its own repository and again inside HolobikeExperience's mount, the two
diverging silently. The gates were built to turn that silence into a
recorded fact. Two temptations were rejected on the way: letting the gate
refuse (which couples measurement to enforcement and teaches people to
stop measuring), and letting an unevaluable gate stay quiet (which reads
as coverage that does not exist).

## Decision

**Gates compute facts; records carry them; admission alone refuses.**

- A gate evaluation is pure: no side effects, no exit authority. Its
  verdict is a fact block riding the resolution record. `resolve` writes
  the record regardless of verdicts and signals problems in its exit
  code; it never withholds the record.
- `admit` is the only refusing step and the only writer of the tracked
  `Releases/` tier. A refused admission records its decision to
  `Artifacts/` and writes nothing tracked.
- **A skip is a problem.** Where a gate cannot be evaluated — a missing
  checkout, a missing subtree — the verdict is skipped-with-reason, and
  every skip lands in the record's problems. A gate that silently cannot
  run is indistinguishable from coverage; the problem line is what keeps
  it distinguishable.
- **`linked` is parity by construction.** When both sites resolve to the
  same real path there is one tree, not two equal trees. A file-by-file
  comparison would report a perfect pass while measuring nothing, so the
  verdict says which situation holds. `linked` names its `target`
  (required — sameness must say the same *what*), admits exactly as a
  pass does, and adds no problem. A site that is a link to somewhere
  *else* resolves to a different real path and is compared like any
  copy: "it's a link" is not the fact; "both sites are one tree" is.

Links are also the preferred end state for plugin mounts (PLAN, M9–M10):
converting a mount from a copy to a canonical link moves its gate from
measured parity to parity by construction, and the drift class it guarded
against stops existing rather than being reconciled forever.

## Consequences

- Every resolution carries every gate's verdict — pass, fail, skipped,
  or linked — so gate history is readable off the record stream without
  re-running anything.
- A gate can never report a vacuous pass over a linked mount, and the
  suite holds that with a link-to-elsewhere counterexample.
- Enforcement points stay countable: exactly one verb refuses. Anything
  that wants to block earlier than admission is asking to become a gate,
  and gets to annotate instead.
- Mount paths that are links must be gitignored in the mounting
  repository; a committed link degenerates into a committed copy on the
  next careless add, silently reopening the drift class.
