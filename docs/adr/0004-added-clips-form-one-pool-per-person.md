# Clips added by naming form one pool per person

When a person names a speaker, the clips cut from the recording go into one
subfolder of that person's folder, `voci/<Nome>/registrazioni/`, which
recognition treats as a single pool beside any condition folders the person
made by hand. Recognition scores a person by their best-matching pool, so every
extra pool is one more chance to reach the threshold, for the wrong person as
well as the right one. One pool per person keeps that risk bounded, and a
measurement found little to gain from finer groups.

## Considered options

- **One pool per recording**: every recording would add a pool, and so another
  chance to reach the threshold, and the calibrated threshold would drift with
  every addition. In the measurement below, one pool per clip, the closest
  proxy, lost recognitions in new conditions and raised the highest score of a
  missing voice.
- **One pool per recording condition, chosen by the transcriber**: the
  transcriber does not know a recording's condition. Grouping the clips by
  similarity instead is
  [deferred](../deferred/automatic-pools-for-added-clips.md) until the
  recognition check can judge it on real named meetings.
- **Condition folders made by hand**, as in YIAN (`clean`, `car`, `phone`): they
  stay supported beside `registrazioni`, and a person may move added clips
  into them.

## Consequences

- Clips from different rooms and microphones are averaged in one pool. The
  measurement shows that this costs about 0.01 in score.
- What matters far more is having some clip of a similar condition at all:
  naming speakers in real recordings brings exactly those conditions into the
  library.
- The recognition check on each PC is the way to revisit this choice.

## Evidence

A measurement on 2026-09-25 used the YIAN library: 8 people, 16 condition
folders and 41 clips. Each clip in turn was scored as a speaker, from its
10-second windows, at threshold 0.575 and margin 0.10, against the library
grouped in three ways:

| Grouping | Condition in the library: mean score, right names | New condition: mean score, right names | Highest score of a missing voice |
|---|---|---|---|
| One pool per condition folder | 0.621, 27 of 37 | 0.530, 13 of 35 | 0.420 |
| One pool per person | 0.609, 26 of 37 | 0.529, 14 of 35 | 0.423 |
| One pool per clip, like one per recording | 0.623, 27 of 37 | 0.512, 9 of 35 | 0.432 |

No grouping produced a wrong name. A pool of one or two clips proved noisy: it
can match worse than the person's merged pool, even for a clip of its own
condition.

The data is small: only three people have a car folder. The clips of one folder
often come from one session, which favors condition pools.
