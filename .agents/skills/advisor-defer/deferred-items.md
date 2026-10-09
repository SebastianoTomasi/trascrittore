# Deferred issues

Deferred work is an issue in the target project's configured tracker, identified
by the additional `advisor:deferred` label. It is project work, not a normative
artifact, implementation ticket, or conversation handoff. Legacy
`docs/deferred/` files are an archive: normal capture and recovery never read,
update, or import them, even when their `State` is `open`. Use
`advisor-migrate-deferred` only on an explicit migration request.

## Tracker prerequisite

Before capture, recovery, or closure, read both `docs/agents/issue-tracker.md`
and `docs/agents/triage-labels.md`. They are the same project-owned
configuration used by the separately installed `to-tickets` skill. If either
is missing, stop the dependent action and ask the user to run
`setup-matt-pocock-skills`; do not guess a tracker. If the configured tracker
cannot be queried, stop a session that requires recovery and report the
failure. Do not treat an empty or partial query result as a completed check.

Use the configured tracker operations. If `advisor:deferred` is absent from
the project's label configuration or tracker, add and provision it during
capture or explicit setup, preserving the configured type (`bug`,
`enhancement`, etc.) and triage labels. During read-only advice, stop and
request this setup instead of mutating either location. The label is a
separate routing axis, not a type or readiness state. Apply an existing type
label when the work clearly fits one; do not require a triage state merely
because an issue is waiting. Do not change another issue's labels without
checking whether it describes the same work.

## Capture

Accept a question, idea, or other future concern only when it is not an input
needed by the current decision. It must identify what to revisit and either a
possible outcome or a meaningful revisit condition. If unclear, invoke
the separately installed `grilling` skill for the shortest clarification that
establishes that minimum. Search open and closed issues for the same work and
read plausible matches, including comments, before creating anything. Update
an existing issue when it is the same work; link related but distinct work.

Inspect identifiable current work and the relevant authority boundary before
choosing Scope and Destination. Use `project`, `feature:<confirmed-slug>`, or
`undecided` for Scope; use an authority name or `undecided` for Destination.
Do not invent a feature identity, condition, or destination. Preserve an
undecided value when evidence does not settle it. An undeclared capability
belongs in the issue body and creates no feature folder.

The issue must make sense without the original conversation. Give it a clear
title, `Scope`, `Destination`, and `Revisit when`; explain the question or
outcome, why it can wait, accepted constraints, relevant links, partial
progress, and remaining questions. Keep the tracker issue open and apply
`advisor:deferred`. The tracker's open/closed state is its lifecycle; readiness
is assessed from the condition and current accepted decisions, never from a
required triage label. A Product non-goal alone creates no issue. If there is
real work to reconsider it, link the Product rule.

For a local Markdown tracker, use one file per issue at
`.scratch/advisor-deferred/issues/<descriptive-slug>.md`, separate from the
numbered feature tickets written by `to-tickets`. Keep a stable filename.
Use this opening shape and keep later discussion under `## Comments`:

```markdown
# Retry policy for payments

**Labels:** advisor:deferred, enhancement
**State:** open
**Scope:** feature:checkout
**Destination:** architecture
**Revisit when:** the payment provider contract is defined.

Decide which payment failures may be retried and how to avoid duplicate charges.
This can wait while Product settles uncertain payment outcomes. Link the
originating artifact and established constraints here.
```

`enhancement` is illustrative; use only labels configured for the project.
For a hosted tracker, put Scope, Destination, and Revisit when in the body and
use its native issue state, labels, and comments. Do not give a hosted issue a
second State field that could disagree with the tracker.

## Recover and classify

Before recommending work or starting or resuming an advisor session:

1. Query **open** issues carrying `advisor:deferred`. Verify the query completed
   and read titles and routing fields. Do not expand this inventory to ordinary
   issues or implementation tickets. Read relevant candidates in full,
   including comments and partial progress. For general next-work advice,
   consider every returned issue. For scoped work, include the feature and
   authority, applicable project work, undecided routing, and related subjects
   whose stored destination may be stale.
2. Compare the revisit condition and issue context with accepted decisions and
   necessary inputs. Report what is ready, still waiting (and for what), or
   apparently answered or superseded, with evidence. An issue's type, triage
   label, or open state alone proves no readiness. Do not save these judgements
   as another issue status or synchronized readiness label.
3. During an authorized session, fill an inferable destination from the
   authority boundary; ask only if routing changes intended scope. Advice-only
   work changes no issue. Consider relevant deferred work before dependent
   decisions, and re-evaluate waiting issues as inputs settle. Keep the
   session's questioning procedure.

## Resume and close

Keep partial progress and remaining questions in the open issue or its
comments. Put a settled answer in the owning artifact through
`advisor-grill-with-docs`, or `advisor-propagate-change` when it changes an
accepted rule. Verify an apparent existing answer applies before closure.
Then add a resolution linking the authoritative answer and close the issue.
A deliberately dropped issue closes with the user's agreed reason. Retain
closed issues in the tracker; do not delete them. Closure tracks work and does
not itself accept a normative decision.
