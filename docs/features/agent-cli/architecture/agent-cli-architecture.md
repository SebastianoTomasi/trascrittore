# Command-line architecture

**Status:** accepted

## Scope

This artifact sets the components that let a person and an agent use the same
commands, and the guarantees they rely on:

- the transcript's folder, its names and the move of the recording;
- the fields that readers of the transcript JSON can rely on;
- the result summary each command ends with;
- the rule of one transcription at a time.

What the commands print is in
[the command surface](../frontend/agent-command-surface.md). How the skills are
delivered is in [skill delivery](../deployment/skill-delivery.md). Why agents
get a command line and a skill instead of an MCP server is in
[ADR 0003](../../../adr/0003-agents-use-a-command-line-and-a-skill.md).

## Dependencies

- [Parity between people and agents](../../../product/transcriber-promise.md#parity-between-people-and-agents)
  — this parity rule is why capabilities live only in commands and the person's
  path is a layer on top of them.
- [Agents](../../../product/transcriber-promise.md#agents) — the agents the
  promise names can all run commands. The choice of a command line over an MCP
  server rests on this.
- [Processing stays on the PC](../../../product/transcriber-promise.md#processing-stays-on-the-pc)
  — no component added here sends anything off the PC or needs a network
  connection.
- [What an update must not break](../../../product/transcriber-promise.md#what-an-update-must-not-break)
  — the fields of the transcript JSON are not in that baseline, so the
  guarantee below covers only what this feature adds. Where transcripts go is
  in it, and [The transcript's folder](#the-transcripts-folder) realizes it.
- [Installation and update](../../../deployment/gpu-installation.md#installation-and-update)
  — the launcher uses the active image selected and checked by the installer.
- [Non-goals](../../../product/transcriber-promise.md#non-goals) and
  [Frames of a video](../../video-frames/product/frames-of-a-video.md) —
  correcting misheard words and choosing a video's frames are an agent's work,
  so the skills for them add no command.

## Components

- **Commands inside the image.** `python -m src.transcriber` and its commands
  are the only place where a capability is implemented. None of them prompts.
- **Host launcher.** `trascrittore.ps1`, in the transcriber's folder, holds
  everything about running the image:
  - mounting the recording's folder, the voice library `voci`,
    `trascrittore.ini` and the voiceprint cache. The recording's folder is
    writable only for transcribing, which creates the transcript's folder in it
    and moves the recording. `voci` is writable only for the commands that
    change the library; every other command mounts it read-only;
  - requesting the GPU for a transcription on a PC installed for GPU use. The
    installer selects a compatible image before the launcher runs, as
    [GPU installation](../../../deployment/gpu-installation.md) defines.
    If GPU execution stops working, the launcher reports the failure instead
    of silently continuing with some or all phases on CPU. On a PC without an
    NVIDIA GPU, the same commands remain available on CPU with a warning;
  - the one-transcription-at-a-time check.

  `Trascrivi.bat` and agents go through the launcher for every command of the
  transcriber. The only other use of the image is the skills': an agent runs
  the image's ffmpeg to look at a video and keep its frames, which uses none of
  the transcriber's commands, data or settings.
- **The person's layer.** The launcher's interactive modes, used by
  `Trascrivi.bat`, show the person what happens and ask any
  questions, such as the naming questions at the end of a run, and then call
  the same commands an agent calls. They implement no capability of their own.
- **Skills.** The `trascrittore` skill describes the launcher's commands, the
  result summary, running a transcription in the background, the list of who
  spoke after every transcription, the rule that only a person gives a name,
  and, for a video, titling the transcript's folder and keeping its frames. The
  `fix-transcript` skill tells an agent how to correct misheard words in a
  transcript's text file and in subtitles made from it, reading the kept frames
  first and leaving the JSON file as it is, as
  [ADR 0007](../../../adr/0007-agents-correct-misheard-words-in-the-text.md)
  records. Both always ship with the image of the same version.

## Guarantees

### The transcript's folder

The transcribe command writes every name it creates the same way: the
recording's name decomposed to drop accents, in lowercase, with each run of
characters other than `a`–`z` and `0`–`9` replaced by one hyphen and no hyphen
at either end. An empty result becomes `registrazione`. Call the result
`<name>`:

- **The folder.** Without an output folder, the transcript goes in `<name>`
  next to the recording. If the recording already sits in its transcript's
  folder, one holding `<name>-trascrizione.json` or itself called `<name>`, the
  transcript is written there again. If `<name>` already holds another
  recording called `<name>`, the next free `<name>-2`, `<name>-3` is used.
  With an output folder, `<name>` is created there instead, and the recording
  stays where it is.
- **The files.** The text and JSON files are `<name>-trascrizione.txt` and
  `<name>-trascrizione.json`.
- **The move.** Only after both files are written does the recording move into
  the folder as `<name>` with its extension in lowercase. When the move
  succeeds, both files are written again with the recording's new place. When
  it fails, the files keep the old place, and the summary and the message say
  that the recording stayed where it was.

An agent may rename the folder, writing the new name the same way. The path
the JSON records then no longer matches, which is why readers also look for the
recording beside the transcript.

### Transcript JSON

This feature adds to the `speakers` block of the transcript's JSON file and
removes nothing from it. For each speaker, recognized or not, it records the
windows the transcriber used to recognize that speaker. Each window has a start
and an end in seconds from the start of the recording, and contains no
overlapping speech. There are at most `matching.max_windows_per_spk` windows per
speaker (12 today), each at most `matching.window_sec` long (10 s today).

[Voice library growth](../../voice-library-growth/architecture/library-growth-architecture.md)
relies on these windows. Transcripts made before this change have no windows,
so every reader must handle their absence.

### Result summary

Every command ends with one JSON document on standard output, with the fields
listed in [the command surface](../frontend/agent-command-surface.md#transcribing).
A command that fails still ends with a summary that states the kind of failure.
When the container ends without one, the launcher writes it.

### One transcription at a time

At most one transcription runs on a PC at a time, because two would compete for
GPU memory. The launcher refuses a second one while a transcription container is
running. Only a transcription uses the GPU: every other command, such as naming
speakers later, runs on the CPU and is not limited.

### Naming later never transcribes again

Naming speakers later rewrites both transcript files from the transcript's JSON
file alone. The recording is read only to cut voice clips for
[voice library growth](../../voice-library-growth/architecture/library-growth-architecture.md#where-clips-come-from),
and it is looked for where the JSON records it, then beside the transcript.
