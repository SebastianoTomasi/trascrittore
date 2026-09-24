# Operations

## Boundary

**Owns:** The procedures for running and recovering the system in production.

**Includes:** Runtime signals, thresholds, dashboards, alerts, responder
ownership, operational runbooks, backup, restore, and evidence that recovery
works, including a manual procedure to recover one feature's interrupted CSV
import. These are representative, not exhaustive.

**Excludes:** Getting a change into production, owned by Deployment;
implementation mechanics, owned by Implementation; and development-time tests, owned
by Development or code.

**Scope:** Shared rules live in `docs/operations/`; decisions applying only
to one feature live in `docs/features/<feature-slug>/operations/` and link to
shared rules instead of copying them. Operations has no phase of its own.
Screening in the [Implementation](../implementation/advisor-implementation-feature.md)
catalogs can trigger either scope; a direct decision within this boundary can
also start an artifact. Create the feature folder only when writing its first
artifact, never as an empty phase placeholder.

The demand-driven questions below serve both scopes. Read only the questions
the trigger makes relevant; accept the artifact against that need and its own
decisions, without requiring the unused catalog to be exhausted.

## How this authority develops

Build the operating loop in this order when both questions have substance:

1. **Detect and route failure** — answer `operations-monitoring` with the
   signals, thresholds, alerts, and responsible responder that make a runtime
   condition actionable.
2. **Recover service and state** — answer `operations-recovery` with backup,
   restore, and proof that recovery works for the state the feature can affect.

In compact form: **detection and alerting → recovery and restoration**. The two
questions may also be triggered independently; do not create the other answer
only to make the sequence look complete. Accept the amended guidance once the
triggered runtime need is covered, then resume the feature.

## Questions

**1. `operations-monitoring`**
What is watched while the system runs, and what raises an alert someone acts on?

- *Decides:* which failures are noticed by the system rather than by a user.
- *Why it matters:* anything not watched is reported by whoever it hurt, at the
  time it hurt them.

**2. `operations-recovery`**
What is backed up, how is it restored, and when was that last shown to work?

- *Decides:* what survives the worst outcome.
- *Why it matters:* a backup that has never been restored is a belief, not a
  procedure.
