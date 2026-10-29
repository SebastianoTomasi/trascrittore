# Clip selection and pools

**Status:** accepted

## Scope

This artifact states how candidate clips are ranked and selected, how similar
names are found, which pool a naming puts its clips in, and which clips the
cap proposes to remove. The contracts these mechanics satisfy are in
[the architecture](../architecture/library-growth-architecture.md).

## Dependencies

- [Rules](../product/naming-grows-the-library.md#rules) — the number of clips
  kept from the first naming, listening one clip at a time, what counts as a
  similar name, which pool receives the clips, and the caps and their order of
  removal.
- [Where added clips go](../architecture/library-growth-architecture.md#where-added-clips-go),
  [Clip record](../architecture/library-growth-architecture.md#clip-record) and
  [Clips over the cap](../architecture/library-growth-architecture.md#clips-over-the-cap)
  — the pool layout, what a clip record holds, and which clips may be removed.
- [The transcript's folder](../../agent-cli/architecture/agent-cli-architecture.md#the-transcripts-folder)
  — a new pool's name is that folder's name written the same way.

## How recognition scores today

`_person_match_score()` in `src/asr/utils/diarization_utils.py` compares every
window embedding of a speaker with every pool of a person, and keeps the
highest score. A pool counts as the normalized mean of its clips' embeddings,
built in `src/asr/voiceprint_cache.py`.

A speaker gets the best person's name when two conditions hold: that score
reaches `matching.threshold`, and it beats the second-best person by
`matching.margin`.

The current values are a threshold of 0.575 and a margin of 0.10. They were
calibrated on 2026-09-24 by leave-one-out on four recordings, with 15 voices in
the library and 7 guests or unknown voices:

- voices in the library scored 0.58–0.82;
- a voice missing from the library scored at most 0.54.

Both sides are thin: the threshold sits 0.035 above the worst unknown and 0.005
below the worst voice in the library. Any growth of the library can move these
numbers, and the maintainer retunes them by hand when people report wrong
names.

## Clip selection

- **Candidates.** The candidates are the speaker's windows, as the transcript
  records them. Only full-length windows (`matching.window_sec`) are kept as
  clips.
- **Consistency score.** Each window's embedding is compared with the mean of
  the same speaker's other windows. A window that does not resemble the rest
  usually contains another voice, laughter or noise.
- **The selection.** The selection keeps at most `library.keep_clips` windows
  per speaker and recording (8 today), best first, and none whose consistency
  score is below `library.min_consistency` (0.60 today, a first guess that no
  review has confirmed, as
  [ADR 0006](../../../adr/0006-clip-selection-works-without-a-trial.md)
  accepts). With a single window there is nothing to compare, so that window is
  kept. Every other window is discarded.
- **What is kept.** From the first naming, only the windows the selection keeps
  are saved as clips, as `<recording>-HH-MM-SS.wav`, where `<recording>` is the
  recording's name written without spaces and the time is the window's start.
  Their clip record holds the consistency score.
- **The listening check.** The person hears one clip at a time, ranked by the
  same score: the first listening plays the best, and each further request the
  next one. A speaker with no full-length window is played from their longest
  recorded window, down to `matching.min_window_sec`; that window is only
  heard, never saved. For an agent, opening a clip means starting the default
  player on the person's PC, for one speaker at a time.

## Similar names

Before a naming saves anything, the given name is compared, ignoring case and
spacing, with the folders of the library other than an exact match. It is
similar to a folder when:

- the two names are one or two letter edits apart;
- the surnames match and one first name is the other's initial;
- the given name is a single word equal to the first word of a folder's name.

## Choosing the pool

A naming decides the pool of each named speaker from the people the library
held before it:

1. **A person new to the library** gets `registrazioni`.
2. **A confirmed person** gets the pool, among all of theirs, whose voiceprint
   is closest to the mean of the speaker's kept clips; when that pool was made
   by hand, the clips go to `registrazioni`.
3. **A miss**, a "Persona N" given the name of a person already in the library
   or a recognized name corrected to one, gets a new added pool when the
   selection kept at least 3 clips and the person has fewer than
   `library.max_pools` added pools (8 today). Its folder takes the transcript
   folder's name, written as
   [the transcript's folder](../../agent-cli/architecture/agent-cli-architecture.md#the-transcripts-folder)
   writes names. An added pool of that name is reused; a folder of that name
   made by hand gets the next free `-2`, `-3` suffix.
4. **Otherwise**, a miss joins the person's added pool whose voiceprint is
   closest to the mean of its kept clips, or `registrazioni` when the person has
   none.

"Closest" is the cosine similarity between the normalized mean of the kept
clips' window embeddings, already computed for the selection, and each pool's
normalized mean, as recognition builds it. An added pool is a subfolder of the
person's folder that holds `clip.json`, or is called `registrazioni`.

## Clips over the cap

After a naming saves clips, the clips with a record in each pool that received
some are counted against `library.max_clips` (16 today). When they are more,
the proposal takes them from the recording with the most such clips in that
pool, lowest consistency first (the consistency is in the clip record),
recounting after each, until the count is back at the cap. A person's added
pools are at most `library.max_pools`, so a person keeps at most
`max_clips × max_pools` added clips (128 today).

## Later

On 2026-09-25 the user confirmed the values above (8 clips and the 0.60
floor); on 2026-09-29 listening one clip at a time replaced the two clips
joined in one file, and the cap was settled. On 2026-10-22 the trial
bookkeeping was dropped with the trial. On 2026-10-29 the recognition check
was removed, as
[ADR 0010](../../../adr/0010-the-list-of-who-spoke-replaces-the-recognition-check.md)
records, and the cap of 64 clips per person became 16 clips per pool with at
most 8 added pools, as
[ADR 0011](../../../adr/0011-a-missed-recognition-starts-a-new-pool.md)
records; the choice of the pool, the closest-pool measure and the suffix for a
name taken by a folder made by hand were settled within the user's delegation
the same day. Still postponed:

- [score normalization](../../../deferred/recognition-score-normalization.md),
  which would change the score scale and require a new calibration.

On 2026-09-29 a measurement confirmed 10-second windows as the length to keep.
[Shorter clips for the library](../../../deferred/shorter-clips-for-the-library.md)
records it and the possible move to clips of about 7.5 seconds.
