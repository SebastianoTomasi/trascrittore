# Vocabulary for names and terms

**State:** closed
**Scope:** project
**Destination:** product
**Revisit when:** before anyone is told to write names in `initial_prompt`, or
when misspelt names become the main complaint about transcripts.

Whisper spells unfamiliar first names, surnames, company names and acronyms by
ear. On 2026-09-25, in a 58-minute call recording, the words around them were
mostly right, but an uncommon first name was always written as a more common
one, a two-word company name came out in five different forms, a two-word
surname was fused into one word, and an acronym came out as a different one.
The recording and its transcript are personal data and are not kept here.

`[whisper] initial_prompt` in `docker/defaults.ini` already steers words and
spelling. whisperX prepends it to every batch (`initial_prompt` in
`whisperx/asr.py`), so it acts on the whole recording, not only on its first
30 seconds. The default is "Registrazione in italiano."; `docker/LEGGIMI.md`
does not mention the setting.

It cannot carry names today. `clean_transcript_text` in
`src/asr/transcript_cleaning.py` removes from every turn each sub-phrase of two
or more words of the prompt that contains a word outside `_PROMPT_STOPWORDS`
(`_prompt_phrase_patterns`), and `is_obvious_transcript_noise` drops a turn made
only of prompt words, including a one-word turn such as a name
(`_is_prompt_fragment`). With a prompt such as "Mario Rossi, Acme Srl", every
correctly transcribed "Mario Rossi" and "Acme Srl" would be deleted from the
transcript. The cleaning exists to remove the prompt when Whisper echoes it
over silence.

Questions to settle:

- Where the names come from: the people in the voice library, with no work for
  the person; a list the person writes in `trascrittore.ini`; a list given for
  one recording through the command line; or more than one of these.
- How an echoed prompt is still removed without deleting real occurrences of
  the names, for example by removing only the whole prompt, or by giving the
  names through whisperX `hotwords` instead of `initial_prompt`.
- How long the list may grow: Whisper keeps at most about 220 prompt tokens,
  and a long list of names may itself be echoed or bias the model towards them.

A possible outcome: the names in the voice library, plus an optional list in
`trascrittore.ini`, given to Whisper with an echo removal that keeps real
occurrences, and the list documented in `LEGGIMI.md`.

## Resolution

Dropped on 2026-09-25. The user chose not to give Whisper names or terms:
a misspelt name is accepted, since the context of the transcript makes it
clear. `initial_prompt` stays "Registrazione in italiano.".
The prompt cleaning described above has since changed: it removes only the
whole prompt, as
[Removing what Whisper invents from the transcript](../implementation/transcript-cleaning.md#what-is-removed)
states.
