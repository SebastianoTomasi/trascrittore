# Listening to more clips, and to recognized speakers

**State:** open
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
