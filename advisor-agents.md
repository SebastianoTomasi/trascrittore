# Delivery process advisor

This project follows the delivery process advisor: a project-local process for
turning an idea into software that is clear enough to build. Its normative
documentation lives under `docs/`. Catalogs define the decisions to address,
their dependencies, and the usual order. Skills use them to conduct the work
and declare when they apply. This file provides shared reading guidance and
navigation.

## Using project documentation

The code is the source of truth for what is implemented. Existing behavior may
be undocumented; that alone creates no requirement to change it or document it.
For work specified in documentation but not yet implemented, read and follow
the relevant accepted decisions. Use the reading guidance below to find them.

When code and documentation contradict each other, surface the discrepancy and
preserve the implementation while clarifying the intended change with the user.
The discrepancy alone establishes neither a bug nor outdated documentation.

Accepted artifacts record settled decisions; they do not prove that those
decisions are implemented. Proposals and artifacts needing review do not
establish accepted inputs; sources inform decisions without establishing rules.
An artifact records decisions established with the user, including choices made
within their explicit delegation. Choices made without that agreement or
delegation remain proposed. The user may change direction; the advisor's advice
creates no additional permission step or deviation record. The full document,
status, dependency, and acceptance rules are in
[`docs/advisor-docs.md`](docs/advisor-docs.md).

## Where things are

- [`docs/advisor-docs.md`](docs/advisor-docs.md) defines common documentation
  rules and routes subjects to their owning authority.
- `docs/<authority>/advisor-<authority>.md` defines that authority's boundary
  and links to its catalogs. Project artifacts live beside it; feature artifacts
  live under `docs/features/<feature-slug>/<authority>/`.
- Project and feature catalogs for Product, Frontend, Architecture, and
  Implementation are separate `advisor-<authority>-project.md` and
  `advisor-<authority>-feature.md` files. Other authorities keep one demand-driven
  catalog in their boundary file.
- [`docs/features/advisor-features.md`](docs/features/advisor-features.md)
  defines feature structure and routes each phase to its boundary and catalog.
- `CONTEXT.md` holds the project's vocabulary; `docs/adr/` holds decision
  records explaining important choices. Neither is an artifact or phase.
- `docs/deferred/` holds future work. `docs/handoffs/` holds temporary
  conversation bridges; read those only when the user identifies one.

## Reading guidance

Open a known relevant artifact directly. When locating or placing documentation,
use `docs/advisor-docs.md` to select the owning authority, then read its boundary.
Consider both shared project rules and relevant feature artifacts. Select
artifacts by filenames and opening passages containing the title, status, and
Scope; read bodies whose scope can affect the work. Do not load the documentation
tree as general context.

Follow relevant Dependencies, Review blocks, and linked decision passages.
Treat filenames and markers as routing information, not evidence of what a
document establishes. Read a catalog when the action needs its decisions or
coverage questions, selecting only the relevant scope and phase.

Look for sources in `docs/sources/` and `docs/<authority>/sources/`. For feature
work, also inspect `docs/features/<feature-slug>/sources/` and
`docs/features/<feature-slug>/<authority>/sources/`. Inspect filenames and
opening lines to choose relevant full reads. A source has no required format.

Recognize advisor scaffolds and catalogs by their fixed names. Unmarked project
documents may be relevant context; reading them does not adopt them as advisor
artifacts.

Cite the documents and passages supporting conclusions drawn from documentation.
Disclose unread material that could affect those conclusions.

Explain the project's documentation conventions from its local advisor files.
For the advisor's broader design and rationale, direct the user to its own
repository: <https://github.com/SebastianoTomasi/delivery-process-advisor>.
