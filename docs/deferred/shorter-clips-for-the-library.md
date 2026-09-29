# Shorter clips for the voice library

**State:** open
**Scope:** feature:voice-library-growth
**Destination:** implementation
**Revisit when:** named speakers often get no clips because they have no
10-second stretch of speech, or the recognition check has named transcripts
from several recordings to recalibrate with.

Only full-length windows (`matching.window_sec`, 10 seconds) become clips, as
[Clip selection](../features/voice-library-growth/implementation/clip-selection-and-recognition-check.md#clip-selection)
states. In calls, speech is broken up, so some speakers have few such windows
or none. On 2026-09-29 the user asked whether 10 seconds is the right length,
and chose to keep it after the measurement below. Accepting clips of about 7.5
seconds is the one change the data suggests, and it can wait.

## Measurement of 2026-09-29

One 58-minute call recording with six speakers was diarized again and cut into
windows of exact lengths from speech where no other speaker overlaps. Speakers
were identified from the transcript's names and the named clips' windows. The
recording and its transcript are personal data and are not kept here.

Against the PC's library without the clips of that recording (three people,
hand-placed clips of 7–54 seconds), with the model and scoring recognition
uses, 12 random windows per speaker, threshold 0.575 and margin 0.10:

| Window | Right names | Mean score, right person vs best wrong one | Speech in full windows |
|---|---|---|---|
| 2 s | 27% | 0.44 vs 0.19 | 84% |
| 3 s | 72% | 0.51 vs 0.22 | 78% |
| 5 s | 100% | 0.58 vs 0.26 | 68% |
| 7.5 s | 100% | 0.63 vs 0.29 | 52% |
| 10 s | 100% | 0.65 vs 0.30 | 46% |
| 15 s | 100% | 0.68 vs 0.34 | 22% |
| 20 s | 100% | 0.70 vs 0.35 | 19% |

No length gave a wrong name. Below 5 seconds recognition degrades sharply.
Above 10 seconds scores gain little while usable speech collapses: at 15
seconds one speaker had a single window and another none. Half of the
speech stretches lasted less than 3.2 seconds.

Pools built from the first half of the same recording and tested on 10-second
windows of the second half scored 0.783 with 5-second clips, 0.789 with
7.5-second clips and 0.796 with 10-second clips. At 7.5 seconds two speakers
would have had 12 and 35 full windows instead of 7 and 18.

Limits: one recording, one condition (a call), three people in the library
besides it, and diarization taken as truth.

## Remaining questions

- Whether clips may be shorter than the recognition windows, which would need a
  setting of their own beside `matching.window_sec`.
- Scores rise with window length, so a change of `matching.window_sec` needs the
  threshold recalibrated with the recognition check.
