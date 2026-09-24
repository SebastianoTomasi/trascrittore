# Development

## Boundary

**Owns:** Development workflow and test guidance, shared or specific to a feature.

**Includes:** Branching, review, pre-merge checks, test kinds, their intended
coverage, and shared evidence expected from a change. These are representative,
not exhaustive.

**Excludes:** Individual test implementations and facts recoverable from code;
production operation, owned by Operations; and release procedure, owned by
Deployment. Test guidance belongs here or in code, never in a separate quality
authority.

**Scope:** Shared rules live in `docs/development/`; decisions applying only
to one feature live in `docs/features/<feature-slug>/development/` and link to
shared rules instead of copying them. Development has no phase of its own.
Screening in the [Implementation](../implementation/advisor-implementation-feature.md)
catalogs can trigger either scope; a direct decision within this boundary can
also start an artifact. Create the feature folder only when writing its first
artifact, never as an empty phase placeholder.

The demand-driven questions below serve both scopes. Read only the questions
the trigger makes relevant; accept the artifact against that need and its own
decisions, without requiring the unused catalog to be exhausted.

## How this authority develops

Follow this order when both questions have substance:

1. **Define the path a change must pass** — answer `development-workflow` for
   branching, review, and the checks required before merge.
2. **Define the evidence those checks require** — answer
   `development-test-strategy` for the distinct test kinds and the risks each
   one covers.

In compact form: **change workflow → test evidence**. A new test need can amend
the strategy without reopening a workflow that already accommodates it. Accept
the amended guidance once the triggered need is covered, then resume the
feature.

## Questions

**1. `development-workflow`**
How does a change travel from written to merged — branching, review, and what
must pass first?

- *Decides:* the gate every change goes through.
- *Why it matters:* an unstated workflow is followed differently by each
  contributor, including the same one at different times.

**2. `development-test-strategy`**
Which kinds of test exist in this project, and what does each kind cover that
the others do not?

- *Decides:* which test a new piece of work owes.
- *Why it matters:* without stated coverage, tests accumulate where they are
  easy to write rather than where they are needed.
