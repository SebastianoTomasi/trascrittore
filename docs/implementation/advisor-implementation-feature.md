# Implementation feature catalog

Read [the Implementation boundary](advisor-implementation.md) before using this
catalog.
This file contains only the progression and questions for the feature-scoped
Implementation phase.

## Feature-scoped Implementation phase

Usual inputs: this feature's accepted Architecture contracts and the Product
and Frontend decisions they realize. Apply the decision-readiness rule in
`docs/advisor-docs.md`; whole-phase completion is not a prerequisite for every
internal design choice.

Work through the phase in this order:

1. **Realize data and interfaces** — answer `feature-persistence` and
   `feature-endpoints` from the ownership and semantic interfaces Architecture
   fixed.
2. **Choose the non-obvious mechanics** — answer `feature-internal-state`,
   `feature-algorithms`, `feature-external-adapters`, and `feature-jobs` where
   the code alone would not preserve the reasoning, failure mechanics, or
   unattended execution model.
3. **Screen delivery readiness** — ask `development-new-test-need`,
   `deployment-new-delivery-need`, and `operations-new-runtime-need` against the
   realization as the relevant mechanics become known. Place new guidance at
   project or feature scope according to what it governs.

In compact form: **persistence and interfaces → state, algorithms, adapters,
and jobs → Development, Deployment, and Operations screening**. When accepted,
this phase leaves implementation with its concrete non-obvious design decisions and
with delivery or runtime decisions in their owning authority and actual scope.
The questions apply to clients, servers, local applications, CLIs, and jobs;
they require significant design reasoning, not a complete description of code.
Consider client history, local caches, and in-memory state where applicable.

**1. `feature-persistence`**
What does this feature store, where, and what change to existing storage does it
require?

- *Decides:* the concrete shape of the data and the migration it implies.
- *Why it matters:* a migration is the part of a feature most likely to be
  irreversible, and the first place a wrong ownership decision becomes
  expensive.

**2. `feature-endpoints`**
Which concrete interfaces does this feature expose, and in what shape?

- *Decides:* the realization of the promises Architecture fixed.
- *Why it matters:* code and generated interface descriptions stay
  authoritative for exact signatures; what belongs here is what a reader could
  not recover from them.

**3. `feature-algorithms`**
Is there a computation here whose correctness is not obvious from reading the
code?

- *Decides:* what has to be written down so the code can later be changed
  safely.
- *Why it matters:* the reasoning behind a non-obvious algorithm is lost first
  and needed most.

**4. `feature-external-adapters`**
Which external services does this feature call, and what does it do concretely
about timeouts, retries and partial failure?

- *Decides:* the mechanics that realize the failure behavior Architecture
  decided.
- *Why it matters:* Architecture fixed what is permitted; if the concrete values
  are never chosen deliberately, the library defaults choose them.

**5. `feature-jobs`**
Does this feature introduce background, scheduled, or deferred work?

- *Decides:* whether anything runs outside the primary interaction or execution
  path and therefore needs its own failure handling.
- *Why it matters:* work that runs unattended fails unattended.

**6. `development-new-test-need`** — *screening, owned by Development*
Does this feature need a kind of test that the project's Development document
does not already describe?

- *Default:* dismiss — the existing kinds of test cover it.
- *If it has substance:* write Development guidance at project scope if shared,
  or in this feature's `development/` folder if specific. Link it here.

**7. `deployment-new-delivery-need`** — *screening, owned by Deployment*
Does this feature require a new environment, deployment artifact, migration
step, or release procedure that the project's Deployment document does not
already describe?

- *Default:* dismiss — it ships by the existing procedure.
- *If it has substance:* write the Deployment decision at project scope if shared,
  or in this feature's `deployment/` folder if specific, and link it here.
  A deferred item is for later work, not a substitute for a decision needed now.

**8. `operations-new-runtime-need`** — *screening, owned by Operations*
Does this feature need monitoring, alerting, backup, or a manual procedure that
the project's Operations document does not already describe?

- *Default:* dismiss — existing operational coverage applies.
- *If it has substance:* write the Operations decision at project scope if shared,
  or in this feature's `operations/` folder if specific, and link it here.
  A deferred item is for later work, not a substitute for a decision needed now.

**9. `feature-internal-state`**
Does this feature need a non-obvious internal state representation or update
mechanism, such as document history, a local cache, or coordinated in-memory
state?

- *Decides:* the significant representation and update choices inside a unit,
  with the reasoning needed to preserve correctness when the code changes.
- *Why it matters:* visible behavior and cross-unit contracts do not determine
  whether a client stores snapshots, inverse operations, or another internal
  model. Dismiss explicitly when no significant choice needs documentation.
