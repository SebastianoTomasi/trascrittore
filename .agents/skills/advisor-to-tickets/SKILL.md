---
name: advisor-to-tickets
description: Prepare relevant advisor documents and constraints, then use the separately installed to-tickets skill to draft and publish implementation tickets from a plan, spec, conversation, or feature.
---

# Advisor ticket production

Use this skill when a guided project asks the advisor for implementation
tickets. `to-tickets` is an external dependency installed separately. If it
is unavailable, explain how to install it and stop before inventing a parallel
ticket procedure. Read the target project's
`docs/agents/issue-tracker.md` and `docs/agents/triage-labels.md`; if either
is missing, ask for `setup-matt-pocock-skills` and stop.

Recover relevant `advisor:deferred` issues through `advisor-defer` before
assessing a feature's work. Use `advisor-agents.md` and `docs/advisor-docs.md`
to read the requested plan, specification, conversation, or feature documents,
plus accepted shared constraints, relevant ADRs, and applicable code evidence.
Give `to-tickets` the source and this relevant context. A proposed document
does not become an accepted constraint; identify open choices that affect the
requested work and ask the user or use choices they explicitly delegate.
Do not demand whole-phase completion when the requested slice has sufficient
accepted inputs.

Read and follow the installed `to-tickets/SKILL.md` for the breakdown,
dependency edges, user review, and publication. Its tracker and label rules
govern implementation tickets. Do
not add `advisor:deferred` to them merely because they concern future
implementation; that label is for advisor recovery of deferred questions and
ideas. Do not close or modify a source issue through this composition.

The same feature may produce further tickets from later plans or changes.
Inspect relevant existing tickets to avoid accidental duplicates, then let
`to-tickets` present and publish the new approved breakdown. The advisor
does not maintain its own ticket set, ticket status, or publication procedure.
