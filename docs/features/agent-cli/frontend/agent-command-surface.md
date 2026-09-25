# Command surface for agents and people

**Status:** accepted

## Scope

This artifact states how the transcriber's commands behave for the agent and
the person who use them: what a command asks for, what it prints, the result it
ends with and the states it can end in. It covers `Trascrivi.bat` only insofar
as it is built on the same commands. The capability is in
[the Product artifact](../product/transcribing-through-an-agent.md). The
components and the transcript file contract are in
[the architecture](../architecture/agent-cli-architecture.md). Exact command
and flag names are left to the code.

## Dependencies

- [Capability](../product/transcribing-through-an-agent.md#capability) and
  [Outcomes](../product/transcribing-through-an-agent.md#outcomes) — the
  commands below express that capability and its success and failure states.
- [Parity between people and agents](../product/transcribing-through-an-agent.md#parity-between-people-and-agents)
  — every person-facing interaction must have a command behind it.
- [Components](../architecture/agent-cli-architecture.md#components) — every
  command goes through the host launcher, so a person and an agent get the same
  behavior.

## Commands ask nothing

A command takes everything it needs from its arguments. When a required input
is missing, the command ends with a message; it never waits for an answer. This
holds for every command a capability adds, including those of
[voice library growth](../../voice-library-growth/product/naming-grows-the-library.md).

## How every command is called and ends

Every command runs through the launcher, with the same line from cmd,
PowerShell and Git Bash:

```
powershell -NoProfile -ExecutionPolicy Bypass -File "<transcriber folder>\trascrittore.ps1" <command> [arguments]
```

Lines for people, including progress, go to standard error. Standard output
carries only the result summary: one line of JSON, in ASCII so that it reads the
same in any code page. Its `status` is `ok` or the kind of failure, and its
`message` is in Italian.

The exit status tells the kinds of result apart that an agent acts on
differently:

| Exit status | Meaning |
| --- | --- |
| 0 | Success. |
| 2 | Invalid arguments. |
| 3 | Another transcription is running on the PC. |
| 130 | Interrupted. |
| 1 | Any other failure; the summary's `status` says which. |

The launcher's `help` lists every command and flag, and stays complete.

## Transcribing

The command takes the recording, optionally the exact number of speakers and
optionally an output folder. The defaults are the same as today: speaker count
detected automatically, and the output written next to the recording.

While it runs, it prints the same Italian progress lines as today, on standard
error. It ends with a result summary with these fields:

- the status (success or the kind of failure) and an Italian message;
- the paths of the transcript's text and JSON files;
- the recording's duration and the elapsed time;
- the device used, with the CPU fallback warning when there was one;
- for each speaker, the displayed label, whether it was recognized, and how
  long they spoke.

A transcription can last longer than one command may run in an agent: Claude
Code, for example, stops a command after 10 minutes. The skill tells the agent
to start it in the background and wait for it to end.

When another transcription is already running on the PC, the command ends
immediately. Its status says so, and its message tells the person to wait.

## Naming speakers later

The command takes a transcript's JSON file and one or more pairs of a displayed
label and a name, for example `Persona 2` = `Luca Bianchi`. It rewrites both
transcript files with the new names, without transcribing again. It ends with
the same kind of result summary.

An agent calls it only with names the person has confirmed or written. The
skill states this rule.

## The person's path

`Trascrivi.bat` keeps what a person has today: drag and drop, the question about
the speaker count, and the naming questions at the end of a run. Dropping a
transcript's JSON file on it asks the same naming questions without
transcribing again, which is the person's way of naming speakers later. It
collects the answers and passes them to the same commands an agent uses, so the
two paths never drift apart.
