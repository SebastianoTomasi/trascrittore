# Naming a speaker grows the voice library

**Status:** accepted

## Scope

This artifact states what happens when a person names a speaker the
transcriber did not recognize. The transcript shows the name, and voice clips
of that speaker join the PC's voice library, so later recordings can recognize
them. It also states the rules that keep bad clips and wrong names out of the
library:

- the listening check;
- the trial period that decides when automatic clip selection can be trusted;
- the recognition check that must exist first.

Other concerns live elsewhere:

- how names are given through commands:
  [agent-cli](../../agent-cli/product/transcribing-through-an-agent.md);
- where clips come from and how the library holds them:
  [the architecture](../architecture/library-growth-architecture.md);
- how clips are selected and how the check works:
  [the implementation](../implementation/clip-selection-and-recognition-check.md).

## Dependencies

- [One voice library per PC](../../../product/transcriber-promise.md#one-voice-library-per-pc)
  — clips go to the library of the PC where the naming happens. There is no
  shared library to keep consistent.
- [No use policy](../../../product/transcriber-promise.md#no-use-policy) and
  [ADR 0002](../../../adr/0002-personal-tool-without-use-policy.md) — naming a
  speaker adds them to the library whoever they are, with no consent step.
- [Naming speakers later](../../agent-cli/frontend/agent-command-surface.md#naming-speakers-later)
  — this feature extends naming, so naming also adds clips.
- [Transcript JSON](../../agent-cli/architecture/agent-cli-architecture.md#transcript-json)
  — the clips come from the speaker windows that the transcript records.
- [Parity between people and agents](../../agent-cli/product/transcribing-through-an-agent.md#parity-between-people-and-agents)
  — every step below exists both for a person and as a command for an agent.
- [Data classes](../../../product/personal-data-and-obligations.md#data-classes)
  — the voice clips, clip records, listening files and trial result this
  feature produces are declared there, with where they live and how long they
  stay.

## Capability

Today clips enter the voice library only when a person places them by hand, and
a name typed at the end of a run applies to that transcript only. With this
feature, naming an unrecognized speaker also adds clips of that speaker's voice
to the library under that name. A name can be given at the end of a run or
later, by the person or through an agent that proposed it. Later recordings
recognize that person.

## Rules

- **A person always gives the name.** An agent may propose one from what the
  speaker said. The name applies only after the person confirms it or writes
  it.
- **Naming adds to the library.** There is no separate choice to name a speaker
  for one transcript only. This was chosen because it is simpler.
- **Nothing is saved for a speaker nobody names.**
- **Only speakers left as "Persona N" are named.** A speaker the transcriber
  recognized keeps its name. Correcting a wrongly recognized name is
  [deferred](../../../deferred/correcting-a-recognized-name.md).
- **One folder per person.** A name that differs from a folder in the library
  only in case or spacing goes to that folder, and the message says so. A
  warning for names that differ more is
  [deferred](../../../deferred/near-duplicate-name-warning.md).
- **No clips for speakers recognized automatically.** The transcriber adds no
  clips for speakers it recognized by itself, so a wrong recognition cannot feed
  itself.
- **Listening check, always.** Before any clip is saved, the person listens to
  the one or two best clips and confirms that the voice is that person's. This
  check stays after the trial, because no automatic selection can tell that a
  whole speaker is the wrong person.
- **Trial period.**
  - Every candidate clip is saved together with the selection's vote (keep or
    discard). Nothing is discarded automatically.
  - The person deletes the clips they judge bad. They do not see the votes
    while judging: deletions that followed the votes would prove nothing.
  - Moving a clip elsewhere in the same person's folder, such as into a
    condition folder, does not count as deleting it.
  - After 10 named speakers, if the selection never kept a clip the person
    deleted, the person is asked whether they listened to the added clips and
    deleted the bad ones. Only when they confirm does the selection start
    discarding by itself. It then keeps up to 8 full 10-second clips per
    recording. Without that review, the absence of disagreements proves
    nothing.
  - If it kept even one such clip, the cause is examined, the selection is
    corrected and the trial starts again.
- **Recognition check first.** A repeatable check of recognition against the
  PC's own library must exist before this feature ships.
  - It reports how many wrong names and missed recognitions the current
    threshold and margin would produce, and suggests a threshold.
  - It takes as truth only the names a person gave. An automatic name may be
    wrong, and counting it as right would hide the error.
  - A person applies the suggestion in `trascrittore.ini`; the check never changes it
    by itself.
  - It runs on each PC, since each PC has its own library.
  - It runs again after a number of additions and before the trial ends. For
    now the person runs it now and then; the number of additions is
    [deferred](../../../deferred/recognition-check-cadence.md).

## Actors

- **A person** names speakers, listens, confirms, deletes bad clips and applies
  the threshold.
- **An agent** proposes names, runs the commands, reports the trial's results,
  and opens clips in the player on the person's PC. It cannot judge a voice by
  ear.
- **The maintainer** may help a person run the recognition check, as the
  promise's [Who acts](../../../product/transcriber-promise.md#who-acts) allows.

## Data

The feature handles voice clips cut from the person's own recordings. Voice
clips are an existing term in `CONTEXT.md`. It also keeps a record of where
each added clip came from, prepares listening files, and records the trial's
result. The recognition check reads named transcripts and their recordings.
Nothing leaves the PC.

## Preconditions

- The transcript was made by a version that records the speaker windows.
- The recording is still where the transcript says it was, or its new location
  is given.

## Outcomes

- **Success.** The transcript shows the name, and clips of the speaker are in
  the library under that name. The next recordings can recognize that person.
- **The recording is missing, or the transcript has no windows.** The name is
  applied to the transcript, no clips are added, and the message says why.
- **The person rejects the voice at the listening check.** Nothing changes:
  neither the transcript nor the library.

## Non-goals

- **No automatic naming.**
- **No shared library.**
- **No consent step,** per ADR 0002.
- **No score normalization for now.** It was considered and
  [postponed](../../../deferred/recognition-score-normalization.md): the
  recognition check comes first, and normalization would be judged with it.
- **No clips from speakers recognized automatically.**

## Later

On 2026-09-25 the user confirmed one subfolder per person for clips taken from
recordings, as
[the architecture](../architecture/library-growth-architecture.md#where-added-clips-go)
describes, and postponed:

- [a warning for near-duplicate names](../../../deferred/near-duplicate-name-warning.md);
- [a cap on clips per person](../../../deferred/clip-cap-per-person.md);
- [correcting a wrongly recognized name](../../../deferred/correcting-a-recognized-name.md);
- [automatic condition pools for added clips](../../../deferred/automatic-pools-for-added-clips.md).

## Security screening

`security-new-subject-or-data`: this feature adds no actor, but it adds data.
Voice clips now also enter the library by naming, and the feature adds clip
records, listening files and the trial result. The project-wide
[Data classes](../../../product/personal-data-and-obligations.md#data-classes)
were amended on 2026-09-25 to declare them, with where each lives and how long
it stays.

No Security control is added. Every new class stays on the PC, as
[Processing stays on the PC](../../../product/transcriber-promise.md#processing-stays-on-the-pc)
requires, and each class's lifetime is set in that table, as it is for
voiceprints and working files. Where the person's own files go afterwards is
theirs to decide, by [No use policy](../../../product/transcriber-promise.md#no-use-policy).
