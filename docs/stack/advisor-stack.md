# Stack

## Boundary

**Owns:** The selected technology inventory, versions, and technology defaults.
A shared selection has one project-level home; a selection used only by one
feature may live in that feature's Stack artifact.

**Includes:** Languages, runtimes, frameworks, databases, libraries, external
services, version constraints, dependency pinning, configuration conventions,
and supported versions. These are representative, not exhaustive.

**Excludes:** The architectural reason or topology established by a technology
choice, owned by Architecture; feature-specific implementation mechanics, owned
by Implementation; and the procedure that deploys it, owned by Deployment.

**Scope:** Shared rules live in `docs/stack/`; decisions applying only
to one feature live in `docs/features/<feature-slug>/stack/` and link to
shared rules instead of copying them. Stack has no phase of its own.
Screening in the [Architecture](../architecture/advisor-architecture-feature.md)
catalogs can trigger either scope; a direct decision within this boundary can
also start an artifact. Create the feature folder only when writing its first
artifact, never as an empty phase placeholder.

The demand-driven questions below serve both scopes. Read only the questions
the trigger makes relevant; accept the artifact against that need and its own
decisions, without requiring the unused catalog to be exhausted.

## How this authority develops

Follow this order when the trigger also introduces shared policy:

1. **Record the selected technology** — answer `stack-inventory` with its role
   and version so the project has one authoritative inventory.
2. **Record what its consumers inherit** — answer `stack-shared-defaults` for
   pinning, configuration, supported versions, and any other default whose
   departure must be explicit.

In compact form: **technology inventory → shared defaults**. A new inventory
entry does not require invented defaults, and a changed default may amend an
existing entry without selecting new technology. Accept the amended guidance
once the triggered Stack need is covered, then resume the feature.

## Questions

**1. `stack-inventory`**
Which languages, runtimes, frameworks, databases and external services does this
project use, and at which versions?

- *Decides:* what a new piece of work may reach for without asking.
- *Why it matters:* an inventory that is only in the lockfiles cannot be
  reasoned about, and a second library doing the same job enters unnoticed.

**2. `stack-shared-defaults`**
Which defaults does every component inherit — how dependencies are pinned, how
configuration reaches the process, which versions are supported?

- *Decides:* what a component has to state because it departs from the default.
- *Why it matters:* without a stated default there is no departure, only
  variation nobody decided on.
