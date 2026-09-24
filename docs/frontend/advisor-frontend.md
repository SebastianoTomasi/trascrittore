# Frontend

## Boundary

**Owns:** Approved client-visible behavior and interaction contracts.

**Includes:** Page and screen descriptions, composition of visible information
and controls, entry points, navigation, journeys, interaction steps, loading,
empty, partial, success and failure states, client-side input and feedback, and
accessibility behavior. These are representative, not exhaustive.

**Excludes:** The product outcome and actors, owned by Product; service and
cross-component contracts, owned by Architecture; internal client and server
design, including state representation, history, and algorithms, owned by
Implementation; and technology inventory and versions, owned by Stack.

**Scope:** Project-scoped artifacts here define the default surface and shared
interaction rules inherited by later features; they are demand-driven and not
part of the foundation. Feature-scoped surfaces belong in
`docs/features/<feature-slug>/frontend/`; their progression and questions are in
[the feature catalog](advisor-frontend-feature.md). A direct
project-wide Frontend decision may start an artifact here without a screening
question.

## Catalogs

Open the boundary above for placement, then only the catalog required by the
current action:

- [Project-scoped Frontend catalog](advisor-frontend-project.md)
- [Feature-scoped Frontend catalog](advisor-frontend-feature.md)

The two catalogs are separate context boundaries. Do not load both merely
because they belong to the same authority.
