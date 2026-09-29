# Transcribing through an agent

**Status:** accepted

## Scope

This artifact states what an agent can do with the transcriber on a person's
behalf: transcribe a recording without anyone answering questions, read the
result, and give names to speakers after the transcript exists. It also states
the rule that keeps people and agents at the same capability. The commands are
in [the command surface](../frontend/agent-command-surface.md), their
components and file guarantees in
[the architecture](../architecture/agent-cli-architecture.md), and how the
skill reaches a PC in [skill delivery](../deployment/skill-delivery.md). Adding
a named speaker's voice clips to the voice library belongs to
[voice library growth](../../voice-library-growth/product/naming-grows-the-library.md).

## Dependencies

- [Agents](../../../product/transcriber-promise.md#agents) — this feature
  details the command-line interface and the skill that the promise says exist.
- [People close to the maintainer](../../../product/transcriber-promise.md#people-close-to-the-maintainer)
  — a person keeps transcribing without a command line. The agent path sits
  beside that path and never replaces it.
- [What users are assumed to have](../../../product/transcriber-promise.md#what-users-are-assumed-to-have)
  — agents run on Windows itself, not inside WSL, so every command must work
  from the Windows shells an agent uses.
- [No use policy](../../../product/transcriber-promise.md#no-use-policy) —
  whether a transcript reaches an agent's model provider is the person's
  choice. The transcriber neither performs nor blocks it.
- [Non-goals](../../../product/transcriber-promise.md#non-goals) — the
  commands keep one transcription at a time and leave minutes and summaries to
  the agent.
- [Rules](../../voice-library-growth/product/naming-grows-the-library.md#rules)
  of voice library growth — naming later confirms or corrects a recognized
  speaker only on the person's request, and stops on a name similar to a person
  in the library, so the capability and failures below follow those rules.
- [Data classes](../../../product/personal-data-and-obligations.md#data-classes)
  — the speaker windows belong to the transcript class declared there, so this
  feature inherits its obligations and adds none.

## Capability

Once this feature exists, a person can tell their agent to transcribe a
recording, for example a file just saved by OBS, and get the transcript without
sitting at the console. The agent starts the transcription, waits for it
without holding a command open, and reads a short machine-readable result:
whether it succeeded, where the transcript files are, who spoke, and which
speakers stayed "Persona N".

Afterwards the agent can propose names for those speakers from what they said.
The person confirms or writes each name, and the transcript is updated without
transcribing the recording again. When the person asks, the agent also confirms
or corrects a speaker the transcriber recognized, as
[voice library growth](../../voice-library-growth/product/naming-grows-the-library.md#rules)
details; it never proposes that step by itself.

## Parity between people and agents

The rule is shared by every feature, so the promise sets it:
[Parity between people and agents](../../../product/transcriber-promise.md#parity-between-people-and-agents).
This feature applies it to transcribing and to naming speakers later.

## Actors

- **A person** asks for the transcription and gives the names. Only a person
  gives a name; an agent may only propose one.
- **An agent**, meaning Claude Code or Codex as the promise names them, runs the
  commands, reads the result and proposes names.

## Data

Recordings and transcripts, as the transcriber already handles them. The
transcript also records, for each speaker, the time windows used to recognize
that speaker. These are times inside the recording, not audio. The feature adds
no new class of data.

## Preconditions

- The transcriber and its skill are installed on the PC, at the same version.
- Docker Desktop is running.
- The recording is on the PC, not only in an online folder.
- No other transcription is running on the same PC.

## Outcomes

**Transcribing succeeds.** The transcript's text and JSON files appear next to
the recording, as they do today. The command ends with a result summary that
the agent can read. When the transcriber fell back to the CPU, the summary says
so, as the files do.

**Transcribing fails for an ordinary reason.** The command gives a plain Italian
message saying what happened and what to do next, as the promise requires for
every message, and a machine-readable status in the summary. The agent can then
relay the message or act on it. Ordinary reasons are:

- an unreadable recording;
- Docker not running;
- the transcriber not installed;
- GPU memory running out;
- another transcription already running.

**Naming later succeeds.** Both transcript files show the new names, and nothing
else in them changes.

**Naming later fails.** A name given for a label the transcript does not contain
is refused with a message, and the files stay as they were. So is a name the
voice library growth rules stop, such as a name similar to a person already in
the library.

## Non-goals

- **No MCP server.** The users are agents that can run commands. An assistant
  without a shell, such as Claude Desktop or claude.ai, is not supported. The
  reasons are in
  [ADR 0003](../../../adr/0003-agents-use-a-command-line-and-a-skill.md).
- **No name without a person.** An agent never gives a name on its own.
- **One transcription at a time** and **no work on the text**, as the promise's
  [Non-goals](../../../product/transcriber-promise.md#non-goals) state.
- **No voice library changes.** Changes to the voice library belong to
  [voice library growth](../../voice-library-growth/product/naming-grows-the-library.md).

## Security screening

`security-new-subject-or-data`: dismissed. The agent is an actor already
declared in [Who acts](../../../product/transcriber-promise.md#who-acts), and
the speaker windows are times inside the transcript, a class already declared
in [Data classes](../../../product/personal-data-and-obligations.md#data-classes).
Whether a transcript reaches an agent's model provider is left to the person by
[No use policy](../../../product/transcriber-promise.md#no-use-policy).
