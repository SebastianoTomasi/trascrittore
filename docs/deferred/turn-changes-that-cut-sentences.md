# Turn changes that cut sentences

**State:** closed
**Scope:** project
**Destination:** implementation
**Revisit when:** the grouping of words into turns in
`src/asr/utils/output_format.py` is next changed, or sooner if a person reports
sentences attributed to the wrong speaker.

Where one speaker hands over to another, the transcript often moves the last
one to three words of a sentence into the next speaker's turn, or the first
words of the next speaker into the previous turn. An invented example of the
pattern:

```
[00:10:27] Persona 1: allora ci vediamo la prossima
[00:10:31] Persona 2: settimana. Intanto partiamo dal budget...
```

On 2026-09-25 a 58-minute call recording with seven speakers was transcribed
with the image built that day: about 45 of its 95 turns begin in the middle of
a sentence, with a lowercase first word and a fragment closed by the first
punctuation mark. The shifts go in both directions. They touch about 1% of the
words and rarely change the meaning, but now and then a short statement ends up
under a speaker who did not say it, which makes the transcript unsafe for
quoting. The recording and its transcript are personal data and are not kept
here.

The cause is in how turns are built. `whisperx.assign_word_speakers` gives each
word the speaker whose diarization segment overlaps it most, and
`_speaker_turns` starts a new turn at every word whose speaker differs from the
previous one. In a call, diarization boundaries are off by a few hundred
milliseconds, most of all where speakers overlap, so the words at the edge
fall on the wrong side. `_smooth_short_turns` only absorbs an isolated flip of
up to three words between two turns of the same speaker; it never moves a
boundary between two different speakers.

A possible outcome: after `_speaker_turns`, move a fragment of up to about three
words at the edge of a turn to the neighbouring turn when punctuation shows it
belongs there, that is a turn that begins with lowercase words up to its first
sentence-ending mark, or a turn that ends with words after its last one.
Alternatively, place each change at the longest pause between words within a
small window around it; the aligned result has word timings to measure pauses.
Tests belong in `tests/test_output_format.py`.

The same smoothing absorbs short interjections by other speakers, such as a
"Sì, sì" said over someone else, into the surrounding turn. That is intended,
since it removes false flips, and a fix for boundaries must not bring those
flips back.

## Resolution

On 2026-09-25 the user chose to move a fragment of at most three words only
when the punctuation of both turns agrees, without using pauses, and to rely on
unit tests rather than a measurement on real recordings. The rule is in
[Where one speaker's turn ends and the next begins](../implementation/speaker-turn-boundaries.md#the-rule).
