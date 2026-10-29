# A missed recognition starts a new pool

When the person says that a speaker the transcriber did not recognize is
someone already in the voice library, the clips of that speaker start a new
pool of that person. This happens when the person gives a "Persona N" the name
of someone in the library, also after the similar-name stop, or corrects a
recognized name to someone in the library. A miss most likely comes from a
recording condition the person's pools do not cover yet, such as another
microphone or room. The clips of that condition match it best when they are
averaged apart from the others. This replaces in part
[ADR 0004](0004-added-clips-form-one-pool-per-person.md), which put every
added clip of a person in one pool.

Recognition scores a person by their best-matching pool, so every pool is one
more chance for someone else's voice to reach the threshold, as ADR 0004 says.
Pools that start only from misses grow slowly, and limits bound them:

- a person has at most 8 pools of added clips, `registrazioni` included;
  pools made by hand do not count;
- a miss with fewer than 3 full clips starts no pool, because a pool of one or
  two clips proved noisy in the ADR 0004 measurement;
- in both cases the clips join the person's added pool most similar to them.

## Considered options

- **Keep one pool per person**: the clips of a new condition are averaged
  with all the others. The ADR 0004 measurement found that this costs about
  0.01, but it had about five clips per person. In a pool of dozens of clips,
  the eight clips of a new condition barely move the average.
- **One pool per recording**, already rejected in ADR 0004: pools would grow
  with every naming, not only when recognition fails.
- **Pools grouped by similarity**, as
  [deferred](../deferred/automatic-pools-for-added-clips.md) on 2026-09-25: it
  needed the recognition check to tune it, and
  [ADR 0010](0010-the-list-of-who-spoke-replaces-the-recognition-check.md)
  removed the check. A miss the person reports marks a new condition more
  surely than a grouping of voiceprints.
- **At most 3 added pools per person**: rejected on 2026-10-29. Since pools
  start only from misses, 8 is a bound nobody is expected to reach.

## Consequences

- An added pool is known by its clip record, not by its folder name, so the
  person may rename it, for example to `macchina`.
- The cap on added clips applies to each pool: at most 16 clips, what two
  namings keep at 8 clips each, so at most 128 per person. From the third
  naming that adds to a pool, the transcriber proposes removals.
- Nothing measures how the extra pools move the scores on a PC, as ADR 0010
  says. A wrong name shows in the list of who spoke, and the maintainer lowers
  the limits if people report wrong names.
