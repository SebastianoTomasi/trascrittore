# Development

## Boundary

**Owns:** Development workflow and test guidance, shared or specific to a
feature, and the coding standards of the repository.

**Includes:** Branching, review, pre-merge checks, test kinds, their intended
coverage, shared evidence expected from a change, and the conventions the
repository's code follows. These are representative, not exhaustive.

**Excludes:** Individual test implementations and facts recoverable from code;
production operation, owned by Operations; and release procedure, owned by
Deployment. Test guidance belongs here or in code, never in a separate quality
authority.

**Scope:** Shared rules live in `docs/development/`; decisions applying only
to one feature live in `docs/features/<feature-slug>/development/` and link to
shared rules instead of copying them. The coding standards hold for every
change, so they are one project-scoped document and no feature has its own.
Development has no phase of its own.
Screening in the [Implementation](../implementation/advisor-implementation-feature.md)
catalogs can trigger either scope; a direct decision within this boundary can
also start an artifact. Create the feature folder only when writing its first
artifact, never as an empty phase placeholder.

The demand-driven questions below serve both scopes, except
`development-coding-standards`, which is answered at project scope only. Read
only the questions the trigger makes relevant; accept the artifact against that
need and its own decisions, without requiring the unused catalog to be
exhausted.

## How this authority develops

Follow this order when several questions have substance:

1. **Define the path a change must pass** — answer `development-workflow` for
   branching, review, and the checks required before merge.
2. **Define the evidence those checks require** — answer
   `development-test-strategy` for the distinct test kinds and the risks each
   one covers.
3. **State what the code is held to** — answer `development-coding-standards`
   for what is particular to this repository's code, which the review the
   workflow defines checks a change against.

In compact form: **change workflow → test evidence → coding standards**. A new
test need can amend the strategy without reopening a workflow that already
accommodates it. Accept the amended guidance once the triggered need is
covered, then resume the feature. The coding standards rest on neither earlier
answer and no screening question asks for them: they are written when
[their own trigger](#the-coding-standards-document) occurs, which can be before
the other two exist.

## Questions

**1. `development-workflow`**
How does a change travel from written to merged — branching, review, and what
must pass first?

- *Decides:* the gate every change goes through.
- *Why it matters:* an unstated workflow is followed differently by each
  contributor, including the same one at different times.

**2. `development-test-strategy`**
Which kinds of test exist in this project, and what does each kind cover that
the others do not?

- *Decides:* which test a new piece of work owes.
- *Why it matters:* without stated coverage, tests accumulate where they are
  easy to write rather than where they are needed.

**3. `development-coding-standards`**
What is particular to the way code is written in this repository, that whoever
writes or reviews a change needs and cannot learn from its tooling or from the
documents that own its design?

- *Decides:* what a review may hold a change to beyond its ticket and its
  checks.
- *Why it matters:* a convention nobody wrote down is argued again at every
  review, and a change that departs from it cannot be told from one whose
  author never knew it.

## The coding standards document

The answer to `development-coding-standards` is one artifact,
`docs/development/CODING_STANDARDS.md`. Its name and place are fixed because
review tools look for a file of that name; under a name the project chose, its
reviews would run without it. It is the project's own document, with the usual
status line, Scope, and Dependencies, and no advisor release delivers or
replaces it.

It is read by whoever writes a change and whoever reviews one, so it is worth
only what it adds to what they already have. It holds what is particular to
this repository, which is of three kinds.

The first is the stage the project is in and what that means for its code,
above all whether backward compatibility is kept: the same rename is a
complete change in a project nothing depends on yet and a breaking one in a
project with users. Where an accepted Product document already states what the
product promises not to break, link to it and say only what follows for the
code.

The second is the repository's own conventions: choices about how its code is
written that hold across features and that no other authority owns, such as
the unit a quantity is measured in, the language and vocabulary of
identifiers, or a generated file that is regenerated instead of edited.

The third is a reminder, one line each, of the rules other accepted documents
own that show in a diff, such as a module boundary or what a log line may
carry. Each line links to the passage that owns the rule, and that passage is
listed under Dependencies. The owning document stays the authority and wins
where the two differ: the line is there so a reviewer reading a diff meets the
rule, and the reasoning stays in one place.

What it leaves out follows from the same aim. Standards a team keeps for all
its repositories stay where the team keeps them, since a copy here would drift
from the original and bury the few lines that belong to this repository alone.
What the formatter, the linter, the type checker, or the tests already decide
needs no sentence, because the tool enforces it without being read. What the
product must do belongs to the ticket and the feature's documents.

Write it when there is something to record, not at project start: a convention
set down before the code has asked for it is a guess that every later review
must then read. Two events call for it. One is a session settling a convention
for the code. The other is a review raising a point that an earlier review
already raised and the document does not state: a single finding is corrected
in its change, while a repeated one shows that reviews rely on something
unwritten. Start the document with that convention, or amend it, and accept it
once the triggering convention is stated; it grows one settled convention at a
time and is never owed a complete account.
