# Architecture project catalog

Read [the Architecture boundary](advisor-architecture.md) before using this
catalog.
This file contains only the progression and questions for project-scoped
Architecture work.

The questions below are the Architecture half of the foundation. Each decision
uses the accepted Product inputs it needs. Apply the
[common readiness rule](../advisor-docs.md#usual-phase-order-and-decision-readiness)
to Architecture and feature decisions even while foundation coverage is
incomplete. The slug is the question's identity and is what a dismissal cites;
the number is presentation order only. A question with no substance here is
dismissed by name in one explicit line.

## How the foundation progresses

Work through the Architecture foundation in this dependency order:

1. **Set the context** — answer `system-boundary` to separate what this project
   owns from the systems it only talks to.
2. **Decompose the system** — answer `components`, then
   `component-dependencies`. Responsibilities have to exist before a permitted
   or forbidden dependency between them can be stated precisely.
3. **Place state and trust** — answer `data-ownership`, then
   `trust-boundaries`. This applies Product's actors, subjects, and data classes
   to components that can own, read, write, or isolate them.
4. **Define runtime contracts** — answer `cross-system-flows`, then
   `consistency-boundaries`. First state what crosses a boundary and what it
   promises; then state which intermediate observations those flows may expose.
5. **Define the bad path** — answer `failure-and-degradation` against those
   dependencies and flows, including which degraded results still count as
   working.

In compact form: **system context → components and dependencies → ownership and
trust → flows and consistency → failure and degradation**. This is a decision
sequence, not a required document layout. Keep related answers together when
that makes the contracts easier to read, and return to an earlier step if a
later one exposes a missing component, owner, or boundary.

The Architecture foundation is complete when compatible accepted artifacts
cover all eight questions below with answers or explicit dismissals and no
necessary input remains unresolved. Together, those decisions give features a
stable system boundary, a place for the work to land, rules for dependency and
ownership, and the cross-system, consistency, trust, and failure contracts they
must apply rather than reinvent.

## Questions

**1. `system-boundary`**
What is inside this system, and which systems does it talk to without owning?

- *Decides:* what the project may change and what it must treat as given.
- *Why it matters:* a dependency mistaken for a component gets redesigned;
  a component mistaken for a dependency never gets designed at all.

**2. `components`**
Which components exist, and what is each one responsible for — stated so that
two plausible responsibilities could not both be true?

- *Decides:* where a new piece of work lands.
- *Why it matters:* if responsibilities overlap, the same rule is enforced in
  two places and drifts; if they leave a gap, it is enforced nowhere and the
  gap is found in production.

**3. `component-dependencies`**
Which component may depend on which, and which direction is forbidden?

- *Decides:* whether a component can be reasoned about, tested, or replaced on
  its own.
- *Why it matters:* dependency direction is cheap to state now and expensive to
  reverse later, because by then code encodes it in both directions.

**4. `data-ownership`**
Which component owns each piece of conceptual data, and who is allowed to write
it?

- *Decides:* where an invariant over that data can be enforced at all.
- *Why it matters:* data with two writers has no enforceable invariant, and the
  resulting corruption is discovered by its consequences rather than by a
  failure.

**5. `trust-boundaries`**
Where does a boundary run between the actors and subjects Product named, and by
what mechanism is one kept from reaching another's data?

- *Decides:* the isolation the system actually provides, as opposed to the one
  it assumes.
- *Why it matters:* this is one of the three early security concerns and it is
  Architecture's. A boundary added after components exist means changing what
  every component is allowed to see.

**6. `cross-system-flows`**
Which flows cross the system boundary, and what does each guarantee to the
system on the other side?

- *Decides:* what an integrator may rely on.
- *Why it matters:* an unstated guarantee is still relied upon; it is simply
  relied upon by guesswork, and broken without anyone noticing which promise
  was broken.

**7. `consistency-boundaries`**
Where is an operation atomic, and what may a reader observe part-way through
one that is not?

- *Decides:* the states the rest of the system must be able to tolerate.
- *Why it matters:* an intermediate state that nobody decided to permit is
  still reachable. Deciding it here makes it a contract; leaving it makes it a
  bug report.

**8. `failure-and-degradation`**
When a dependency this system needs is unavailable, what does it do, and which
degraded result is permitted rather than an error?

- *Decides:* what "working" means when not everything is working.
- *Why it matters:* the default answer is whatever the code happens to do,
  which is discovered during the first outage instead of before it.
