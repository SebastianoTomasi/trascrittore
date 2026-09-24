# Product project catalog

Read [the Product boundary](advisor-product.md) before using this catalog.
This file contains only the progression and questions for project-scoped
Product work.

The questions below are the Product half of the foundation. They define shared
decisions for the project. Use the
[common readiness rule](../advisor-docs.md#usual-phase-order-and-decision-readiness)
to select work whose necessary inputs are accepted, including Architecture or
feature decisions before this catalog is fully covered. A question with no
substance is dismissed explicitly by its slug; silence is not an answer.

## How the foundation progresses

Work through the Product foundation in this dependency order:

1. **Frame the product** — answer `product-purpose` and `primary-user` so every
   later choice has a purpose and a known reader, actor, or beneficiary.
2. **Name the parties and constraints** — answer `actors-and-subjects`, then
   `data-classes`, then `legal-and-privacy-obligations`. The parties reveal
   whose data and interests exist; the data classes reveal which obligations
   can apply.
3. **Draw the observable scope** — answer `observable-capabilities`, then
   `non-goals`. Together they say what can become a feature and where the
   product deliberately stops.
4. **Make the promise stable and checkable** — answer
   `compatibility-baseline`, then `success-criteria`. These fix what later work
   must preserve and how the product claim can be tested from outside.

In compact form: **purpose and user → parties, data, and obligations →
capabilities and non-goals → compatibility and success**. This is a decision
sequence, not a required set of filenames: one artifact may cover several
steps, or several artifacts may cover one, as long as every question is
addressed. Screen-level interaction steps do not belong in this foundation;
they become answerable for a concrete feature in its Frontend phase.

The Product foundation is complete when compatible accepted artifacts cover
all nine questions below with answers or explicit dismissals and no necessary
input remains unresolved. Together, those decisions give Architecture the
product boundary, actors and subjects, constrained data, observable capabilities,
non-goals, compatibility promises, obligations, and external success criteria.

## Questions

**1. `product-purpose`**
What is this product for, and who is worse off if it does not exist?

- *Decides:* the boundary against which every later judgement of scope is made.
- *Why it matters:* without it each feature argues its own relevance from
  scratch, and a non-goal cannot be stated because there is nothing to be
  outside of.

**2. `primary-user`**
Who uses this product, in what role, and what can be assumed about what they
already know and already have?

- *Decides:* how much the product must explain, carry, or set up on the user's
  behalf.
- *Why it matters:* a product for one informed person and a product for many
  unknown ones differ in almost every later decision, and the difference is
  invisible unless it is written down first.

**3. `actors-and-subjects`**
Which distinct actors act on this system, and whose data or interests does it
hold on behalf of someone who is not the actor?

- *Decides:* the parties the system must tell apart, and therefore where
  isolation has to exist at all.
- *Why it matters:* trust boundaries are drawn in Architecture but they are
  drawn *between* these parties. Naming them late means drawing the boundaries
  twice.

**4. `data-classes`**
Which classes of data does the product handle, and which of them are personal,
regulated, or otherwise not free to move?

- *Decides:* which later work is constrained by an obligation rather than by a
  preference.
- *Why it matters:* a class discovered after the architecture is fixed
  reopens storage, boundaries, and retention at once. This is one of the three
  early security concerns, and it is Product's, not Security's.

**5. `observable-capabilities`**
What can someone do with this product, stated as capabilities a user could
observe rather than as parts of a system?

- *Decides:* the material from which features are carved.
- *Why it matters:* a feature is a user-observable capability. If capabilities
  were never enumerated, features get invented from the implementation and stop
  being units the user recognizes.

**6. `non-goals`**
What nearby thing does this product deliberately not do?

- *Decides:* what may be refused without further argument.
- *Why it matters:* a non-goal that is only understood, never written, is
  reopened by every conversation and eventually built.

**7. `compatibility-baseline`**
What does this product promise not to break, and for whom?

- *Decides:* which later changes are ordinary and which are breaking.
- *Why it matters:* without a stated baseline, "breaking" is decided
  case by case and after the fact, which is when it is most expensive.

**8. `legal-and-privacy-obligations`**
Which external obligations bind this product — legal, regulatory, contractual —
and what does each require it to do or refrain from?

- *Decides:* the requirements that are not negotiable and cannot be traded
  against effort.
- *Why it matters:* an obligation found late is not a feature request; it
  invalidates decisions already accepted.

**9. `success-criteria`**
How would someone check, from outside, that this product does what it claims?

- *Decides:* what "done" means for the product as a whole.
- *Why it matters:* a criterion that cannot be checked from outside cannot
  settle a disagreement, which is the only moment it is needed.
