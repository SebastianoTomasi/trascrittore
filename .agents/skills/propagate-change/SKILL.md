---
name: propagate-change
description: Propagate a change to an accepted decision through its dependent artifacts. Use for substantive rule changes, assessing whether a changed source requires one, or resuming an interrupted propagation marked needs-review.
disable-model-invocation: false
---

Finish with one authoritative current rule and coherent dependent artifacts.
Apply wording-only corrections directly when meaning, dependencies, and scope
are unchanged. A changed source prompts assessment of the current rule and its
ADRs; it does not authorize a replacement. Propagate only an agreed change.

Follow `advisor-agents.md` for selective reading and relevant deferred work,
and `docs/advisor-docs.md` for writing, statuses, Review blocks, dependencies,
and acceptance, including coupled decisions. Read them if not already in
context. Use `grilling` only for unresolved choices and `domain-modeling` for
changed terminology or qualifying ADRs.

## Establish the change

Identify the owning passage, the old and replacement decisions, the reason,
and which clauses remain valid. Recover settled answers and delegation from
the conversation and artifacts; apply determined consequences without another
approval. Explain and ask only new choices. Discover impact while a choice or
reason is pending, but settle both before accepting its replacement. Keep the
current rule in force while a replacement is proposed; any draft names the
passage it would replace.

## Trace the effects

Trace direct and transitive dependants through their Dependencies links, and
search paths, headings, terms, old formulations, and ADR references.
Inspect likely related artifact scopes
for missing links, including shared rules, features, screening answers, and
dismissals. Read affected authority boundaries and relevant catalogs as needed;
do not reopen unrelated phases. Search matches are candidates for semantic
review, not a complete dependency graph or automatic replacements.

Keep a compact working map in the session: candidate passage, consequence,
and disposition (amend, checked-compatible, unaffected, or unresolved choice).
Extend it as new effects emerge; do not persist another registry.

## Apply settled decisions

Before replacing the rule, mark affected accepted artifacts whose compatibility
is unchecked `needs-review` with the required Review blocks. Existing proposals
stay proposed and record their changed input and remaining work.

Write the rule in its owning artifact. Elsewhere update consequences and links
without duplicating its definition or rationale. Update affected dependency
links and dismissals, and integrate or remove replaced proposals and `absent.md`.
Record qualifying ADRs with reasons and sources. For an older ADR, distinguish
full supersession from replacement of specific clauses; identify what still
stands using its existing format. An ADR status never overrides the owning rule.

Check compatibility before restoring acceptance, even when the body needs no
edit. Settle and accept coupled decisions together under the common rules.

## Verify and close

Review the affected documents together against the agreed change:

- Every candidate has a resolved disposition and each affected dependency is
  compatible; revisit catalog coverage where an answer or dismissal changed.
- Old formulations no longer state the current rule; paths and anchors resolve.
- Current rationale links reflect full or partial ADR replacement. Preserve
  historical accounts and source evidence instead of rewriting them as current.
- Each rule has one owner, with no contradictory or duplicated definitions or
  rationale introduced by the propagation.

Finish only when propagation is complete. Summarize the changed rule, amended
or confirmed documents, relevant ADRs, and any resulting advice.

If interrupted, leave actionable Review blocks and report incomplete work. If
the owning rule has not yet been replaced, say so and link the agreed draft or
ADR. Resume from those blocks and decisions, complete the remaining work, and
remove Review blocks only when acceptance is justified. `needs-review` is
recovery state, not successful closure.
