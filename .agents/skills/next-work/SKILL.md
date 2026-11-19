---
name: next-work
description: Recommend the next useful work in an advisor-guided project. Use when the user asks where the project stands or what to prioritize, not when they have chosen a concrete task or requested a documentation session.
disable-model-invocation: false
---

# Next-work advice

Recommend one useful next action. Keep the assessment read-only: do not start an
interview, change files or tracker state, or create reminders. Stop after the
recommendation; the user's selection is a new request.

## Establish the current state

Read `advisor-agents.md` and `docs/advisor-docs.md` if not already read; apply
their reading, readiness, and conflict rules.

Start from the user's current goal, active issues, pull requests, and work in
progress. Use the configured tracker guidance. For a general request, consider
every open deferred issue; for scoped work, those relevant to the scope or
shared prerequisites. Check candidates' current state: an open issue or an old
plan may describe work already delivered or underway.

Deepen the assessment where evidence can change the choice. Read relevant
artifacts and dependencies, code, existing tests, and delivery evidence; run a
safe focused check when it can resolve a deciding uncertainty. Expand discovery
if candidates are unclear. A general recommendation does not require inspecting
every artifact; assess full phase coverage only when requested.

Stop exploring when evidence supports a choice over plausible alternatives and
remaining uncertainty would not change it. If a deciding uncertainty cannot be
resolved, report it and consider verification as the next action.

## Select the recommendation

Distinguish absent behavior, broken behavior, and unverified behavior. Missing
documentation or verification does not establish missing implementation.

Prioritize a working primary journey: build the smallest missing end-to-end
slice, repair a demonstrated failure, or verify uncertain behavior when the
result changes the choice. Once it works, prefer explicit goals, observable
problems, and ready deferred work over minor polish. Material security, safety,
or operational risk may take priority throughout; cleanup needs a concrete
benefit.

Require only the chosen work's necessary decision inputs, not completed earlier
phases. If blocked, recommend the nearest decision that can be settled and name
what it unlocks. Surface material code/documentation conflicts without resolving
them. Use phase order only to break ties. If evidence supports no actionable
work, say so.

## Report

State the action, why now, the first concrete step, and the smallest observable
completion condition. Cite supporting evidence and applicable accepted decisions;
name uncertainty, unavailable evidence, or unread material that could change the
choice. Mention alternatives only when they clarify why this action wins. Keep
any prerequisite decision distinct from the work it blocks.
