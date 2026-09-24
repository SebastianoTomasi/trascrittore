# Product

## Boundary

**Owns:** What the product promises and to whom.

**Includes:** Purpose, users, actors and subjects, data classes, observable
capabilities, preconditions and outcomes, non-goals, legal and privacy
obligations, compatibility promises, and external success criteria. These are
representative, not exhaustive.

**Excludes:** Detailed pages and interaction behavior, owned by Frontend;
system decomposition and contracts, owned by Architecture; concrete realization,
owned by Implementation; and cross-cutting control design, owned by Security.

**Scope:** Project-scoped artifacts here hold the Product foundation and
subsequent shared decisions. A new proposal does not replace the accepted
foundation; use the state and change rules in `docs/advisor-docs.md`.
Feature-scoped promises belong in `docs/features/<feature-slug>/product/`; their
progression and questions are in [the feature catalog](advisor-product-feature.md).

## Catalogs

Open the boundary above for placement, then only the catalog required by the
current action:

- [Project-scoped Product catalog](advisor-product-project.md)
- [Feature-scoped Product catalog](advisor-product-feature.md)

The two catalogs are separate context boundaries. Do not load both merely
because they belong to the same authority.
