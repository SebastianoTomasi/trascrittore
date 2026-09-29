# Listening to more clips, and to recognized speakers

**State:** closed
**Scope:** feature:voice-library-growth
**Destination:** product
**Revisit when:** the `listen` command is next changed, or when a person wants
to judge more than two clips of a speaker, or to check by ear a name that
recognition gave.

On 2026-09-25 the user proposed two changes to `listen` and postponed them for
lack of time:

- **`--clips N`**, defaulting to 2, so that the person can hear the best N
  clips of a speaker instead of the best two.
- **Listening to any speaker of the transcript**, not only to those left as
  "Persona N".

The agent's assessment, not a decision: both are low-risk, since listening
changes neither the transcript nor the voice library, and they could come
before [adding clips from a recognized speaker](clips-from-recognized-speakers.md).

Today `_prepare_listening` in `src/transcriber/naming.py` calls the same
`_check_labels` as `name`, which refuses any label that already holds a name,
and keeps `library.LISTENING_CLIPS` candidates. Listening to a recognized
speaker changes nothing and lets the person verify a name that recognition
gave, which is the first step of
[correcting a wrongly recognized name](correcting-a-recognized-name.md). `name`
keeps its own rule until that item and the item on clips from recognized
speakers are decided.

## Progress

On 2026-09-29 the user chose:

- `listen` accepts any speaker of the transcript, recognized or not, since
  confirming and correcting a recognized speaker start from it (see
  [correcting a wrongly recognized name](correcting-a-recognized-name.md)).
- `listen` plays one clip at a time: the best one first. A person unsure of the
  voice asks for the next best, again one at a time. This replaces both the
  joined file of two clips and the `--clips N` idea.
- After `name` saves clips, the transcriber opens the person's `registrazioni`
  folder, so the person can click, listen to and delete the clips there, as the
  trial asks. When the folder cannot be opened, for example from an agent, the
  message gives its path.

- A speaker without any full-length window can still be heard: `listen` plays
  the longest window the transcript records, down to
  `matching.min_window_sec`, and says how long it is. It serves to recognize
  the voice by ear only; the library still takes only full-length windows, so
  `name` then changes the transcript and adds no clips.

This changes "the one or two best clips" in the documents listed at the end.
The accepted rules stay in force until the change is propagated.

Established facts that bound N:

- Candidates are only full-length windows (`matching.window_sec`, 10 seconds),
  as
  [the implementation](../features/voice-library-growth/implementation/clip-selection-and-recognition-check.md)
  states, and the transcript records at most `matching.max_windows_per_spk`
  (12) windows per speaker. So N is at most 12 and often less; the result
  should say how many were found.
- A speaker without any full-length window gets no clip whatever N is. On
  2026-09-25 a speaker with about two minutes of speech had none, because every
  stretch was interrupted before 10 seconds.

Questions to settle:

- The listening file. Today the clips are joined in one file with a 0.7-second
  pause, so the player opens once per speaker. With eight clips that file lasts
  more than 80 seconds and the person cannot easily point at a bad one:
  numbered files per clip, or one file per speaker plus numbered ones, or
  another way.
- Whether `listen` should offer shorter windows, down to
  `matching.min_window_sec` (2 seconds), when a speaker has no full-length one.
  They would serve to recognize the voice by ear, not to become clips, since
  only full-length windows are kept as clips.
- Documents that state "the one or two best clips" and would change with it:
  [Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules),
  the listening check in the implementation artifact,
  `docker/skill-trascrittore.md` and the launcher's `help`.

## Resolution

Settled on 2026-09-29 as recorded above. The rules are in
[Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules) ("Listening check, always" and "The clips are
the person's to review"), the command in
[Listening before naming](../features/agent-cli/frontend/agent-command-surface.md#listening-before-naming),
and the mechanics in
[Clip selection](../features/voice-library-growth/implementation/clip-selection-and-recognition-check.md#clip-selection).
Whether 10-second windows are right was measured the same day; see
[Shorter clips for the library](shorter-clips-for-the-library.md).
