# Automatic condition pools for added clips

**State:** closed
**Scope:** feature:voice-library-growth
**Destination:** architecture
**Revisit when:** the recognition check has run on at least 10 named speakers
from real meetings, and it shows people missed in some recording conditions,
such as a call or a car.

In YIAN each person's clips sat in condition subfolders (`clean`, `car`,
`phone`, `wa_audio`, `echo`). Each subfolder is a pool with its own mean
voiceprint, so a speaker recorded in a car can match that person's car pool
strongly. The transcriber still supports these folders.

The clips added by naming, however, all go into one pool,
`voci/<Nome>/registrazioni/`, as
[Where added clips go](../features/voice-library-growth/architecture/library-growth-architecture.md#where-added-clips-go)
states. The transcriber does not know a recording's condition, and one pool per
recording would inflate scores.

A measurement on the YIAN library on 2026-09-25, recorded in
[ADR 0004](../adr/0004-added-clips-form-one-pool-per-person.md#evidence), found
that grouping by condition moved scores by about 0.01. The difference between a
condition present in the library and a new condition was about 0.09. On
2026-09-25 the user chose the single pool, with condition folders made by hand.

A later change could split a person's added clips automatically into at most
two or three pools of similar clips, for example by clustering their
voiceprints. That bounds the extra pools while keeping condition matching.
Before adopting it, the recognition check should compare it with the single
pool on the PC's own named meetings. It must not raise the highest score of a
missing voice.

## Resolution

Settled on 2026-10-29 in another way: instead of grouping a person's added
clips by similarity, a recognition the person says was missed starts a pool of
its own, up to 8 added pools per person. The rule is in
[Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules)
("A missed recognition starts a new pool"), with the reasons in
[ADR 0011](../adr/0011-a-missed-recognition-starts-a-new-pool.md).
