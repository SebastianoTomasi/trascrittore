# Frontend feature catalog

Read [the Frontend boundary](advisor-frontend.md) before using this catalog.
This file contains only the progression and questions for the feature-scoped
Frontend phase.

## Feature-scoped Frontend phase

Usual inputs: this feature's accepted Product decisions. Apply the
decision-readiness rule in `docs/advisor-docs.md` to the specific interaction
being designed; unresolved Product choices must not be silently assumed.

Work through the phase in this order:

1. **Decide applicability** — answer `frontend-surface-exists`. A negative
   answer supports closing the phase through `frontend/absent.md` after the
   [absence contract](../features/advisor-features.md#a-phase-with-no-decisions).
2. **Make the capability reachable** — answer `frontend-entry-points` before
   detailing a journey that the actor might otherwise have no way to start.
3. **Define the client-visible path** — answer `frontend-interaction-steps` as
   the ordered on-screen route from entry to the outcome Product promised.
4. **Complete every reachable condition** — answer `frontend-states` and
   `frontend-input-rules` for waiting, empty, partial, failed, and rejected
   input paths as well as the happy path.

In compact form: **surface applicability → entry points → client-visible path
→ states and input rules**. When accepted, this phase leaves Architecture with approved
client-visible behavior to support. It does not choose components, interfaces,
or storage.

**1. `frontend-surface-exists`**
Does this feature have any client-visible surface?

- *Decides:* whether this phase has substance at all.
- *Why it matters:* a negative answer supplies the basis for dismissing the
  surface questions. Verify and record every dismissal through the
  [phase absence contract](../features/advisor-features.md#a-phase-with-no-decisions)
  before accepting `frontend/absent.md`.

**2. `frontend-entry-points`**
Where does the actor reach this capability from, and how do they know it is
there?

- *Decides:* what has to change in surfaces that already exist.
- *Why it matters:* a capability with no entry point is built and never found,
  and the omission is invisible in the feature's own documents.

**3. `frontend-interaction-steps`**
What sequence does the actor go through, and what do they see at each step?

- *Decides:* the client-visible behavior the architecture then has to support.
- *Why it matters:* this is the step where the product statement becomes
  specific enough to be wrong, which is the point of putting Frontend before
  Architecture.

**4. `frontend-states`**
What does the actor see while it is pending, when there is nothing yet, when
there is partial data, and when it has failed?

- *Decides:* the states the client must represent.
- *Why it matters:* these four are the states that are never specified and
  always reached, and each one invented at implementation time contradicts the
  others.

**5. `frontend-input-rules`**
What does the client accept and reject before anything leaves it?

- *Decides:* which rules are duplicated for the actor's benefit and which are
  enforced only where they are authoritative.
- *Why it matters:* a client rule mistaken for the authoritative one leaves the
  real boundary unguarded.
