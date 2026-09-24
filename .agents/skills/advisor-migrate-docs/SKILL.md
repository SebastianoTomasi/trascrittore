---
name: advisor-migrate-docs
description: Migrate one or more user-selected documents into an initialized delivery-process-advisor project. Reorganize their content into advisor documents, resolve necessary decisions with the user, and replace the in-scope originals without retaining source copies. Use when adopting, migrating, or restructuring existing documentation, including pre-existing project documents that carry no advisor marker; the request to migrate is itself the adoption, and no second adoption request is needed. This skill owns the migration case and invokes advisor-grill-with-docs for writing and acceptance, and advisor-propagate-change when a migration changes a rule the project has already accepted.
disable-model-invocation: false
---

# Migrate documents into the advisor

Transfer the supplied content faithfully into the project's advisor structure.
Resolve only choices needed for that transfer; report missing design decisions
as later work. Completed migration leaves the new documents, with no copies of
the originals in `sources/`, archives, or replacement stubs.

## Read and map

1. Identify the target project and the input documents from the request and
   conversation. Read `advisor-agents.md` and `docs/advisor-docs.md` in that
   project. If required advisor instructions are missing, name what is needed
   before writing dependent documents; do not invent the scaffold or treat
   initialization as migration.
2. Read every input in full, using tools appropriate to its format. Include
   meaningful tables, diagrams, notes, and linked material needed to interpret
   it. A linked document is context, not automatically another migration input.
   Identify unreadable or unavailable portions and pause the affected transfer;
   never treat an extraction failure as empty content.
3. Follow the advisor's reading path to inspect relevant existing artifacts,
   authority boundaries, and only the catalogs for the scopes being migrated.
   Choose authority and project or feature scope from the decisions expressed,
   not the original filename or layout. Shared rules belong at project scope;
   feature-specific rules link to them. Reuse a document whose Scope owns the
   content; otherwise create the minimum documents its subjects require.
4. Keep a compact working map from meaningful input passages to destination
   documents and sections, including unresolved items and agreed exclusions.
   Use it to check loss and duplication across all inputs. Keep this in the
   session, not a permanent migration or coverage registry.

For a new feature, use the Starting a feature procedure in
`advisor-grill-with-docs`, applying the identity and placement rules in
`docs/features/advisor-features.md` to the supplied capability information. Ask for missing information only when needed to place
the content. Do not invent Product decisions or complete the foundation just
to file later-phase material; record unresolved inputs in proposed work.

## Resolve only necessary decisions

Resolve explicitly delegated choices under `docs/advisor-docs.md`. Use
`advisor-grill-me`, the bundled `grill-me` skill, for remaining choices that
change the migration. Ask one question at a time, explain the consequence,
suggest a default, and wait for the answer before applying that choice.
Continue independent transfers where useful. The migration request authorizes
writing documents as decisions settle.

- Treat explicit decisions in documents the user identifies as current project
  specifications as already settled. Do not ask the user to approve them again.
  For notes, alternatives, or descriptions of another system, establish their
  intended role only when it affects what becomes a project rule. Neither
  confident wording nor an old status alone establishes advisor acceptance.
- Ask about conflicting decisions, ambiguous terms or scope that change
  meaning, and substantive content that cannot be placed without changing or
  discarding it. Show the relevant passages. Resolve routine filenames,
  organization, and wording autonomously within the advisor's rules.
- A conflict with an accepted artifact requires a decision under
  `docs/advisor-docs.md`. Preserve
  the current rule while its replacement is only a proposal. Apply an agreed
  change through `advisor-propagate-change`, including affected dependants.
- Report catalog questions the inputs do not answer as gaps. Do not turn them
  into a general design interview, invent answers, or infer inapplicability
  from silence. An unresolved necessary input keeps the affected work proposed;
  an unrelated gap does not prevent acceptance of a sound artifact.

## Write and verify

Use the writing and acceptance procedures in `advisor-grill-with-docs` within
this migration's scope, and `advisor-propagate-change` when the migration
changes a rule the project has already accepted. Use
`advisor-domain-modeling` for resolved terminology and qualifying ADRs; preserve
existing ADR locations, numbering, and decision history. Keep existing reasons
and alternatives without inventing rationale or manufacturing an ADR for each
moved paragraph.

Split mixed documents by ownership and merge overlapping content where its
meaning is equivalent. Each rule has one authoritative home. Preserve
conditions, exceptions, examples that explain behavior, and the distinction
between current decisions, proposals, and historical alternatives. Artifact
structure follows its subject, with the required status, Scope, and decision
Dependencies; glossary entries and ADRs keep their own formats. Keep proposals
distinct from current rules, with their unresolved assumptions visible.

Check the replacements against the inputs and relevant project documents:

- Every meaningful passage is represented or its substantive exclusion was
  settled; constraints change only where a change was settled with the user
  or within their explicit delegation during migration.
- Authority, scope, terminology, and cross-document decisions are coherent.
- Dependencies point to the decisions actually relied on, explain why, and
  have compatible accepted inputs before the dependent artifact is accepted.
  Follow the existing joint-acceptance procedure for coupled decisions.
- Moved paths, headings, and references resolve to the new owning passages.
  Preserve useful provenance in ADRs or beside smaller decisions: use an
  existing stable version link when available, otherwise a factual citation
  identifying the original document and passage. Do not create a retained copy
  or a link to a file about to be removed just to preserve provenance.

Accept sound artifacts without another approval round for decisions already
settled. This checks migration fidelity, coherence, and dependencies; it is
not a general audit of the project's design. A completed migration may contain
proposed artifacts and leave phases incomplete. Claim phase completion only
after the separate catalog coverage checks in `advisor-grill-with-docs`.

## Replace originals and close

Write and verify replacements before removing an original. Search the target
project for references to its old path and headings and update affected links,
including entry points and Dependencies. Inspect related passages for textual
references that a path search may miss. For an in-place replacement, prepare
and compare the new text before overwriting, then reread and keep the rewritten
file. Retain needed attachments as part of the new
documentation or reproduce their content; do not leave them linked only
through a discarded original.

Remove only input files inside the target project that this migration replaces.
Do not retain them as sources, archives, or redirect documents. External input
files and remote documents are read without importing copies into the advisor;
deleting those external originals requires that scope in the user's request.
Resolve actual deletion paths within the target and remove only checked input
files, never whole folders. Do not delete unrelated sources or existing advisor
instructions, scaffolds, catalogs, or skill files.

Before removal, verify that each input's content is accounted for, its output
is saved and readable, and its references are repaired. Proposed output can
preserve an unresolved decision faithfully; unresolved transfer, unreadable
content, or an undecided exclusion prevents removal of that input. On an
interruption, retain unverified originals temporarily and report the migration
as incomplete, with remaining files and work. Use the advisor's Review blocks
for interrupted changes to accepted rules. Resume by inspecting existing output
and remaining inputs rather than creating duplicate artifacts.

Finish with a concise account of input-to-output destinations, originals
replaced or removed, decisions resolved, resulting statuses, and remaining gaps
or incomplete transfers. Distinguish migration completion from design or phase
completion; do not persist another status register.
