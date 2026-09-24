---
name: advisor-propagate-change
description: Propagate an agreed change to an accepted rule through every artifact that depends on it. Use when a term, capability, contract, prerequisite, or other accepted decision under docs/ must change, when a changed source may have invalidated an accepted decision, or when resuming an interrupted propagation left behind as needs-review.
disable-model-invocation: false
---

Changing an accepted rule is one procedure with one outcome: the rule and every
artifact depending on it are coherent again. A wording-only correction is not
this procedure and can be applied directly after checking that it changes no
meaning, dependency, or scope.

Before starting or resuming, recover relevant deferred items through
`advisor-defer`. Read `docs/advisor-docs.md` for the status, dependency, Review
block, and provenance rules, and use the shared reading guidance in
`advisor-agents.md` to find the affected artifacts; read those files when they
are not already read. Use `advisor-grill-me` for the questions this procedure
raises and `advisor-grill-with-docs` for writing and accepting the artifacts it
changes. Invoke `advisor-domain-modeling` for a qualifying ADR.

## Propagating the change

A change to a term, capability, contract, prerequisite, or other accepted rule
starts a focused session:

1. Identify the owning decision and passage, the reason for the change, and the
   proposed replacement. While the replacement is only a proposal, preserve the
   accepted rule; a separate draft names the passage it proposes to replace.
   A missing reason does not delay independently knowable impact discovery in
   step 2; obtain it before accepting the replacement.
2. Trace direct and transitive dependants by reading Dependencies and searching
   artifact references to the changed path, headings, and terms. Inspect likely
   related routing envelopes as well: missing links are possible, so search
   results are candidates for semantic review, not a complete dependency graph.
   Include shared rules, affected features, screening answers, and dismissals.
   Read each affected authority boundary and relevant catalog as the work reaches
   it, using the root file's selective reading guidance.
   Do not reopen unrelated phases merely because the change is upstream.
3. Explain consequences, resolve explicitly delegated choices under
   `docs/advisor-docs.md`, and ask only the remaining new choices, one at a time.
   Apply consequences already determined by the answers without
   seeking approval for each document edit. If more decisions are coupled,
   resolve their compatible replacement together; do not accept drafts using
   each other as their only evidence of readiness.
4. When the change is agreed, use `advisor-domain-modeling` for the qualifying
   ADR, including reasons and sources, and supersede an incompatible old ADR
   through its existing format. Before replacing a current rule, mark affected
   accepted artifacts whose compatibility is not yet checked `needs-review`
   and write the Review block required by `docs/advisor-docs.md`. Link the
   changed decision and ADR when present, with concrete remaining work. If an
   interruption occurs before the rule replacement, say that applying the
   agreed replacement is still pending and link its draft or ADR. Existing
   proposed dependants stay proposed and record the changed input and work left.
5. Update the owning rule and every affected artifact, dependency link, and
   dismissal. A checked-compatible artifact may return to accepted unchanged;
   an incompatible one is amended from settled answers and then accepted. When
   more effects emerge, trace them in turn. Update or remove a replaced proposal
   or blanket `absent.md` so there is still one authoritative current rule.
6. Review the affected documents together for contradictions and unresolved
   dependencies. Recheck affected catalog coverage when an answer or dismissal
   changed. Close the session only when propagation is complete and the affected
   documents are coherent; summarize the changed rule, updated or confirmed
   documents, ADR, and resulting advice.

`needs-review` supports recovery from interruption or a user pause, not the
normal outcome. If work must stop, update each Review block with cause, changed
passage, relevant ADR, and remaining checks or decisions; report the work as
incomplete. On resumption, read those blocks and the changed decisions, finish
the propagation, then remove the recovery blocks when acceptance is justified.
Do not create another change or rationale registry.

A changed source only identifies decisions that may deserve reconsideration.
Read their ADRs and current rules, raise any substantive conflict, and use this
procedure only when an accepted decision is actually changed. Neither a source
nor an ADR status overrides a normative artifact automatically.
