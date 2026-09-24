---
name: advisor-next-work
description: Assess a guided project's current state and recommend what product, decision, design, implementation, or other delivery work is worth doing next. Use when the user asks for the current position, what to decide or work out next, or which work to prioritize; do not use when the user has already chosen a concrete task or asks to conduct a documentation session.
disable-model-invocation: false
---

# Next-work advice

Choose and explain one useful next action without performing it. This is a
read-only assessment: do not write project files, start an interview, implement
the recommendation, create a flag or reminder, or treat the advice as permission.
After reporting, stop and let the user's chosen action route as a new request.

## Establish the current state

Invoke `advisor-defer` first to recover relevant deferred items. For a general
request, consider every open record; for scoped work, include applicable shared
and unclassified records as well as those already routed to the scope. Let that
skill own recovery and classification. Advice does not change the records.

Use the shared reading guidance in `advisor-agents.md` and the common rules in
`docs/advisor-docs.md`. For a general request, list project authority and feature
folders and inspect every artifact's routing envelope before selecting bodies.
For a scoped request, inspect that scope, shared prerequisites, and other evidence
that can change its readiness. Read relevant Dependencies, Review blocks,
decision passages, and catalog questions. Use the feature router for phase routes.
Do not infer readiness or coverage from folders, filenames, or markers.

Assess implemented state when it can change the recommendation. Inspect relevant
code and existing tests, and run a safe focused verification when practical.
Code establishes what is implemented; accepted documentation establishes settled
intent, not implementation. Name the evidence and disclose checks or coverage
that remain unverified. If code and documentation materially contradict one
another, preserve both, explain the discrepancy, and recommend clarification as
a prerequisite when it blocks a sound choice. This skill does not resolve it.

## Select the recommendation

Consider ready decisions, implementation slices, repairs, explicit user goals,
relevant deferred work, and focused improvements. A candidate is ready when its
necessary accepted decision inputs suffice and remaining open choices cannot
invalidate it. An implementation slice does not require a complete earlier phase;
require only the accepted decisions and applicable constraints that could change
or invalidate that slice.

Prioritize a working product before optional polish:

1. If the primary user journey is not supported by concrete implementation
   evidence, recommend the smallest end-to-end slice that makes it work while
   satisfying established Product behavior and applicable constraints.
2. If that slice lacks a necessary decision, recommend the nearest decision that
   can be settled now and explain what it unlocks.
3. Once the primary journey works, prefer explicit user goals, broken or
   incomplete observable behavior, and ready deferred work over minor improvements.
4. Let a material security, safety, or operational risk take priority at either
   stage. Do not recommend speculative cleanup without an observable, reliability,
   safety, or delivery benefit.

Recommend exactly one action and state why it outranks the other ready candidates.
Name materially useful alternatives and why they are secondary. Use the usual
phase order only to break otherwise equivalent choices. If no actionable work is
supported by the evidence, say so instead of inventing a recommendation.

## Report

State the recommended outcome, its accepted basis, relevant implementation
evidence, unresolved uncertainty, and the smallest concrete boundary of the
work. When relevant, distinguish a ready decision from whole-phase coverage and
identify the nearest blocker separately from the work it blocks. Cite the files
and passages supporting documentation-derived conclusions and disclose relevant
material left unread.
