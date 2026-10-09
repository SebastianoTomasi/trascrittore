# Documentation rules and navigation

This page defines the common documentation contract and routes subjects to  
their owning authority. Shared reading guidance is in  
[`advisor-agents.md`](../advisor-agents.md); skills own the workflows that apply  
these rules.

## Decisions and authority

An artifact records decisions established with the user, including choices the
user explicitly delegates to the agent. Within that delegation, the agent's
choice is settled and can be accepted without further user confirmation when
the usual acceptance conditions hold. A choice made without the user's
agreement or outside their delegation remains proposed. A session is the
ordinary way to establish decisions and the one to recommend; a document
written another way is held to the same acceptance rules. Acceptance records
a settled decision, not evidence that it has been implemented.

Code establishes what is implemented. Existing behavior absent from the docs  
creates no obligation to change or document it. Accepted documentation guides  
the work it specifies that has not yet been implemented. When code and docs  
explicitly contradict one another, the discrepancy needs clarification with  
the user; it proves neither a bug nor outdated documentation. Preserve the  
implementation while the intended change is clarified.

The advisor’s position is advice. Accepted decisions guide the agent’s  
reasoning, while the user remains free to change direction. Proceeding against  
advice creates no extra permission step, deviation record, flag, or reminder.  
Work assuming unresolved decision inputs remains proposed and names them.

## Which authority owns what

Use this summary to choose which authority folder to inspect. It intentionally  
repeats each authority’s local description at routing depth; the linked  
authority scaffold’s opening `Boundary` block is more specific and resolves  
close cases without requiring any separate question catalog.

| Authority | Owns |
| --- | --- |
| [Product](product/advisor-product.md) | Cross-system requirements, actors, behavior, privacy and legal requirements, and the compatibility baseline the product promises not to break |
| [Frontend](frontend/advisor-frontend.md) | Approved client-visible behavior and interaction contracts |
| [Architecture](architecture/advisor-architecture.md) | Implementation-independent system and module contracts |
| [Implementation](implementation/advisor-implementation.md) | Significant, non-obvious internal design for clients, servers, local applications, CLIs, and jobs |
| [Security](security/advisor-security.md) | Security policy and control requirements |
| [Deployment](deployment/advisor-deployment.md) | Procedures for delivering and deploying the system |
| [Operations](operations/advisor-operations.md) | Procedures for operating the system in production |
| [Development](development/advisor-development.md) | Development and test guidance |
| [Stack](stack/advisor-stack.md) | The selected technology inventory, versions, and shared defaults |

The line between Architecture and Implementation follows the guarantees offered
across a unit's boundary. Architecture defines or changes what a client,
integrator, another unit, or a reader of persisted state may rely on.
Implementation chooses the internal mechanics that satisfy those contracts,
including choices whose measurable differences the contracts permit.

For example, a response-time guarantee across a component boundary belongs to
Architecture; an algorithm chosen to meet it belongs to Implementation. A
measurable timing difference alone does not change that ownership.

There is no top-level API, contracts, data, quality, privacy, or planning  
folder. Test guidance belongs to Development or to the code. Delivery status  
belongs to the task system.

## Where a document goes

A document sits in the folder of the authority that owns it, whatever kind of  
document it is. Its name is free and is chosen when it is written, because the  
folder already states the authority and the marker line already states the status.  
Choose a descriptive filename and title: a reader must be able to judge the  
document’s subject before reading its body.

A document has one owning authority even when its subject touches several. It  
may link to another authority’s rule and mention it for context, but it does not  
duplicate that rule. A new decision owned elsewhere is written in that  
authority’s document.

Project-scoped documents sit in `docs/<authority>/`. A feature’s documents sit  
together in `docs/features/<feature-slug>/<authority>/`, so that the unit of work and  
the unit of navigation are the same thing. Every authority permits both scopes.  
Create a feature authority folder with its first artifact, never in advance.  
Shared rules remain at project scope; feature-specific applications link to  
them. Folder presence shows where documentation exists, not phase completion.

There is one fixed name: `absent.md`, the document that closes a phase this  
feature has nothing to decide in. Its name is fixed so the dismissal is visible  
in a listing.

Two positions belong to the advisor’s process but hold content the project  
owns: `GLOSSARY.md` at the project root, and `docs/adr/` for decision records.  
Neither is an artifact, and neither carries the `advisor-` prefix, a scaffold  
or a question list: nothing is delivered there, and the  
separately installed `domain-modeling` skill carries their format.

## Where material that is not a document sits

Material a session reads but the project does not own as a rule — know-how, an  
external specification, a description of a system being replaced, a research result — sits in a  
`sources/` folder. Four positions exist and no others:

```
docs/sources/
docs/<authority>/sources/
docs/features/<feature-slug>/sources/
docs/features/<feature-slug>/<authority>/sources/
```

The position states which work the material is relevant to, never who owns it:
a source belongs to no authority at any of these positions. `docs/sources/` is
considered across the project, while `docs/features/<feature-slug>/sources/`
holds material shared across authorities within one feature. Material relevant
to one authority belongs in that authority's `sources/` folder at project or
feature scope. Select full reads by relevance; broader placement makes a
source a candidate for more work, not a mandatory full read for every session.

Store experiment material in an `experiments/` subfolder of the relevant
`sources/` location. Use `docs/sources/experiments/` for experiments relevant
across the project. Look in these subfolders when selecting sources relevant
to the current work. Experiment material remains informative; storing it does
not adopt its findings as decisions. The agent carrying out the experiments
manages their conduct and lifecycle.

A source is the user’s file, not the advisor’s: no `advisor-` prefix, no  
scaffold, no question list and no marker line, so it belongs to no phase and  
counts toward no position. None is delivered — a `sources/` folder exists  
because someone put a file in it.  
A source informs decisions but establishes no project rule. Its content  
constrains work only when the owning artifact states the adopted decision in  
the project’s own words. A contradiction with an accepted artifact is a  
question for the user, not an override. Preserve informative source links using  
the provenance rule below; updating a source alone changes no accepted rule.  
Source discovery follows [the shared reading guidance](../advisor-agents.md#reading-guidance);  
the workflow determines when that reading is needed.

## What a document says about itself

Deferred work lives in project-owned `advisor:deferred` issues in the
configured tracker, outside every authority and phase. Issue open/closed state
is distinct from the artifact statuses below. Legacy `docs/deferred/` files
are an archive and are not recovered unless explicitly migrated.

An artifact places one line directly below its title, never in frontmatter:

-   `**Status:** proposed` — a draft or alternative, not a current rule.
-   `**Status:** accepted` — a current rule whose decisions are settled and whose  
    necessary decision inputs are accepted and compatible.
-   `**Status:** needs-review` — a previously accepted artifact whose compatibility  
    with a changed decision still needs verification. Do not rely on it yet.

The status applies to the whole artifact, not individual sections. A
`needs-review` artifact supplies no accepted decision input until its review
is complete, even when only part of its content prompted the review.

Every artifact opens with `## Scope`, a short paragraph stating what it governs  
and which nearby concern it leaves elsewhere. Filename, title, status, and  
Scope are its routing envelope; the rest follows its subject, with the common  
sections below when applicable. Advisor scaffolds and catalogs have no artifact  
status. The glossary and ADRs keep their own format. Unmarked project documents  
count toward no phase. Reading them does not adopt them as advisor artifacts;  
the user chooses adoption, and a request to migrate selected material is itself  
that choice.

### Dependencies and provenance

When an artifact relies on decisions in other artifacts, put `## Dependencies`  
immediately after Scope. Each bullet links to the relevant heading or anchor  
and briefly explains which decision here relies on it and why. For example,  
from a feature Product artifact:

```md
## Dependencies

- [Product visibility](../../../product/catalog.md#visibility) — search results
  include only published products, so a visibility change requires reviewing
  the search filter and its results.
```

Omit this section when there are no decision dependencies. A navigation link  
alone is not a dependency. Keep these references accurate as decisions evolve,  
including dependencies across features; repair anchors when moving or renaming  
sections. Proposed work explicitly identifies any unresolved input it assumes.

Link important decisions to the relevant ADR for their reasons and informative  
sources. If a decision does not qualify for an ADR, a brief informative source  
link may accompany it. Such links preserve provenance, never delegate the rule  
to a source. A changed or removed source prompts assessment, not an automatic  
change of status or rule. ADRs are not phases or prerequisites.

### Interrupted review

A `needs-review` artifact also has `## Review` after Dependencies (or Scope  
when there are none), containing:

-   **Cause:** what changed and why this artifact may be affected;
-   **Changed decision:** a link to the changed artifact passage;
-   **Decision record:** a link to the relevant ADR when one exists;
-   **Remaining work:** the checks, amendments, or unresolved choices required.

When an upstream input is still under review, link to it as well as to the  
originating change. A bare marker is insufficient. Keep existing Dependencies  
while recording recovery information. Restore `accepted` and remove Review  
only after checking compatibility, even when no body text needs changing.

### Proposals and accepted decisions

Initial foundation work is incomplete until accepted artifacts cover its  
catalog questions. A new `proposed` artifact does not withdraw coverage already
supplied by accepted artifacts or reopen unrelated work, even while the
foundation is incomplete. A proposal to
replace a rule identifies the affected accepted passage in Scope and leaves  
that rule in force until the change is agreed. Do not silently rewrite an  
accepted rule while discussing its replacement.

When a change is agreed, propagate it: update the current owning rule, review  
its affected dependants, and finish with coherent documents. Integrate the proposal into the  
one authoritative rule and remove any now-redundant draft. A change that removes  
accepted coverage or leaves an affected dependency under review makes that work  
unfinished; unrelated decisions in other accepted artifacts remain usable.

## Usual phase order and decision readiness

1.  Product foundation — [project catalog](product/advisor-product-project.md)
2.  Architecture foundation — [project catalog](architecture/advisor-architecture-project.md)
3.  feature Product — [feature catalog](product/advisor-product-feature.md)
4.  feature Frontend — [feature catalog](frontend/advisor-frontend-feature.md)
5.  feature Architecture — [feature catalog](architecture/advisor-architecture-feature.md)
6.  feature Implementation — [feature catalog](implementation/advisor-implementation-feature.md)

This is the normal route, not a total prerequisite chain. Frontend usually  
precedes Architecture because it sharpens the behavior the system must support.  
Each catalog gives the usual inputs and sequence within its phase; these steps  
create no extra folders, markers, or completion states.  
Catalogs own subject-specific decisions, their dependencies, and recommended  
order. Skills use those inputs and the decisions already settled to conduct the  
work; the catalogs do not define the session procedure.

A decision is ready when its necessary inputs are accepted and compatible,  
and remaining open choices cannot invalidate it. A later-phase decision can  
be ready before an earlier phase is complete. This includes the initial
foundation: incomplete Product or Architecture coverage does not prevent
starting feature work or accepting a feature decision whose readiness is
established. The foundation remains incomplete until its full catalog coverage
is accepted.

Proposed or needs-review inputs do not establish readiness. Circular
dependencies require the coupled choices
to be settled together; neither draft proves the other’s readiness. Internal  
consistency and accepted external inputs permit joint acceptance of the  
settled set. Interrupted acceptance retains recovery notes until the whole set  
has been verified.

For example, accepted export content and rules can support its Architecture  
file contract while the launch screen remains open, provided the interaction  
choices cannot change the file’s contents, delivery, or failure guarantees.  
Do not declare the whole Architecture phase complete from this one decision.

A phase is complete when accepted, mutually compatible artifacts cover every  
question or explicitly dismiss it, and no unresolved decision needed by that  
coverage remains. All markers being accepted is insufficient; an unrelated  
proposed extension does not remove accepted coverage. The workflow’s semantic  
acceptance check establishes whether these conditions hold.

Security, Deployment, Operations, Development, and Stack have no phase of their  
own. Their screening questions occur in the phase catalogs where the necessary  
inputs normally become available. A substantive answer creates or amends an  
artifact in its owning authority, at project scope if shared or feature scope  
if specific. The screening answer links to that artifact and states the  
dependency; a new folder adds no phase. Their single demand-driven catalogs  
serve either scope and are read only for the triggered need.

## Artifact boundaries and structure

An artifact has a descriptive name and a structure suited to its subject. The  
questions measure coverage; they do not prescribe the document’s sections.  
Content already owned by an artifact’s Scope belongs there. Additional artifacts  
exist only when distinct scopes require them; their placement and boundaries  
may be revised as decisions settle.
