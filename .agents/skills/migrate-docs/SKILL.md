---
name: migrate-docs
description: Adopt or migrate user-selected documentation into an initialized delivery-process-advisor project, preserving meaning and replacing superseded originals. Use for migration into the advisor structure, including reorganization of existing artifacts; ordinary document edits do not require this skill.
disable-model-invocation: false
---

# Migrate documents into the advisor

Give the selected content one appropriate home without redesigning the project.
Preserve decisions, proposals, informative material, and unresolved design as
distinct things. Migration completion does not imply design or phase completion.

## Establish the transfer

Read `advisor-agents.md` and `docs/advisor-docs.md` unless already read. Follow
their reading guidance, relevant deferred-work lookup, and documentation rules.
If required advisor instructions are missing, report what is needed before
writing dependent documents; initialization is separate work.

Identify the target project and selected inputs from the request and conversation.
Read each input fully, including meaningful tables, diagrams, notes, attachments,
and linked context needed to interpret it. Linked documents are not automatically
migration inputs. Unreadable content blocks only the affected transfer.

For each meaningful passage, identify its role and destination:

- Current project decisions: reuse the artifact whose Scope owns them.
- Equivalent existing content: merge without duplicating the rule.
- Content with no suitable owner: create the minimum necessary artifacts.
- Informative material: preserve its context in one permitted `sources/` location.
- Proposals and unresolved choices: preserve them explicitly as proposed work.

Split mixed inputs by role and ownership. Choose authority and project or feature
scope by meaning, not by the old layout. Follow relevant authority boundaries
and catalogs. For a new feature, apply `docs/features/advisor-features.md`;
ask only for information needed to place the supplied content.

Keep a compact passage-to-destination map in the session, including unresolved
transfers and agreed exclusions. Use it to check coverage across all inputs;
do not create a permanent migration registry.

## Resolve transfer decisions

The migration request authorizes adoption and writing as decisions settle.
Explicit decisions in documents the user identifies as current specifications
are already settled; old status labels or confident wording alone do not
establish acceptance.

Handle filenames, organization, wording, and explicitly delegated choices
autonomously. Use `grilling` only for unresolved choices affecting the transfer:
conflicting decisions, meaning or scope, normative versus informative role,
or substantive exclusions. Show the relevant passages, recommend an answer,
and await it before applying that choice. Continue independent transfers.

Preserve accepted rules while replacements remain proposals. Use
`propagate-change` when an agreed transfer changes an accepted rule.

Report unanswered relevant catalog questions as gaps. Do not invent answers,
infer inapplicability from silence, or expand migration into a design interview.
Missing design may remain proposed; missing transfer decisions block the
affected transfer.

## Write and verify

Use the writing and acceptance steps in `docs/advisor-docs.md`. Reuse existing
owners before creating documents. Keep current rules distinct from proposals.

Preserve conditions, exceptions, behavior-explaining examples, reasons,
alternatives, and unresolved assumptions. Use `domain-modeling` for resolved
terms and qualifying ADRs, preserving existing formats, locations, numbering,
and decision history. Do not invent rationale or an ADR for every moved passage.

Verify each replacement against the inputs and relevant existing artifacts:

- Every meaningful passage is represented or its exclusion was settled.
- Meaning changes were agreed or explicitly delegated.
- Ownership, terminology, and cross-document decisions are coherent.
- Dependencies and acceptance satisfy the common documentation rules.
- Useful provenance identifies the original passage through an existing stable
  version link or factual citation, never a link to an original being removed.

Accept eligible artifacts without reconfirming settled decisions. Unrelated
design gaps do not block acceptance. Claim phase completion only after the
common phase-completion check.

## Replace originals and report

Before removing an input:

1. Save and read its verified replacement.
2. Repair references across the target project, including entry points,
   Dependencies, old headings, and relevant textual mentions.
3. Preserve needed attachments at their new home or reproduce their content.
4. Confirm that no unreadable content, unresolved transfer, or undecided
   exclusion remains.

For an in-place replacement, compare the prepared text before overwriting,
then reread and retain the rewritten file.

Remove only superseded input files whose resolved paths are inside the target
project. Never remove whole folders, unrelated sources, advisor instructions,
scaffolds, catalogs, or skills. Keep no archival copies or redirect stubs for
replaced specifications. Informative inputs retain one appropriate copy.

Read external inputs without importing copies. Deleting external originals
requires explicit scope in the user's request.

Proposed output may faithfully preserve unresolved design and still replace its
input. If transfer or verification is incomplete, retain the affected original
and report the remaining work. Follow the common Review rules for interrupted
changes to accepted decisions. Resume from existing outputs and remaining inputs.

Finish with destinations, originals replaced or retained, resolved choices,
resulting statuses, and remaining gaps. State whether migration itself is complete.
