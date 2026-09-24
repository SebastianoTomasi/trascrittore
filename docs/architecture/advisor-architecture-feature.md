# Architecture feature catalog

Read [the Architecture boundary](advisor-architecture.md) before using this
catalog.
This file contains only the progression and questions for the feature-scoped
Architecture phase.

## Feature-scoped Architecture phase

Usual inputs: this feature's accepted Product and Frontend decisions, and the
accepted project-scoped Architecture shape. Apply the decision-readiness rule
in `docs/advisor-docs.md`: an export format can be designed while its launch
screen is open if the accepted content and export rules suffice and the open
interaction choices cannot invalidate the contract.

Work through the phase in this order:

1. **Place the change** — answer `feature-components` against the accepted
   system decomposition.
2. **Place contracts and state** — answer `feature-interfaces`, then
   `feature-data-ownership`, so promises have participants and mutable data has
   one writer.
3. **Define correctness across time** — answer `feature-invariants`, then
   `feature-consistency`, including duplicate, retry, and intermediate-state
   semantics.
4. **Protect behavior under change and failure** — answer
   `feature-failure-behavior` and `feature-compatibility` against the Product
   and Frontend promises already accepted.
5. **Screen the resulting design** — ask `security-new-trust-crossing` and
   `stack-new-technology` only after the boundaries and required technology are
   visible.

In compact form: **component placement → interfaces and ownership → invariants
and consistency → failure and compatibility → Security and Stack screening**.
When accepted, this phase leaves Implementation with implementation-independent
contracts and failure semantics to realize, without prescribing private code
structure.

**1. `feature-components`**
Which existing components does this feature change, and does a new one appear?

- *Decides:* where the work lands and what its blast radius is.
- *Why it matters:* a new component decided during implementation is a
  component nobody assigned a responsibility to.

**2. `feature-interfaces`**
Which semantic interfaces are added or changed, and what does each promise to
its caller?

- *Decides:* what other work may rely on once this feature is done.
- *Why it matters:* the promise is the part that outlives the implementation,
  and it is the part that is never written unless it is asked for.

**3. `feature-data-ownership`**
Which component owns the data this feature introduces, and who may write it?

- *Decides:* where this feature's invariants can be enforced.
- *Why it matters:* the project-scoped rule fixed the principle; this is where
  it is applied, and where a second writer would be introduced unnoticed.

**4. `feature-invariants`**
What must stay true regardless of the order in which operations arrive, or of
the same one arriving twice?

- *Decides:* the duplicate and retry semantics this feature carries.
- *Why it matters:* retries happen whether or not they were designed for, and a
  duplicate effect is discovered by its consequences.

**5. `feature-consistency`**
This feature's application of the project's consistency rule: is the operation
atomic, and what may be observed part-way through if it is not?

- *Decides:* the intermediate states the rest of the system must tolerate.
- *Why it matters:* the project-scoped question fixed the rule. This one asks
  this feature's application or its derogation, and never restates the rule.

**6. `feature-failure-behavior`**
When a dependency this feature needs is unavailable, what does it do, and which
degraded result is permitted?

- *Decides:* what the feature does on its worst ordinary day.
- *Why it matters:* left undecided, the answer is whatever the code happens to
  do, and the Frontend document has already promised the actor something.

**7. `feature-compatibility`**
Does this feature change anything the project's compatibility baseline promised
not to break?

- *Decides:* whether this is an ordinary change or a breaking one.
- *Why it matters:* the answer determines what else must happen before release,
  and it is cheapest to know before the interface is built.

**8. `security-new-trust-crossing`** — *screening, owned by Security*
Does this feature let data or an action cross a trust boundary in a way the
accepted Architecture shape does not already permit?

- *Default:* dismiss — the feature stays within existing boundaries.
- *If it has substance:* settle the Architecture boundary and any Security
  control in their owning artifacts, at project scope if shared or feature scope
  if specific. Link the Security answer here and propagate changes to accepted
  rules. Use a deferred item only for work that is not required by the current
  decision.
- *Why it is asked now:* the feature's boundaries exist only from this phase
  onward, and asking at Implementation delivers the finding after the design is fixed.

**9. `stack-new-technology`** — *screening, owned by Stack*
Does this feature require a technology, library, or external service that the
project's Stack document does not already list?

- *Default:* dismiss — the feature uses what is already there.
- *If it has substance:* update the shared Stack inventory, or create a
  feature-scoped Stack selection if only this feature uses it. Link it here;
  never maintain two authoritative entries for the same selection.
- *Why it is asked now:* a technology required by a contract must be recorded
  before its consumers assume it, with its actual scope and owner.
