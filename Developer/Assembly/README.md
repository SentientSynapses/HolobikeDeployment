# Assembly

Assembly turns a declared set of facet revisions into an inspectable HoloBike
integration bundle.

The name is intentional: this domain assembles independently owned software
artifacts. It does not compile assembly language and should not absorb the
build logic already owned by each facet. A future executable can be named
`holobike-assemble`; `assembler` is suitable for that implementation role, but
`Assembly/` is the clearer architectural domain.

## Intended Contract

An assembly consumes:

- a product or development profile;
- an exact source revision for every required facet;
- facet-specific build options;
- compatibility constraints; and
- an explicit output location.

It produces:

- staged artifacts without modifying source working trees;
- a machine-readable inventory of source revisions and artifact digests;
- build and integration results;
- a compatibility report; and
- enough provenance to reproduce or reject the assembly.

## Boundary

Assembly may invoke a facet's documented build, package, export, and test
commands. It must not copy their internal build logic, infer success from file
existence alone, or treat mutable branch names as production release
identities.

The first implementation should begin with a versioned manifest schema and a
read-only preflight command. Artifact staging should follow only after source
identity and compatibility checks are deterministic.
