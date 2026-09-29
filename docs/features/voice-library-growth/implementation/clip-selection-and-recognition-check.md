# Clip selection and recognition check

**Status:** accepted

## Scope

This artifact states how candidate clips are ranked and selected, how similar
names and clips over the cap are found, how the trial
compares the selection with the person's choices, and how the recognition check
measures the threshold and margin without fooling itself. The contracts these
mechanics satisfy are in
[the architecture](../architecture/library-growth-architecture.md).

## Dependencies

- [Rules](../product/naming-grows-the-library.md#rules) — the trial's
  criterion, the number of clips kept, listening one clip at a time, what
  counts as a similar name, the cap and its order of removal, and what the
  recognition check reports.
- [Where added clips go](../architecture/library-growth-architecture.md#where-added-clips-go),
  [Clip record](../architecture/library-growth-architecture.md#clip-record),
  [Clips over the cap](../architecture/library-growth-architecture.md#clips-over-the-cap) and
  [Recognition check](../architecture/library-growth-architecture.md#recognition-check)
  — the pool layout, how a recorded clip is identified, which clips may be
  removed, and the check's inputs.

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
numbers.

## Clip selection

- **Candidates.** The candidates are the speaker's windows, as the transcript
  records them. Only full-length windows (`matching.window_sec`) are kept as
  clips.
- **Consistency score.** Each window's embedding is compared with the mean of
  the same speaker's other windows. A window that does not resemble the rest
  usually contains another voice, laughter or noise.
- **The selection's vote.** The selection votes to keep at most
  `library.keep_clips` windows per speaker and recording (8 today), best first,
  and none whose consistency score is below `library.min_consistency` (0.60
  today, a first guess for the trial to confirm). With a single window there is
  nothing to compare, so that window is kept. Every other window is voted
  discard.
- **What is kept.** After the trial, only the windows voted keep are saved as
  clips. Their file names carry the recording and the window's time.
- **The listening check.** The person hears one clip at a time, ranked by the
  same score: the first listening plays the best, and each further request the
  next one. A speaker with no full-length window is played from their longest
  recorded window, down to `matching.min_window_sec`; that window is only
  heard, never saved. For an agent, opening a clip means starting the default
  player on the person's PC.

## Similar names

Before a naming saves anything, the given name is compared, ignoring case and
spacing, with the folders of the library other than an exact match. It is
similar to a folder when:

- the two names are one or two letter edits apart;
- the surnames match and one first name is the other's initial;
- the given name is a single word equal to the first word of a folder's name.

## Clips over the cap

After a naming saves clips, the person's clips in `registrazioni` that have a
clip record are counted against `library.max_clips` (64). When they are more,
the proposal takes them from the recording with the most such clips, lowest
consistency first (the consistency is in the clip record), recounting after
each, until the count is back at the cap. During the trial nothing is proposed.

## Trial bookkeeping

Each saved clip's vote is written to the clip record, `clip.json` in the
person's `registrazioni` folder, when the clip is saved. To find a recorded
clip, the trial looks for its file name anywhere in that person's folder. A
clip the person deleted is simply missing from the whole folder. A
named speaker counts once for each person, recording and label.

After 10 named speakers, a command reports where the votes and the person's
deletions disagree. The only disagreement that matters is a clip the selection
kept and the person deleted. With none, the trial ends only when the person
confirms the review: `Verifica.bat` asks, and an agent runs `trial --reviewed`
after asking. A change to the selection algorithm raises `SELECTION_VERSION` in
the code, which starts a new trial.

## Recognition check

The check repeats the 2026-09-24 calibration as the `check` command
(`src/transcriber/recognition_check.py`). It works on the named transcripts
listed in the clip records, together with any given to it; the launcher finds
them by reading every `clip.json` in the library.

1. **Each recording in turn.** For each named transcript, the check removes from
   the library the clips cut from that same recording, so no speaker matches
   their own clips. A clip's recording is the part of its file name before the
   window's time, so moving a clip or losing its record changes nothing. Two
   recordings with the same name lose each other's clips too, which only makes
   the check stricter. It then scores the transcript's speakers and counts:
   - right names;
   - wrong names;
   - people in the library who stayed "Persona N".
2. **Unknown voices.** The check removes one person at a time from the library
   and records the name that person's voice would receive instead.
3. **Report.** The check reports:
   - the range of scores for right matches and for voices missing from the
     library;
   - the error counts at the current threshold and margin;
   - a suggested threshold 0.03 above the highest score reached by a voice
     missing from the library or by a person taken for another, so that wrong
     names stay at zero, and the recognitions that threshold would lose. With
     fewer than 10 voices missing from the library, real or simulated, the check
     suggests no threshold, because a suggestion would rest on chance.

Only the voices a person named count as known: a name the transcriber gave by
itself may be wrong.

## Later

On 2026-09-25 the user confirmed the values above (8 clips, the 0.60 floor, the
0.03 slack and the 10 missing voices); on 2026-09-29 listening one clip at a
time replaced the two clips joined in one file, and the cap was settled. Still
postponed:

- [how many additions trigger a new run of the check](../../../deferred/recognition-check-cadence.md);
- [score normalization](../../../deferred/recognition-score-normalization.md),
  which would change the score scale and require a new calibration.

On 2026-09-29 a measurement confirmed 10-second windows as the length to keep.
[Shorter clips for the library](../../../deferred/shorter-clips-for-the-library.md)
records it and the possible move to clips of about 7.5 seconds.
