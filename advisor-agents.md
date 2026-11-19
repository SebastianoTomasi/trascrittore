# Delivery process advisor

This project follows the delivery process advisor: a project-local process for
turning an idea into software that is clear enough to build. Its normative
documentation lives under `docs/`. Catalogs define the decisions to address,
their dependencies, and the usual order. This file provides shared reading
guidance and navigation, says what a decision rests on, and says how sessions,
tickets, coding standards, handoffs, and deferred work fit the process.

## Using project documentation

The code is the source of truth for what is implemented. Existing behavior may
be undocumented; that alone creates no requirement to change it or document it.
For work specified in documentation but not yet implemented, the relevant
accepted decisions are part of its spec: read and follow them when planning,
building, or reviewing it. Use the reading guidance below to find them.

Before explaining, planning, or changing behavior the project may already
have, read the code first, then the documentation, and answer from both,
because documentation read alone can describe a behavior the code has since
replaced. Where the two agree, explain the implementation through the
documents. Where they contradict each other, say so, keep the implementation,
and propose bringing the documentation in line with the code; the
contradiction alone changes no document and proves no bug, and the user may
instead confirm the documentation as the intended direction. A ticket or
request that contradicts an accepted decision is likewise raised before acting
on it.

Accepted artifacts record settled decisions; they do not prove that those
decisions are implemented. Proposals and artifacts needing review do not
establish accepted inputs; sources inform decisions without establishing rules.
A passage read without its routing envelope is not yet an input, since a slice
of a proposal reads like a slice of an accepted rule: before planning, building,
reviewing, or telling the user what the project decided on it, read the
document's title, status line, and Scope, and its Dependencies when the passage
is a decision that relies on others.
An artifact records decisions established with the user, including choices made
within their explicit delegation. Choices made without that agreement or
delegation remain proposed. The user may change direction; the advisor's advice
creates no additional permission step or deviation record. The full document,
status, dependency, and acceptance rules are in
[`docs/advisor-docs.md`](docs/advisor-docs.md).

## Decisions rest on data

A decision that turns on a fact, such as a number, a limit, a cost, or how an
external system or library behaves, rests on that fact, not on a guess. A
choice that depends only on what the user wants needs no research. Before
recommending an answer, look in the code, the documents, and the sources for
the facts that could change it. When one is missing or has no source behind
it, research it thoroughly in primary sources first, in a subagent where the
host offers one, to keep this session's context for the decision. Do so even
when the fact seems too specific to this project to be found, because that is
known only after looking, and stop when further searching is unlikely to
change the answer. Save the findings, with where the research looked, as a
[source](docs/advisor-docs.md#where-material-that-is-not-a-document-sits) and
cite it from the artifact that records the decision. A fact the research does
not find, or derives only from similar cases, stays uncertain: the artifact
states it as an estimate or an assumption, never as a fact, and says what
would verify it.

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
- `GLOSSARY.md` holds the project's vocabulary; `docs/adr/` holds decision
  records explaining important choices. Neither is an artifact or phase.

## Sessions, tickets, and handoffs

- **Grill-with-docs sessions**, started by `/grill-with-docs` or by a request to
  write, fill in, or accept a document under `docs/`, record decisions in the
  advisor's artifacts as they settle. Before the first question, read
  `docs/advisor-docs.md` and follow its
  [session procedure](docs/advisor-docs.md#grill-with-docs-sessions).
- **Ticket breakdowns and implementation.** Before drafting tickets or building,
  put to the user, each with a recommended answer, the decisions the work
  depends on that neither an accepted artifact, its ticket, nor the
  conversation settles. The pull request that delivers a ticket closes it,
  through a closing keyword in its description. When a plan or breakdown is
  replaced, close its remaining tickets as not planned, each with a link to
  what replaces it. A ticket left open after its work is later taken for work
  still to do.
- **Coding standards.** Where the project has
  `docs/development/CODING_STANDARDS.md`, it states what is particular to this
  repository's code, and a change is written and reviewed against it. When a
  session settles a convention for the code, or a review raises a point an
  earlier review already raised and that document does not state, propose
  recording it there, as
  [its description](docs/development/advisor-development.md#the-coding-standards-document)
  says; a project without the document starts it then.
- **Opening an issue.** Before opening any issue, search the open and closed
  ones for its subject. Where one exists, comment on it, reopening it if
  closed, in place of opening another.
- **Delegation.** A brief that delegates work names the documents that own its
  subject, with their status, because a delegate finds documents through its
  brief before anything else.
- **Handoffs** name the decisions settled in the conversation but not yet
  written to their artifacts, so the next session can write them, and leave
  work that can wait beyond the next session to deferred issues.
- **Deferred work** is something an artifact, a ticket, or a release will need
  that can wait beyond the next session. An idea nothing depends on is not
  deferred work: mention it to the user and file it only if they ask. Deferred
  work is an open issue carrying the deferred label in the tracker configured
  by `docs/agents/issue-tracker.md` (if it is missing, ask the user to run
  `/setup-matt-pocock-skills`). The deferred label is the one
  `docs/agents/triage-labels.md` assigns to deferred work, or `deferred` where
  it assigns none. The issue states what to revisit, why it can wait, and the
  date or event that makes it due. The event is one a later session can verify
  from the repository or the tracker, such as an issue closing, a document
  being accepted, or a release. Open one directly, or publish a deferred
  breakdown through `to-tickets` with the deferred label in place of
  `ready-for-agent`, so no agent starts its tickets before their time.
  Before a grill-with-docs session, a ticket breakdown, a propagation, a
  migration, or next-work advice, read the open deferred issues relevant to it
  and check each against its due condition, the code, and the documents:
  - Due: take it up in the work at hand, or tell the user it is due. Work that
    starts from it keeps the issue, with the deferred label replaced by its
    triage label, rather than opening a new ticket.
  - Answered or delivered: close it with a link to the artifact or pull
    request.
  - Apparently dropped or overtaken: ask the user, then close it as not planned
    with the reason.

  Next-work advice reports these findings and changes nothing. Legacy
  `docs/deferred/` files are an archive.

## Reading guidance

Open a known relevant artifact directly. To find what the project decided on a
subject, search inside the folders that hold it: `docs/<authority>/` for shared
rules, `docs/features/<feature-slug>/` for a feature, `docs/adr/` for the
reasons behind a decision; then follow the links those documents carry. For
feature work, search the authority folders as well as the feature's, because
shared rules bind every feature. The folders already name subject and owner,
so this reaches the passage at a fraction of the cost of reading the common
rules first. When a search finds nothing, the subject may be documented in
other words: open the authority's boundary file or the authority table in
`docs/advisor-docs.md`. To place a document, select its authority in that table
and read the authority's boundary; to learn which decisions an action must
cover, read only the catalog the action needs. Do not load the documentation
tree as general context.

Follow relevant Dependencies, Review blocks, and linked decision passages.
Treat filenames and markers as routing information, not evidence of what a
document establishes.

Look for sources in `docs/sources/` and `docs/<authority>/sources/`. For feature
work, also inspect `docs/features/<feature-slug>/sources/` and
`docs/features/<feature-slug>/<authority>/sources/`. Inspect filenames and
opening lines to choose relevant full reads. A source has no required format.

Look for experiment material in the `experiments/` subfolders of these sources
locations. See the
[experiment placement convention](docs/advisor-docs.md#where-material-that-is-not-a-document-sits).

Recognize advisor scaffolds and catalogs by their fixed names. Unmarked project
documents may be relevant context; reading them does not adopt them as advisor
artifacts.

Cite the documents and passages supporting conclusions drawn from documentation.
Disclose unread material that could affect those conclusions.

Explain the project's documentation conventions from its local advisor files.
For the advisor's broader design and rationale, direct the user to its own
repository: <https://github.com/SebastianoTomasi/delivery-process-advisor>.
