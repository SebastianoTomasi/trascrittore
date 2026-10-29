# What the transcriber promises

**Status:** accepted

## Scope

This artifact states what the transcriber is for, who uses it and in which
role, the parties it involves, what they can observe it doing, what it
deliberately does not do, what an update must not break, and how someone can
check from outside that it keeps its claim. The classes of personal data it
handles and the external obligations that bind it are in
[Personal data and external obligations](personal-data-and-obligations.md).
Step-by-step interaction belongs to Frontend, the
realization to Architecture and Implementation, and how the transcriber is
delivered to its users to Deployment.

## Purpose

The transcriber turns a recording — any audio or video file in which people
speak — into a transcript that says who spoke, when, and what they said.
Meetings are one use among many, so its promises are stated for recordings in
general.

It is a personal tool, not a work tool: general, and agnostic of what its
users do with it. What that leaves to them is under
[No use policy](#no-use-policy).

Without it, someone who needs a written record of a recording has to listen to
it again and write it down, or send the recording, with the voices of the
people in it, to an external service.

### Processing stays on the PC

The transcriber processes a recording entirely on the PC where it runs. It
sends nothing it reads or produces anywhere, and it needs no network connection
to transcribe. Files that a person moves on their own initiative, for example
to a shared drive or by email, are outside this promise. The reasons and the
rejected alternatives are in
[ADR 0001](../adr/0001-transcription-stays-on-the-pc.md).

## Users

### People close to the maintainer

The transcriber is for people the maintainer knows personally and can help
directly, not for strangers. Most of them are technical, but using it must stay
easy for someone who is not: transcribing a recording must require neither a
command line nor any knowledge of the tools inside, and its messages must say
in plain words what happened and what to do next. When something goes wrong
beyond that, the maintainer helps directly, so the guide does not have to cover
every case.

### Agents

AI coding agents, namely Claude Code and Codex, are primary users as well: a
person can ask their agent to transcribe a recording. The transcriber therefore
offers a command-line interface that an agent can use on its own and a skill
that tells the agent how to use it. A second skill tells the agent how to
correct misheard words in a transcript, which is the agent's work on the text,
as [Non-goals](#non-goals) state.
[Transcribing through an agent](../features/agent-cli/product/transcribing-through-an-agent.md)
details what an agent can do with them.

#### Parity between people and agents

A person and an agent use the same commands, which ask no questions: the
person's scripts, such as `Trascrivi.bat`, call the commands an agent calls,
and someone at ease with a command line can call them directly. Transcribing a
recording and naming speakers also have a path without a command line, and
neither is finished until that path exists. Anything
else may exist for agents only: work that needs an agent's judgment, such as
correcting misheard words or choosing the frames of a video, and commands that
no script of the person exposes. The reasons are in
[ADR 0008](../adr/0008-agents-may-do-what-a-person-s-path-does-not.md).

### What users are assumed to have

- A PC with Windows 10 or 11. Linux and macOS are not supported, so an agent
  that uses the transcriber runs on Windows itself rather than inside WSL.
- The rights to install software on that PC, since the transcriber currently
  needs Docker Desktop, and about 30 GB of free disk space.
- Optionally an NVIDIA GPU. Without one, transcription still works, only much
  more slowly.
- The ability to read Italian, the language the transcriber and its guide use.

## Parties

### Who acts

- **A person** transcribes recordings on their own PC and manages that PC's
  voice library.
- **An agent** transcribes on a person's behalf, on that person's PC.
- **The maintainer** builds and distributes the transcriber, helps the people
  who use it, tunes how it recognizes voices, and may send voice clips to start
  a library.

### Whose data passes through it

- **Speakers** heard in a recording, including people who know nothing of the
  transcriber.
- **People in a voice library**, whose voice clips let the transcriber
  recognize them.

Neither group acts on the transcriber.

### One voice library per PC

Each PC has its own voice library, managed by the person who uses that PC:
they decide whose voices it holds. The library grows in two ways: the person
places voice clips in it, and naming a speaker adds clips of that speaker's
voice. Naming covers a speaker the transcriber did not recognize and, only when
the person asks, confirming or correcting one it recognized, as
[Naming a speaker grows the voice library](../features/voice-library-growth/product/naming-grows-the-library.md)
details. Voice clips sent by the maintainer are only a starting point. There is
no shared library.

### No use policy

The transcriber imposes no consent step and no other rule of use: it
recognizes whoever has voice clips in the library of the PC where it runs.
Whoever uses it answers for how they use it: which recordings they transcribe,
whose voices they put in the library, and where transcripts, and what an agent
sees of a recording, go afterwards, including to that agent's model provider.
The reasons and the rejected alternatives are in
[ADR 0002](../adr/0002-personal-tool-without-use-policy.md).

## Capabilities

What someone can observe the transcriber doing. A capability that a feature
details links to it.

- **Transcribe a recording.** Given one recording in a common audio or video
  format, the transcriber writes a transcript in Italian, a text to read and a
  JSON file for programs, in a folder of its own next to the recording, and
  moves the recording into it. Each turn carries the time from the start of the
  recording and who spoke.
- **Tell speakers apart.** It separates the voices by itself; the person can
  state the exact number of speakers to help it.
- **Recognize known voices.** Speakers who are in the PC's voice library appear
  under their name. When recognition is not sure enough, the speaker appears
  as "Persona N", because a wrong name is worse than none. Words it cannot
  attribute to any speaker appear as "Voce non attribuita".
- **Name speakers.** A person can give a name to each
  "Persona N", seeing two of their sentences as a reminder, and, when they ask,
  confirm or correct a name the transcriber gave. Naming also adds clips of
  that speaker's voice to the voice library, as
  [Naming a speaker grows the voice library](../features/voice-library-growth/product/naming-grows-the-library.md)
  details.
- **Keep a voice library.** A person adds someone by creating a folder with
  their name and at least three voice clips, and removes them by deleting the
  folder.
- **Transcribe through an agent.** An agent transcribes a recording without
  asking questions, reads a summary of the result, and later gives speakers the
  names the person confirms, as
  [Transcribing through an agent](../features/agent-cli/product/transcribing-through-an-agent.md)
  details.
- **Work with or without a GPU.** On a supported NVIDIA GPU, transcription,
  alignment, speaker separation and recognition use that GPU. The transcriber
  does not present a mixed GPU/CPU run as the solution for such a PC. A PC
  without an NVIDIA GPU can still transcribe on its CPU, with a warning about
  the slower processing. It says which device was used on screen and in the
  transcript.
- **Explain what went wrong.** Ordinary problems, such as an unreadable
  recording, Docker not running, the transcriber not installed or GPU memory
  running out, end with a plain message saying what to do.
- **Install and update from files.** One installer checks the PC's NVIDIA GPU
  and loads the CUDA 12.8 image from a local release file. It supports GPUs
  such as the RTX 2070 and RTX 5070. Older NVIDIA GPUs, including the MX230,
  are outside the supported range because transcription on the MX230 proved too
  slow to be useful. Installation reports whether the image can actually use
  the GPU. The delivery and verification rules are in
  [GPU installation](../deployment/gpu-installation.md).
- **Adjust settings without a new version.** A person changes processing and
  recognition settings by writing them in `trascrittore.ini`, next to the
  scripts.

## Non-goals

- **Languages other than Italian.** A recording in another language is outside
  what the transcriber promises.
- **Operating systems other than Windows**, as
  [What users are assumed to have](#what-users-are-assumed-to-have) states.
- **Processing off the PC**, on a server or through an external service, as
  [ADR 0001](../adr/0001-transcription-stays-on-the-pc.md) records.
- **Live transcription.** The transcriber works on recordings that already
  exist, not on speech as it happens.
- **Work on the text.** Minutes, summaries, action items and the correction of
  misheard words are the work of an agent or of the person, done on the
  transcript, not the transcriber's. The transcriber only ships the skill that
  tells an agent how to correct misheard words, as
  [ADR 0007](../adr/0007-agents-correct-misheard-words-in-the-text.md) records.
  Correcting is agent work that a person's path does not offer, as
  [parity](#parity-between-people-and-agents) allows: a person corrects the
  text by hand.
- **More than one transcription at a time on a PC.** Recordings are transcribed
  one after another.
- **A shared voice library**, as [One voice library per PC](#one-voice-library-per-pc)
  states.
- **A use policy**, such as a consent step, as [No use policy](#no-use-policy)
  states.
- **Users beyond the people close to the maintainer**, including use as a work
  tool, as [ADR 0002](../adr/0002-personal-tool-without-use-policy.md) records.

## What an update must not break

An update may break anything not listed here. When one does, the maintainer
tells the people who use the transcriber to reinstall it: for a few people the
maintainer can help directly, an occasional reinstall costs less than the
development needed to keep everything from earlier versions working. A change
that keeps everything listed is therefore ordinary, even when it requires a
reinstall; a change that breaks something listed is a breaking change.

- **The voice library.** No update touches it, not even a reinstall, and every
  version reads libraries organized as today: one folder per person, named as
  the name should appear, with voice clips directly inside it or in subfolders.
- **Transcripts already written.** No update changes them. When a newer command
  cannot do all its work on an older transcript, for example adding a named
  speaker's voice clips to the voice library, it says what it could not do and
  suggests transcribing the recording again.
- **Where transcripts go.** The transcriber writes the names of what it
  creates without spaces: lowercase, without accents, with a hyphen in place of
  every run of other characters, so the recording `2026-10-29 14-30-12.mkv`
  gives `2026-10-29-14-30-12`. A transcript is written as
  `<name>-trascrizione.txt` and `.json` in a folder `<name>`, where `<name>` is
  the recording's name written that way, next to the recording unless the
  person chooses another place for it. At the end of a successful transcription
  the recording moves into that folder as `<name>` with its extension, unless
  the person chose another place; transcribing it again there writes in the
  same folder. An agent may give the folder another name, written the same way,
  as
  [Frames of a video](../features/video-frames/product/frames-of-a-video.md#the-transcripts-folder)
  states; the files inside keep theirs. The reasons for moving the recording
  are in [ADR 0009](../adr/0009-the-recording-moves-into-its-transcript-s-folder.md).
- **The person's settings.** `trascrittore.ini` holds only what the person
  changed; everything else comes from the transcriber itself. No update changes
  that file, and each update brings new defaults for everything the person did
  not change. When the file holds a line the new version does not understand,
  the transcriber says which line to correct instead of stopping without
  explanation.
- **Commands and skills together.** The skills always ship with the
  transcriber of the same version, so changing a command is ordinary when the
  skill that describes it changes with it.

For example, any update may change the layout of the text file, the fields of
the JSON file, and whatever the transcriber keeps for itself and can rebuild,
such as voiceprints.

## How to check that it works

Each check can be made from outside, without reading the code.

- **Nothing leaves the PC.** With the PC disconnected from the internet, a
  transcription succeeds and gives the same transcript as when it is connected.
- **No wrong names.** On recordings whose speakers the person knows, the list
  of who spoke after each transcription, which
  [Naming a speaker grows the voice library](../features/voice-library-growth/product/naming-grows-the-library.md#rules)
  requires, shows no one under someone else's name, and voices missing from the
  library stay "Persona N". The maintainer made this test by hand when
  calibrating the settings on 2026-09-24.
- **Easy without help.** Someone who is not technical installs the transcriber
  and transcribes a recording by following only its guide.
- **Parity.** For transcribing and naming speakers, a person without a command
  line and an agent using commands that ask no questions reach the same result.
