# Revisions

Revision manifests: the declared composition of each line, one file per
line, named for it. A development line may select by branch — the manifest
states where development *rides*, and editing it is how the intent changes.
A release line resolves to exact commits: a mutable branch name is never a
release identity.

The `resolve` verb pins a manifest against the workstation's checkouts and
writes what actually is — commits, dirty state, mismatches — as a record
under the untracked `Artifacts/records/`. A mismatch between declaration
and checkout is a recorded fact, not a resolve failure; refusing to promote
a record with problems is admission's job.
