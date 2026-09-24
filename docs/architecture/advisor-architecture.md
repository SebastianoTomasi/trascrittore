# Architecture

## Boundary

**Owns:** Implementation-independent system and module contracts.

**Includes:** Components and meaningful submodules, responsibilities,
dependencies, semantic interfaces, conceptual data ownership, invariants,
failure and degradation behavior, trust boundaries, cross-system flows, and a
technology choice when it fixes an architectural constraint or runtime
topology. These are representative, not exhaustive.

**Excludes:** Product behavior and Security policy, whose enforcement may be
placed here but whose rule remains in the owning artifact; technology inventory
and versions, owned by Stack; and internal mechanics that satisfy the unit's
contracts, owned by Implementation. Architecture defines or changes guarantees
offered across the boundary, including guarantees still to be established.
Measurable differences permitted by those contracts do not by themselves make
an internal choice architectural.

**Scope:** Project-scoped artifacts here hold the Architecture foundation and
subsequent shared decisions. A new proposal does not replace the accepted
foundation; use the state and change rules in `docs/advisor-docs.md`. Feature-scoped applications belong in
`docs/features/<feature-slug>/architecture/`; their progression and questions are in
[the feature catalog](advisor-architecture-feature.md).

## Catalogs

Open the boundary above for placement, then only the catalog required by the
current action:

- [Project-scoped Architecture catalog](advisor-architecture-project.md)
- [Feature-scoped Architecture catalog](advisor-architecture-feature.md)

The two catalogs are separate context boundaries. Do not load both merely
because they belong to the same authority.
