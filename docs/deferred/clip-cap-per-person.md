# Cap on clips per person

**State:** closed
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
[the implementation](../features/voice-library-growth/implementation/clip-selection-and-pools.md)
and as proposed in
[the Product artifact](../features/voice-library-growth/product/naming-grows-the-library.md).
On 2026-09-25 the user chose to postpone it. It can wait because the library is
small and grows only when a person names someone.

## Progress

On 2026-09-29 the user chose, noting that the cap is rarely reached: a
person's clips grow only when they are named as "Persona N", that is missed by
recognition, or when the person explicitly asks to add clips of a recognized
speaker.

- **Cap:** 64 clips in a person's `registrazioni` folder (8 recordings of 8
  clips), a setting in `trascrittore.ini`.
- **Proposal, then confirmation.** When a naming takes the folder over the cap,
  the transcriber proposes which clips to remove and removes them only after
  the person confirms. `Trascrivi.bat` asks; for an agent, the command ends
  with the proposal and the agent asks the person before running the removal.
- **Which clips:** only clips the transcriber added, in `registrazioni`; folders
  made by hand are never touched. The proposal starts from the recording with
  the most clips, least consistent first, so rooms and microphones stay varied.
- **Not during the trial,** since the trial discards nothing automatically.

Former questions:

- the cap per person;
- which clips to drop when it is reached: the oldest, the least consistent, or
  those of the recordings with the most clips, which keeps variety of rooms and
  microphones;
- whether dropping needs the person's confirmation, since the clips are the
  person's files.

## Resolution

Settled on 2026-09-29 as recorded above. The rule is in
[Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules) ("Cap on added clips"), the removable clips in
[Clips over the cap](../features/voice-library-growth/architecture/library-growth-architecture.md#clips-over-the-cap),
and the order of removal in
[Clips over the cap](../features/voice-library-growth/implementation/clip-selection-and-pools.md#clips-over-the-cap).
