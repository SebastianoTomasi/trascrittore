---
name: advisor-grill-with-docs
description: Conduct an advisor-grill-with-docs session, writing what settles into the project's own documents as it settles. Use when writing, filling in, or accepting a normative document under docs/ (product, architecture, implementation, frontend, security, deployment, operations, development, stack), when declaring or advancing a feature, or when pressure-testing a plan or design whose outcome the project should keep. To change a rule the project has already accepted, use advisor-propagate-change.
disable-model-invocation: false
---

Use the separately installed `grilling` skill to resolve open decisions,
invoking the separately installed `domain-modeling` skill as terms or
qualifying decisions settle.
Invoke `advisor-defer` to record agreed future work and to recover relevant
items before starting or resuming a session. That skill owns clarification,
capture, classification, recovery, partial progress, and closure in the
configured issue tracker.

## Preparation

Before starting or resuming a session, recover relevant deferred items through
`advisor-defer`, including undecided destinations. Read `docs/advisor-docs.md`
for document rules and use the shared reading guidance in `advisor-agents.md`
to find the relevant artifacts and sources. Read the owning authority's boundary
and only the catalog for the current scope or triggered need. Use its decisions,
dependencies, and recommended order with the answers already settled to select
the next useful question. Complete those relevant reads before the first session
question. Migration owns full reads of its selected inputs and invokes this
workflow for decisions.

## Starting a feature

When the user describes a new capability, apply the identity, declaration, and
phase-route rules in `docs/features/advisor-features.md`; that file owns them.
Read it when it is not already read. Writing the first proposed Product artifact
under those rules is what declares the feature, and it is this procedure that
writes it.

## Writing and accepting

For new features, use Starting a feature above before the first write.

1. Apply the placement and artifact-boundary rules in `docs/advisor-docs.md`.
   Inspect existing routing envelopes and reuse the artifact whose Scope owns
   the content; otherwise create the minimum new artifact with a descriptive
   name, proposed status, and Scope. Choose a structure suited to its subject.
   This choice is autonomous and may be revised as answers settle.
2. Resolve explicitly delegated choices under `docs/advisor-docs.md`. Put the
   remaining unresolved, decision-critical choices to the user through
   `grilling`, and write each answer as it settles into the artifact where it
   naturally belongs. Questions measure coverage; they do not become the document layout.
3. Keep each artifact under one authority. Link decisions owned elsewhere and
   write new cross-authority decisions in their owning artifacts, at project
   scope when shared or feature scope when specific. Maintain Dependencies with
   passage links and explanations, not just navigation links. For a substantive
   screening answer, link its authoritative answer and settle any input needed
   now; use `advisor-defer` only for work that can wait.
4. Invoke `domain-modeling` to update resolved terms and qualifying ADRs
   as decisions settle. Important decisions keep their reasons, alternatives,
   and informative source links in the ADR; current artifacts state the rule
   and link to it. Preserve existing ADR folders and numbering.
5. Accept an individual artifact once its envelope and dependency references
   are sound, its own decisions and any triggering question are settled, and
   the necessary decision inputs are accepted and compatible. Do not require
   an authority's unused demand-driven catalog to be exhausted, or a catalog
   question for a document that belongs by its boundary. This applies at either
   scope. Individually accepted artifacts may leave a phase incomplete.
   For a coupled set, settle all choices, verify its internal consistency and
   accepted external inputs, then accept the set together; mutual draft links
   alone never justify acceptance. If writing that acceptance is interrupted,
   retain recovery notes until every member is checked and accepted.
6. Before claiming a foundation or feature phase complete, read its catalog and
   every artifact in its folder, including proposals and `absent.md`. Map each
   question to an accepted answer or named dismissal; follow linked screening
   answers and decision inputs. Check for missing coverage, contradictions, or
   dependencies under review. Accept completed drafts through step 5 before
   counting them; never infer coverage merely because all markers are accepted.
   An unrelated proposed extension does not undo existing accepted coverage.
   Report the question-to-artifact-and-passage mapping and what remains open;
   do not persist a coverage registry.

If the user chooses work without its necessary inputs, keep the result proposed
and name the unresolved assumptions. A draft that does not change a current
decision leaves that decision and unrelated feature work usable.

## Closing a feature phase with no decisions

Before writing `absent.md`, read the entire feature catalog and check every
question, including screening questions, against the relevant accepted
decisions. Apply the absence contract in `docs/features/advisor-features.md`:
write Scope and a justified dismissal for every slug, linking accepted answers
and dependencies when they support dismissal. A substantive answer requires
a normal artifact rather than blanket absence. Read available evidence before
asking only unresolved decision-critical questions; no interview question is
required for each catalog entry. Accept through the writing and acceptance
procedure above only when all dismissals and necessary inputs are sound.

When a change to an already accepted rule is needed, that is a different
procedure: use `advisor-propagate-change`.
