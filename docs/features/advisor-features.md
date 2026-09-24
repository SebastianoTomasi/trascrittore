# Features

This page is the routing scaffold for feature work. It is held once for the
whole project and defines feature identity, structure, completion rules, and
which authority boundary and phase catalog to open. It contains no phase
question catalog: each feature phase has its own file in that authority's
directory, so working on one phase does not load the other phases or the
project-scoped catalog of the same authority.

## Feature identity

A feature is a user-observable capability of the product, declared by writing
its first feature-scoped Product artifact. Its decisions use the relevant
accepted foundation inputs — project-scoped Product and Architecture — under
the [common readiness rule](../advisor-docs.md#usual-phase-order-and-decision-readiness).
The foundation need not be complete before feature work begins or an individual
feature decision is accepted.

A feature has a project-meaningful readable name and a user-confirmed stable
path slug: lowercase ASCII kebab-case matching `[a-z0-9]+(?:-[a-z0-9]+)*`.
The readable name belongs in artifact titles and prose. An existing slug
identifies the existing feature; a different capability needs a different
explicitly agreed slug, never an automatically added numeric suffix.

The first proposed Product artifact under
`docs/features/<feature-slug>/product/` declares the feature and opens its
Product phase. Empty feature folders and later authority folders do not exist
in advance of their first artifacts.

Agree the readable name and confirm the slug with the user before that first
write, unless the user already supplied it. An identity that already exists
resumes its feature instead of declaring a new one. Check the relevant accepted
foundation inputs before writing; when a necessary input is unresolved, explain
the missing decision and offer to settle it first, and if the user proceeds
without it, keep the artifact proposed and name the unresolved assumption.

## What a feature folder holds

```
docs/features/<feature-slug>/
  sources/       informative material shared across authorities, when needed
  product/       artifacts
  frontend/      artifacts
  architecture/  artifacts
  implementation/ artifacts
  security/       artifacts, when needed
  deployment/     artifacts, when needed
  operations/     artifacts, when needed
  development/    artifacts, when needed
  stack/          artifacts, when needed
```

Nothing delivered by the advisor is ever written inside a feature's folder, so
what is there is this project's own work. Each authority folder appears with
its first artifact. Its presence shows documentation in that authority, not
completion of a phase or of any previous phase. Authorities outside the four
feature phases may also hold feature artifacts; they introduce no new phases.

The optional `sources/` folder follows the
[common source rules](../advisor-docs.md#where-material-that-is-not-a-document-sits).
It appears with its first source and adds no authority or phase.

### A phase with no decisions

`<authority>/absent.md` represents a feature phase with no decisions to make.
It has Scope and an explicit dismissal naming each catalog question's slug,
including screening questions, with the reason no decision is needed. A
dismissal relying on existing coverage links its accepted answer and records
the dependency. Every dismissal must be supported and no necessary input may
remain unresolved before acceptance.

A negative applicability answer alone is insufficient, and a dedicated
applicability question is not required. Any substantive answer belongs in a
normal artifact, with links to answers owned elsewhere, and rules out blanket
absence for the phase. The session's acceptance workflow checks these conditions.

## Phase order and reading route

For the phase being worked on, open the small authority boundary and only its
feature catalog. The boundary decides what belongs there and is read, never
inferred from the folder name; the catalog supplies that phase's progression
and complete question list.

1. **feature Product** — `docs/features/<feature-slug>/product/` —
   [Product boundary](../product/advisor-product.md) +
   [Product feature catalog](../product/advisor-product-feature.md)
2. **feature Frontend** — `docs/features/<feature-slug>/frontend/` —
   [Frontend boundary](../frontend/advisor-frontend.md) +
   [Frontend feature catalog](../frontend/advisor-frontend-feature.md)
3. **feature Architecture** — `docs/features/<feature-slug>/architecture/` —
   [Architecture boundary](../architecture/advisor-architecture.md) +
   [Architecture feature catalog](../architecture/advisor-architecture-feature.md)
4. **feature Implementation** — `docs/features/<feature-slug>/implementation/` —
   [Implementation boundary](../implementation/advisor-implementation.md) +
   [Implementation feature catalog](../implementation/advisor-implementation-feature.md)

This is the usual route, not a total prerequisite chain. Coverage and decision
readiness follow [the common rules](../advisor-docs.md#usual-phase-order-and-decision-readiness).
Read another catalog only when the action needs that other scope or phase.

An absent phase folder means no artifact for that phase has been written, not
that every later decision is premature. Accepted coverage remains valid when a
new, unrelated proposal is added, including at foundation scope.

## Completing a phase

The linked feature catalog groups its questions by decision dependency. Those
groups guide one session and are not subphases: they create no folders, markers,
or state of their own.

A phase is complete when accepted, compatible artifacts together address every
question in its catalog and no unresolved input needed by that coverage remains.
Statuses alone do not establish completion; unrelated proposals do not remove
existing accepted coverage.
A question with no substance in the feature is answered by one explicit
dismissal naming its slug. Silence is not an answer.

Some catalogs include **screening questions** owned by Security, Deployment,
Operations, Development, or Stack. They stay beside the phase where they first
become answerable and are marked with their owning authority. Their normal
answer is a dismissal only when existing coverage actually applies. For a
substantive answer, use the owning authority's boundary and demand-driven
questions. Shared rules belong at project scope and feature-only decisions in
that feature's authority folder. Link the authoritative answer and explain the
dependency in the screening artifact. A missing shared document is not evidence
of coverage. A deferred item is for later work, not an unresolved current
prerequisite.

When accepted applicability changes, review `absent.md` as part of propagation:
amend its dismissals or remove it when replaced, so an accepted blanket absence
cannot contradict new accepted decisions.
