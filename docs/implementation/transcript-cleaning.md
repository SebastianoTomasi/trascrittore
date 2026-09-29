# Removing what Whisper invents from the transcript

**Status:** accepted

## Scope

This artifact states which text the transcriber removes from speaker turns
after they are built, and which turns it drops as noise, in
`src/asr/transcript_cleaning.py`. Where one turn ends and the next begins is in
[Where one speaker's turn ends and the next begins](speaker-turn-boundaries.md).
What `initial_prompt` says is a setting in `docker/defaults.ini`, left to the
person and the maintainer.

## What is removed

Whisper sometimes writes text that nobody said, mostly over noise and silence.
The voice activity detection before transcription removes most of it; these
rules remove what is left, and never remove words a person may have said.

- **Known phrases.** Subtitle credits and video endings that Whisper learned
  from its training data, such as "Sottotitoli e revisione a cura di QTSS" or
  "Grazie per la visione", are removed wherever they appear. The list is in the
  code.
- **The echoed prompt.** Whisper can write its `initial_prompt` back into the
  transcript. The prompt is removed only where it appears whole, ignoring case
  and punctuation. A part of the prompt, or a turn made of some of its words,
  stays.
- **Noise-only turns.** A turn is dropped only when every word in it is a
  filler with no meaning: eh, ehm, mh, mmh, uh, ah, alone or repeated. A turn
  with any other word stays, however short: "Sì.", "No.", "Ok.",
  "Sì, sì, sì.".

A turn that nothing is left of after these removals is dropped.

## Why

A missing "No." changes what a transcript says; an extra "Eh." does not. The
rules follow the approach studied for Whisper's hallucinations, which removes
only whole phrases that are unlikely in real speech and relies on voice
activity detection for the rest
([Investigation of Whisper ASR Hallucinations Induced by Non-Speech Audio](https://arxiv.org/html/2501.11378v1)).
The echoed prompt is a documented behaviour of Whisper, whole or slightly
changed, at the start of a recording or at the end of a batched segment
([openai/whisper #1150](https://github.com/openai/whisper/discussions/1150),
[faster-whisper #1179](https://github.com/SYSTRAN/faster-whisper/issues/1179)).

## Not chosen

On 2026-09-25 the user replaced two earlier rules:

- **Removing every part of the prompt** of two or more words, and dropping a
  turn made only of prompt words. With the default prompt,
  "Registrazione in italiano.", it dropped a turn "Italiano.". With a longer
  prompt it would delete real speech throughout the transcript: every
  "rumore domestico" in a prompt that mentioned it.
- **Dropping every one-word turn of up to two letters and every turn of one
  repeated word.** It dropped real answers such as "No.", "Sì." and "Ok.".

Removing the echoed prompt altogether was also rejected, since the echo is
documented.

## Known limits

- An echo that changes the prompt's words stays.
- A person who says the whole prompt loses it: with the default prompt,
  "La registrazione in italiano va bene." becomes "La va bene.". A short prompt
  that people rarely say keeps this rare.
- A loop of a real word that Whisper invents over noise, such as
  "sì sì sì sì", stays.
- A short answer said between two turns of the same other speaker is still
  absorbed into that speaker's turn, as
  [the turn rule](speaker-turn-boundaries.md#the-rule) keeps.
