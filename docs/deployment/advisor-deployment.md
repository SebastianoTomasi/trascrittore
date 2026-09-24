# Deployment

## Boundary

**Owns:** The procedures by which a change is delivered and deployed.

**Includes:** Environment paths, packaging and delivery steps, release
verification, migrations as release steps, rollback, and recovery from a failed
deployment. These are representative, not exhaustive.

**Excludes:** Running and recovering the deployed system, owned by Operations;
implementation mechanics, owned by Implementation; and delivery status, owned by the
task system.

**Scope:** Shared rules live in `docs/deployment/`; decisions applying only
to one feature live in `docs/features/<feature-slug>/deployment/` and link to
shared rules instead of copying them. Deployment has no phase of its own.
Screening in the [Implementation](../implementation/advisor-implementation-feature.md)
catalogs can trigger either scope; a direct decision within this boundary can
also start an artifact. Create the feature folder only when writing its first
artifact, never as an empty phase placeholder.

The demand-driven questions below serve both scopes. Read only the questions
the trigger makes relevant; accept the artifact against that need and its own
decisions, without requiring the unused catalog to be exhausted.

## How this authority develops

Follow this order when both questions have substance:

1. **Map the route to production** — answer `deployment-environments` so the
   places a change crosses and the mechanism that moves it are explicit.
2. **Make that route repeatable and reversible** — answer
   `deployment-release-procedure` with the ordered release, verification, and
   rollback procedure for those environments.

In compact form: **environment path → release and rollback procedure**. This is
not a new phase and does not require an environment inventory when the trigger
only changes an already documented release procedure. Amend the triggered
answer, accept it once the new delivery need is covered, and resume the feature.

## Questions

**1. `deployment-environments`**
Which environments exist, and how does a change reach each one?

- *Decides:* what "released" means and how many steps precede it.
- *Why it matters:* an environment that exists but is undocumented drifts from
  the others, and the drift is discovered by a deployment that behaves
  differently.

**2. `deployment-release-procedure`**
What are the steps of a release, and how is one undone?

- *Decides:* what happens when a release turns out to be wrong.
- *Why it matters:* rollback improvised during an incident is rollback designed
  under the worst possible conditions.
