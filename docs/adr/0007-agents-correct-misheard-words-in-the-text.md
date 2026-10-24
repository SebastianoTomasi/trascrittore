# Agents correct misheard words in the text

Names, technical terms and other misheard words are corrected after the
transcription by an agent, through the `fix-transcript` skill that ships with
the transcriber, in the transcript's text file and in subtitles made from it.
An agent has what the transcriber lacks to find the right word: the topic, the
files the person points to, what a video shows on screen, a project's glossary.
The transcriber itself implements nothing for it, and the transcript's JSON
file stays as the transcriber wrote it.

## Considered options

- **Give Whisper the names and terms**: dropped on 2026-09-25, as the closed
  record `docs/deferred/vocabulary-for-names-and-terms.md` says, because the
  context of a transcript makes a misspelt name clear. This decision does not
  reopen it: the agent uses that same context to correct the text afterwards.
- **Correct the JSON file as well**: naming a speaker would then keep the
  corrections, but every correction would have to be made in a turn's text,
  in its segment's text and in the text file, or a new command would rewrite
  the text file from the JSON. Rejected on 2026-10-24 as more complication than
  the corrections are worth.

## Consequences

- Naming a speaker rewrites the text file from the JSON file and undoes the
  corrections, so the skill corrects after naming, and again if a speaker is
  named later.
- Readers of the JSON file, such as an agent that cuts a video by its segments,
  get the words as the transcriber heard them.
- Correcting is not a capability of the transcriber, so parity between people
  and agents does not apply to it: a person corrects the text by hand.
- To read a video's screen, the skill may run the ffmpeg of the transcriber's
  image directly, outside the launcher.
