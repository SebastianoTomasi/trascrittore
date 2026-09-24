# Implementation project catalog

Read [the Implementation boundary](advisor-implementation.md) before using this
catalog.
This file contains only the progression and questions for project-scoped
Implementation work.

## How this authority develops

Implementation is demand-driven rather than a phase at project scope. A feature
defines its own concrete realization in its Implementation phase. When that work
reveals a rule that should hold across features, use this order when both
questions have substance:

1. **Fix the shared execution conventions** — answer
   `implementation-shared-conventions` for validation, errors, logging, and
   boundary mechanics shared by the relevant client, server, local application,
   CLI, or job modules.
2. **Fix the shared storage mechanics** — answer
   `implementation-persistence-defaults` for default storage and the path by
   which a representation change reaches an installed app or running system.

In compact form: **shared execution conventions → persistence defaults**. The
sequence does not require both answers: write or amend an artifact only for the
question a feature made real. Accept it once that triggered question is
addressed, then resume the feature; later needs extend the authority without
retroactively blocking earlier work.

## Questions

**1. `implementation-shared-conventions`**
Which conventions do the relevant implementation modules share — error handling,
logging, validation, internal state handling, and boundary mechanics? State which
runtimes they apply to instead of imposing a server convention on every client.

- *Decides:* what a feature's Implementation document may leave unsaid.
- *Why it matters:* a convention discovered rather than stated is followed
  inconsistently, and the inconsistency is only visible across features.

**2. `implementation-persistence-defaults`**
What storage defaults do the relevant runtimes share, and how does a stored
representation change reach an installed application or running system?

- *Decides:* the mechanics every feature's migration inherits.
- *Why it matters:* migration is where a feature is most likely to be
  irreversible, and deciding it per feature means deciding it under pressure.

## Retired question names

`backend-shared-conventions` and `backend-persistence-defaults` are retired.
The `implementation-*` questions above extend their server-oriented scope to
all runtimes; existing answers must be read for applicability, not treated as
answers to the broader questions by renaming alone.
