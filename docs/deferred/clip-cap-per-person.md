# Cap on clips per person

**State:** open
**Scope:** feature:voice-library-growth
**Destination:** implementation
**Revisit when:** a person's `registrazioni` folder passes about 100 clips, or
building the voiceprint cache after an update becomes noticeably slow.

Naming a speaker adds clips of their voice to `voci/<Nome>/registrazioni`, as
[the architecture](../features/voice-library-growth/architecture/library-growth-architecture.md#where-added-clips-go)
describes. During the trial every candidate clip is saved. After the trial the
selection keeps at most `keep_clips` clips per recording (8, confirmed on
2026-09-25). So a person named in many recordings keeps growing: 50 recordings
add up to 400 clips.

More clips cost the voiceprint of each new clip once, and every clip again when
the cache is rebuilt. Past some size they may also stop improving recognition,
because a pool counts as the mean of its clips.

A cap was listed as an open question in
[the implementation](../features/voice-library-growth/implementation/clip-selection-and-recognition-check.md)
and as proposed in
[the Product artifact](../features/voice-library-growth/product/naming-grows-the-library.md).
On 2026-09-25 the user chose to postpone it. It can wait because the library is
small and grows only when a person names someone.

Remaining questions:

- the cap per person;
- which clips to drop when it is reached: the oldest, the least consistent, or
  those of the recordings with the most clips, which keeps variety of rooms and
  microphones;
- whether dropping needs the person's confirmation, since the clips are the
  person's files.
