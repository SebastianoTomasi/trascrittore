# Product feature catalog

Read [the Product boundary](advisor-product.md) before using this catalog.
This file contains only the progression and questions for the feature-scoped
Product phase.

## Feature-scoped Product phase

Usual inputs: the relevant accepted foundation decisions — project-scoped
Product and Architecture. Apply the
[common readiness rule](../advisor-docs.md#usual-phase-order-and-decision-readiness)
to the specific feature decision; the foundation may remain incomplete when
its open choices cannot invalidate that decision.

Work through the phase in this order:

1. **Bound the capability** — answer `feature-purpose` and
   `feature-non-goals` so the session knows which outcome belongs to this
   feature and which nearby outcome does not.
2. **Identify its participants and conditions** — answer `feature-actors`,
   `feature-data`, and `feature-preconditions` against the accepted Product
   foundation.
3. **State its observable contract** — answer `feature-outcomes` for both
   success and ordinary failure, without choosing a surface or implementation.
4. **Screen the changed product model** — ask
   `security-new-subject-or-data` after the actors and data are known.

In compact form: **capability boundary → actors, data, and preconditions →
observable outcomes → Product-level security screening**.

Steps 2 and 3 compose into one capability narrative — actor, precondition,
success outcome, ordinary failure outcome — written as a connected claim rather
than four independent facts. The narrative names no screen, component, or
mechanism: it is what the actor can achieve and what is true afterwards, and it
stays readable by someone who never sees the product. When accepted, this phase
leaves Frontend with a bounded capability and the observable contract it must
express; it does not yet prescribe screens or interaction steps.

**1. `feature-purpose`**
What can someone do once this feature exists that they could not do before?

- *Decides:* the boundary of the feature — what belongs to it and what is a
  different feature.
- *Why it matters:* a feature stated as a part of the system rather than as a
  capability grows until it is a subsystem, and nothing says when it is done.

**2. `feature-actors`**
Which of the project's actors take part in this feature, and does it introduce
one the Product description does not name?

- *Decides:* whose permissions and whose experience this feature concerns.
- *Why it matters:* an actor introduced here and not written into the
  project-scoped description is invisible to every other feature, and the trust
  boundaries drawn without it are wrong.

**3. `feature-data`**
Which classes of data does this feature touch, and does it introduce one the
Product description does not declare?

- *Decides:* whether this feature inherits existing obligations or creates new
  ones.
- *Why it matters:* a new class of data found at implementation time reopens
  storage, boundaries and retention after they are fixed.

**4. `feature-preconditions`**
What has to be true before this capability is available to the actor at all?

- *Decides:* what the feature may assume rather than check.
- *Why it matters:* an unstated precondition becomes an assumption in code, and
  the first caller that violates it fails in a way nobody predicted.

**5. `feature-outcomes`**
What observable result counts as success, and what does the actor see when it
does not succeed?

- *Decides:* what the feature promises, in terms someone outside it can check.
- *Why it matters:* the failure half is the half that gets designed by accident
  if it is not decided here.

**6. `feature-non-goals`**
Which nearby capability does this feature deliberately not include?

- *Decides:* what may be refused without reopening the feature.
- *Why it matters:* without it, scope grows by suggestion, and each addition
  looks reasonable on its own.

**7. `security-new-subject-or-data`** — *screening, owned by Security*
Does this feature introduce an actor, a subject, or a class of data that the
project's accepted Product description does not already declare?

- *Default:* dismiss — the feature uses actors and data classes already
  declared.
- *If it has substance:* update the owning Product rule at its actual scope;
  change the foundation only when the shared actor or data model changes. Write
  any new control in Security at project scope if shared, or feature scope if
  specific. Link the rule here and propagate changes to existing decisions.
- *Why it is asked now:* it is answerable from the Product statement alone, and
  asking later means the boundaries were drawn without it.
