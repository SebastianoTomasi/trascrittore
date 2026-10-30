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
- [Rules](../../voice-library-growth/product/naming-grows-the-library.md#rules)
  of voice library growth — confirming or correcting a recognized speaker on
  request, similar names, the pools and their caps, listening one clip at a
  time and the list of who spoke decide what naming and listening accept, where
  they stop for the person, and what follows a transcription.
- [Where transcripts go](../../../product/transcriber-promise.md#what-an-update-must-not-break)
  — what transcribing writes, and where the recording goes.

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
optionally an output folder. By default the speaker count is detected
automatically, and the transcript goes in a folder of its own next to the
recording, into which the recording moves, as [Where transcripts go](../../../product/transcriber-promise.md#what-an-update-must-not-break) states. With an
output folder, the transcript's folder goes there and the recording stays where
it is.

While it runs, it prints Italian progress lines on standard error. Its closing
lines list who spoke, longest first, with the minutes each spoke, and say that
a wrong name can be corrected; they also say where the transcript's folder is
and whether the recording moved into it. It ends with a result summary with
these fields:

- the status (success or the kind of failure) and an Italian message, which
  also lists who spoke;
- the paths of the transcript's folder and of its text and JSON files;
- where the recording is now, and whether it moved;
- the recording's duration and the elapsed time;
- the device used, with a CPU warning on a PC without an NVIDIA GPU;
- a warning listing the stretches where the transcription got stuck repeating
  the same syllables even when decoded again, so that speech may be missing there;
- a warning listing the stretches of speech that could not be aligned word by
  word: their text is in the transcript, but their times and speaker are
  approximate. The text file's header shows the same warnings;
- for each speaker, the displayed label, whether it was recognized, and how
  long they spoke.

A transcription can last longer than one command may run in an agent: Claude
Code, for example, stops a command after 10 minutes. The `trascrittore` skill
tells the agent to start it in the background and wait for it to end.

When another transcription is already running on the PC, the command ends
immediately. Its status says so, and its message tells the person to wait.

### The list of who spoke

After every transcription the `trascrittore` skill has the agent show the
person who spoke: one bullet per speaker, the name in bold and the minutes,
longest first, recognized names and "Persona N" alike, and then ask whether the
names are right. The message has no buttons. A "yes", or no answer, changes
nothing; a name the person says is wrong leads to
[naming speakers later](#naming-speakers-later), which corrects it.

## Naming speakers later

The command takes a transcript's JSON file and one or more pairs of a displayed
label and a name, for example `Persona 2` = `Luca Bianchi`. It rewrites both
transcript files with the new names, without transcribing again. It ends with
the same kind of result summary.

An agent calls it only with names the person has confirmed or written. The
`trascrittore` skill states this rule.

A label that already holds a recognized name is accepted only in a form that
states the person's intent: confirming the name, or correcting it to another.
Before confirming, the summary carries the recognition score and whether new
clips would help little or much. An agent uses this form only when the person
asked, never on its own suggestion.

Because commands ask nothing, the steps that need the person's decision end
the command with a status of their own, and the agent asks the person before
calling it again:

- **A similar name.** Nothing is saved. The summary lists the people in the
  library whose names are similar. The agent calls the command again with the
  person the person meant, or with an option confirming a new person.
- **Clips over a pool's cap.** The new clips are saved, and the summary lists,
  for each pool past its cap, the added clips proposed for removal. The agent
  runs the removal only after the person confirms.

The pool a naming fills follows the voice library growth rules. The command
needs no option for it: it tells a miss from the labels and from the people
already in the library. When the command saves clips, the summary gives the
folder where each person's clips went, a new pool included. It opens no
window.

## Listening before naming

The listening command takes a transcript's JSON file and one speaker's label,
recognized or not, and plays one clip of that speaker: the best one, or the
next best when asked for it. It refuses more than one speaker: clips opened
together cannot be told apart, so the person answers for one voice before
hearing the next. A speaker without a full clip is played from their
longest stretch of speech, and the summary says how long it lasts. The summary
also says how many clips the speaker has.

In place of a label, the command can take a time. It then plays the segment of
the transcript that holds that time, or the nearest one when the time falls in
a pause, with a second before and after it, so that a person can hear a
doubtful passage before choosing its correction. Its summary gives the times it
cut and the segment's text, so the agent checks that it holds the doubtful
words before offering it. One passage at a time, as for voices. A transcript
made before segments existed has no passage to play, and the summary says so.

## The person's path

`Trascrivi.bat` keeps what a person has today: drag and drop, the question about
the speaker count, and the naming questions at the end of a run. Dropping a
transcript's JSON file on it asks the same naming questions without
transcribing again, which is the person's way of naming speakers later. In
that case it also asks whether the person wants to confirm or correct a
recognized speaker; the questions at the end of a run do not. When a command
stops on a similar name or proposes clips to remove, `Trascrivi.bat` asks the
person the same question the agent would. It collects the answers and passes
them to the same commands an agent uses, so the two paths never drift apart.

At the end of a run, `Trascrivi.bat` shows the same list of who spoke and says
that dropping the JSON file on it corrects a wrong name. There is no
`Verifica.bat`. Keeping a video's frames and correcting misheard words have no
path for a person, as
[parity](../../../product/transcriber-promise.md#parity-between-people-and-agents)
allows.
