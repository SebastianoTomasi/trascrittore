# Frontend project catalog

Read [the Frontend boundary](advisor-frontend.md) before using this catalog.
This file contains only the progression and questions for project-scoped
Frontend work.

## How this authority develops

Frontend is demand-driven rather than a phase at project scope. A feature first
settles its own client-visible behavior in the feature Frontend phase. When that
work reveals a rule that should hold for later features, use this order:

1. **Fix the medium** — answer `frontend-default-surface` so shared behavior has
   a known kind of client and runtime surface.
2. **Fix the shared interaction language** — answer
   `frontend-shared-interaction-rules` for navigation, waiting, errors, and
   other behavior every such surface inherits.

In compact form: **default surface → shared interaction rules**. Start only with
the question the feature triggered; do not manufacture the other answer merely
to complete this sequence. If both have substance, the surface comes first
because the shared rules need to say where they apply. Accept the new or amended
project-scoped artifact once the triggered question is addressed, then resume
the feature that exposed the need.

## Questions

**1. `frontend-default-surface`**
What kind of client does this product present, and on what does it run?

- *Decides:* what every feature's surface can assume about its medium.
- *Why it matters:* a second kind of client added later changes what
  client-visible behavior means for every feature already accepted.

**2. `frontend-shared-interaction-rules`**
Which rules does every surface follow — how errors are shown, how waiting is
shown, how the actor moves between places?

- *Decides:* what a feature's Frontend document may leave unsaid.
- *Why it matters:* without shared rules each feature invents its own, and the
  product is inconsistent in exactly the way the actor notices first.
