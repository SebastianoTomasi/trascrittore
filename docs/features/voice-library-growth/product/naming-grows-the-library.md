# Naming a speaker grows the voice library

**Status:** accepted

## Scope

This artifact states what happens when a person names a speaker the
transcriber did not recognize, or, on request, confirms or corrects a speaker
it recognized. The transcript shows the name, and voice clips of that speaker
join the PC's voice library, so later recordings can recognize them. It also
states the rules that keep bad clips, wrong names and duplicate people out of
the library:

- the listening check;
- the warning for similar names;
- the automatic selection of the clips to keep;
- the pools the added clips form, and their limits;
- the list of who spoke that follows every transcription.

Other concerns live elsewhere:

- how names are given through commands:
  [agent-cli](../../agent-cli/product/transcribing-through-an-agent.md);
- where clips come from and how the library holds them:
  [the architecture](../architecture/library-growth-architecture.md);
- how clips are selected:
  [the implementation](../implementation/clip-selection-and-pools.md).

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
  — the voice clips, clip records and listening files this feature produces
  are declared there, with where they live and how long they stay.

## Capability

Today clips enter the voice library only when a person places them by hand, and
a name typed at the end of a run applies to that transcript only. With this
feature, naming an unrecognized speaker also adds clips of that speaker's voice
to the library under that name. A name can be given at the end of a run or
later, by the person or through an agent that proposed it. Later recordings
recognize that person.

When the person asks for it, a speaker the transcriber recognized can be
confirmed, adding more clips of that person, or corrected, moving the
transcript and the new clips to the right person.

## Rules

- **A person always gives the name.** An agent may propose one from what the
  speaker said. The name applies only after the person confirms it or writes
  it.
- **Naming adds to the library.** There is no separate choice to name a speaker
  for one transcript only. This was chosen because it is simpler.
- **Nothing is saved for a speaker nobody names.**
- **A recognized speaker changes only on the person's request.** A speaker the
  transcriber recognized keeps its name unless the person asks to confirm or
  correct it, for example by telling the agent "vorrei aggiungere delle clip di
  Sebastiano". Neither the transcriber nor an agent starts or offers this by
  itself. The reasons are in
  [ADR 0005](../../../adr/0005-recognized-speakers-get-clips-only-on-request.md).
  - **Confirming** keeps the name and adds clips of that person. Before
    adding them, the transcriber shows the recognition score and says whether
    new clips would help little, when the score is well above the threshold,
    or much, when it is close to it. The clips are added either way, since the
    person asked.
  - **Correcting** gives the speaker the right name in the transcript and adds
    the clips to the right person. The clips of the person recognized in their
    place are left as they are; the message says who was taken for whom and
    suggests listening to that person's clips and deleting those that are not
    theirs.
- **One folder per person.** A name that differs from a folder in the library
  only in case or spacing goes to that folder, and the message says so.
- **Similar names stop the naming.** A name similar to a person in the library
  saves nothing until the person says whether they meant that person or a new
  one. A name is similar when it differs by one or two letters ("Marco Rosi"
  and "Marco Rossi"), when it has the same surname with the first name reduced
  to an initial ("M. Rossi"), or when it is only the first name of a person in
  the library ("Marco").
- **No clips without a person's request.** The transcriber never adds clips
  for a speaker it recognized unless the person asked, so a wrong recognition
  cannot feed itself.
- **Listening check, always.** Before any clip is saved, the person hears the
  speaker's best clip and confirms that the voice is that person's. When unsure,
  they ask for the next best, one clip at a time. A speaker without any full
  10-second clip can still be heard from their longest stretch of speech, but
  gets no clips. The automatic selection does not replace this check, because
  no automatic selection can tell that a whole speaker is the wrong person.
- **Only the selected clips are saved.** From the first naming, the
  transcriber keeps up to 8 full 10-second clips per speaker and recording, the
  ones that most resemble the rest of that speaker's voice, and discards the
  others by itself. There is no trial period before the selection is trusted:
  the reasons, and the price of a bad clip reaching the library unseen, are in
  [ADR 0006](../../../adr/0006-clip-selection-works-without-a-trial.md).
- **A missed recognition starts a new pool.** The clips a naming adds go into
  one pool of the person's folder:
  - a person new to the library starts with `registrazioni`;
  - confirming a recognized person adds to the added pool that recognized
    them, or to `registrazioni` when a pool made by hand did;
  - when the person says the transcriber missed someone already in the
    library, by giving a "Persona N" that person's name, also after the
    similar-name stop, or by correcting a recognized name to that person, the
    clips start a new pool. It takes the name of the transcript's folder,
    written without spaces as
    [the transcriber writes names](../../../product/transcriber-promise.md#what-an-update-must-not-break),
    such as `2026-10-29-demo-prodotto-acme`. More clips from the same
    transcript join that pool, and the person may rename it;
  - a miss with fewer than 3 full clips, or of a person who already has 8
    added pools, adds its clips to the person's added pool most similar to
    them.

  The reasons are in
  [ADR 0011](../../../adr/0011-a-missed-recognition-starts-a-new-pool.md).
- **The added clips stay within reach.** The result of a naming gives the
  folder where each person's clips went, where the person may listen to them
  and delete a bad one. The transcriber opens no window.
- **Caps on added clips.** Each pool of added clips keeps at most 16 clips,
  and each person at most 8 such pools, so at most 128 added clips. A person
  can change both numbers in `trascrittore.ini`. When a naming takes a pool
  past its cap, the transcriber proposes which of its clips to remove and
  removes them only after the person confirms. It proposes clips of the
  recording with the most clips in that pool first, least consistent first, so
  that different recordings stay. Clips the person placed by hand are never
  proposed.
- **Every transcription shows who spoke.** After each transcription the person
  sees every speaker, recognized or "Persona N", with how long they spoke,
  longest first, and is told to say if a name is wrong. Agreeing, or saying
  nothing, changes nothing and adds no clips, so the list breeds none of the
  confirmations by habit that
  [ADR 0005](../../../adr/0005-recognized-speakers-get-clips-only-on-request.md)
  rules out. Saying that a name is wrong is the person's request to correct it.
  The list is how wrong names are found: there is no recognition check, and
  the maintainer tunes the threshold by hand when people report wrong names.
  The reasons are in
  [ADR 0010](../../../adr/0010-the-list-of-who-spoke-replaces-the-recognition-check.md).

## Actors

- **A person** names speakers, listens, confirms, reads who spoke after each
  transcription, and may delete bad clips.
- **An agent** proposes names for anonymous speakers, runs the commands, and
  opens clips in the player on the person's PC, one speaker at a time. It asks the person before answering a similar name or a proposal to
  remove clips, and it confirms or corrects a recognized speaker only when the
  person asked. It cannot judge a voice by ear.
- **The maintainer** tunes the recognition threshold by hand when people
  report wrong names, as the promise's
  [Who acts](../../../product/transcriber-promise.md#who-acts) allows.

## Data

The feature handles voice clips cut from the person's own recordings. Voice
clips are an existing term in `GLOSSARY.md`. It also keeps a record of where
each added clip came from and prepares listening files. Nothing leaves the PC.

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
- **The name is similar to a person in the library.** Nothing changes until
  the person chooses that person or confirms a new one.
- **The naming takes a pool past its cap.** The new clips are saved, and the
  proposed removals wait for the person's confirmation.

## Non-goals

- **No automatic naming.**
- **No shared library.**
- **No consent step,** per ADR 0002.
- **No score normalization for now.** It was considered and
  [postponed](../../../deferred/recognition-score-normalization.md), and with
  no recognition check nothing would measure it.
- **No clips from recognized speakers without the person's request.**

## Later

On 2026-09-25 the user confirmed one subfolder per person for clips taken from
recordings, as
[the architecture](../architecture/library-growth-architecture.md#where-added-clips-go)
describes, and postponed
[automatic condition pools for added clips](../../../deferred/automatic-pools-for-added-clips.md).
On 2026-09-29 the user settled the similar-name warning, the cap, listening one
clip at a time, and confirming or correcting recognized speakers, which had
been postponed too. On 2026-10-22 the user dropped the trial period and the
folder that naming opened, as
[ADR 0006](../../../adr/0006-clip-selection-works-without-a-trial.md) records.
On 2026-10-29 the user replaced the recognition check with the list of who
spoke, as
[ADR 0010](../../../adr/0010-the-list-of-who-spoke-replaces-the-recognition-check.md)
records. The same day the user chose a new pool for each missed recognition,
with 16 clips per pool and 8 pools per person in place of 64 clips per
person, as
[ADR 0011](../../../adr/0011-a-missed-recognition-starts-a-new-pool.md)
records; this answers the postponed automatic condition pools.

## Security screening

`security-new-subject-or-data`: this feature adds no actor, but it adds data.
Voice clips now also enter the library by naming, and the feature adds clip
records and listening files. The project-wide
[Data classes](../../../product/personal-data-and-obligations.md#data-classes)
were amended on 2026-09-25 to declare them, with where each lives and how long
it stays.

No Security control is added. Every new class stays on the PC, as
[Processing stays on the PC](../../../product/transcriber-promise.md#processing-stays-on-the-pc)
requires, and each class's lifetime is set in that table, as it is for
voiceprints and working files. Where the person's own files go afterwards is
theirs to decide, by [No use policy](../../../product/transcriber-promise.md#no-use-policy).
