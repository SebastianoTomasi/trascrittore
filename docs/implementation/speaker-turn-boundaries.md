# Where one speaker's turn ends and the next begins

**Status:** accepted

## Scope

This artifact states how the transcriber moves the boundary between two
speakers' turns when the diarization puts the last or first words of a sentence
on the wrong side. It covers the grouping of words into turns in
`src/asr/utils/output_format.py`. Which speaker each word gets comes from
whisperX and the diarization and is left to them. What is removed from turns
afterwards is in
[Removing what Whisper invents from the transcript](transcript-cleaning.md).

## Why boundaries move

`whisperx.assign_word_speakers` gives each word the speaker whose diarization
segment overlaps it most, and a new turn starts at every word whose speaker
differs from the previous one. In a call, diarization boundaries are off by a
few hundred milliseconds, most of all where speakers overlap. So the last one
to three words of a sentence often land in the next speaker's turn, or the
first words of the next speaker in the previous turn:

```
[00:10:27] Persona 1: allora ci vediamo la prossima
[00:10:31] Persona 2: settimana. Intanto partiamo dal budget...
```

On 2026-09-25, in a 58-minute call with seven speakers, about 45 of 95 turns
began in the middle of a sentence. Now and then a short statement ended up
under a speaker who did not say it.

## The rule

Between two neighbouring turns of different speakers, a fragment of at most
three words moves to the other turn only when the punctuation of both turns
agrees that it belongs there:

- **A turn that starts mid-sentence.** The later turn begins with a lowercase
  word, and its words up to and including the first one that ends a sentence
  (`.`, `?`, `!`, `…`) number at most three. The earlier turn does not end a
  sentence. The fragment moves to the end of the earlier turn.
- **A turn that ends with the start of a sentence.** The earlier turn has at
  most three words after its last sentence-ending word, and the first of them
  begins with a capital. The later turn begins with a lowercase word. The
  fragment moves to the start of the later turn.

When both apply at the same change of speaker, as in "Intanto partiamo" followed
by another speaker's "dal budget.", either speaker could have said the sentence,
and nothing moves.

A comma never counts as the end of a sentence, so that after a move both turns
read as whole sentences. A turn that a move leaves empty disappears, and
neighbouring turns of the same speaker then merge. "Voce non attribuita"
follows the same rule as any speaker.

The rule runs after short isolated flips are absorbed (`_smooth_short_turns`),
and never splits them again. An interjection such as "Sì, sì" said over
someone else stays inside the surrounding turn, as before.

## Not chosen

- **Placing the change at the longest pause between words.** Turn changes go
  wrong mostly where speakers overlap, where there is often no pause between
  them and the word timings at the edges are least precise. A pause cannot be
  trusted exactly where the fix is needed.
- **Punctuation proposing a move and the pause vetoing it.** For the same
  reason a veto would block the moves that matter most. It is the first
  addition to consider if a person reports words moved to the wrong speaker.

The rule was not measured on real recordings before release: on 2026-09-25 the
user chose to rely on the unit tests in `tests/test_output_format.py`. The
limit of three words and the agreement of both turns bound the harm of a wrong
move.
