# Command-line architecture

**Status:** accepted

## Scope

This artifact sets the components that let a person and an agent use the same
capabilities, and the guarantees they rely on:

- the fields that readers of the transcript JSON can rely on;
- the result summary each command ends with;
- the rule of one transcription at a time.

What the commands print is in
[the command surface](../frontend/agent-command-surface.md). How the skill is
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
  guarantee below covers only what this feature adds.

## Components

- **Commands inside the image.** `python -m src.transcriber` and its commands
  are the only place where a capability is implemented. None of them prompts.
- **Host launcher.** `trascrittore.ps1`, in the transcriber's folder, holds
  everything about running the image:
  - mounting the recording's folder, the voice library `voci`,
    `trascrittore.ini` and the voiceprint cache. `voci` is writable only for
    the commands that change the library; every other command mounts it
    read-only;
  - requesting the GPU for a transcription, and falling back to the CPU when
    Docker cannot start the container with it (exit status 125);
  - the one-transcription-at-a-time check.

  `Trascrivi.bat`, `Verifica.bat` and agents all go through the launcher.
- **The person's layer.** The launcher's interactive modes, used by
  `Trascrivi.bat` and `Verifica.bat`, ask the person the questions, including
  the naming questions at the end of a run, and then call the same commands an
  agent calls. They implement no capability of their own.
- **Skill.** It describes the launcher's commands, the result summary, running a
  transcription in the background, and the rule that only a person gives a
  name. It always ships with the image of the same version.

## Guarantees

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
[voice library growth](../../voice-library-growth/architecture/library-growth-architecture.md#where-clips-come-from).
