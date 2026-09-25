# Library growth architecture

**Status:** proposed

## Scope

This artifact states where the clips of a named speaker come from, and how the
voice library holds the clips added from recordings. It also states what the
trial period and the recognition check must keep. Algorithms are left to
[the implementation](../implementation/clip-selection-and-recognition-check.md).
The rules the person sees are in
[the Product artifact](../product/naming-grows-the-library.md).

## Dependencies

- [Rules](../product/naming-grows-the-library.md#rules) — this architecture
  realizes naming that adds to the library, nothing saved without a name, the
  listening check, the trial and the recognition check.
- [Transcript JSON](../../agent-cli/architecture/agent-cli-architecture.md#transcript-json)
  — clips are cut from the windows that this contract adds to the transcript.
- [Components](../../agent-cli/architecture/agent-cli-architecture.md#components)
  — every new command runs through the host launcher, which mounts the voice
  library. Adding clips needs the library mounted with write access, which is
  read-only today.

## Where clips come from

When a speaker is named, clips are cut from the original recording using that
speaker's windows in the transcript JSON. No clip or voiceprint exists for a
speaker before a name is given. When the recording or the windows are missing,
no clips are added.

## Where added clips go

A person's clips taken from recordings go into one subfolder of that person's
folder, `voci/<Nome>/registrazioni/`. The subfolder is a single pool. Each file
name carries the recording and the time of the window, so a person can tell
where each clip came from. The user confirmed this layout on 2026-09-25.

Subfolders a person makes by hand for a recording condition, such as
`voci/<Nome>/macchina/` or `voci/<Nome>/telefono/`, stay pools of their own, as
they were before this feature. `registrazioni` is one more pool beside them, and
a person may move clips from it into a condition folder.

The reason is how recognition scores a person today. The score is the highest
match between any window of the speaker and any pool of the person. Each pool
counts as the average of its clips:

- **One pool per recording would inflate scores.** Every recording would add
  another pool, and so another chance to reach the threshold, including for the
  wrong person. The calibrated threshold would drift with every addition.
- **One pool keeps the risk bounded.** It adds at most one pool per person, and
  a bad clip in it weighs only as one clip in the average.

A measurement on 2026-09-25 supports this. It used the YIAN library: 8 people,
16 condition folders and 41 clips. Each clip in turn was scored as a speaker,
from its 10-second windows, with threshold 0.575 and margin 0.10. The library
was grouped in three ways:

| Grouping | Condition in the library: mean score, right names | New condition: mean score, right names | Highest score of a missing voice |
|---|---|---|---|
| One pool per condition folder | 0.621, 27 of 37 | 0.530, 13 of 35 | 0.420 |
| One pool per person | 0.609, 26 of 37 | 0.529, 14 of 35 | 0.423 |
| One pool per clip, like one per recording | 0.623, 27 of 37 | 0.512, 9 of 35 | 0.432 |

No grouping produced a wrong name. What these numbers show:

- **Grouping by condition changes scores by about 0.01.** Having a clip of a
  similar condition in the library at all counts far more: about 0.09.
- **A pool of one or two clips is noisy.** It can match worse than the person's
  merged pool, even for a clip of its own condition.
- **One pool per clip loses recognitions in new conditions and raises the
  highest score of a missing voice.**

The data is small: only three people have a car folder. The clips of one folder
often come from one session, which favors condition pools. Grouping added clips
automatically by condition is
[deferred](../../../deferred/automatic-pools-for-added-clips.md): the recognition
check can judge it once named meetings exist.

## Trial state

During the trial, the selection's vote on each saved clip must be kept beside
the clips. A clip the person deleted must remain distinguishable from one they
kept, so the votes can be compared with the person's deletions after 10 named
speakers.

## Recognition check

The check runs on the PC whose library it measures, and it reads that PC's named
transcripts and their recordings. It reads the configuration and suggests a
threshold, but it never writes `trascrittore.ini`.
