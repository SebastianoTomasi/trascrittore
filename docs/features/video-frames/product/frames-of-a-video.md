# Frames of a video

**Status:** accepted

## Scope

This artifact states what a person gets when a recording is a video: frames of
the moments that matter, kept with the transcript, who takes them, when, and
how they are chosen, and the name an agent gives the transcript's folder. The
folder itself, and the move of the recording into it, are a promise of the
transcriber, in
[What an update must not break](../../../product/transcriber-promise.md#what-an-update-must-not-break).
Correcting misheard words, which uses the frames, stays in
[ADR 0007](../../../adr/0007-agents-correct-misheard-words-in-the-text.md).

## Dependencies

- [Agents](../../../product/transcriber-promise.md#agents) — frames are taken
  by an agent through a skill that ships with the transcriber, as the skill for
  correcting misheard words is.
- [Parity between people and agents](../../../product/transcriber-promise.md#parity-between-people-and-agents)
  — choosing frames and titling the folder need an agent's judgment, which the
  rule lets exist for agents only, so a person's path does neither.
- [Processing stays on the PC](../../../product/transcriber-promise.md#processing-stays-on-the-pc)
  — the transcriber has no language model and calls none off the PC, so it
  cannot judge which moments matter. That judgment is why only an agent takes
  frames.
- [What an update must not break](../../../product/transcriber-promise.md#what-an-update-must-not-break)
  — the frames go in the transcript's folder that the transcriber creates, and
  the agent renames that folder without renaming the files inside.
- [Data classes](../../../product/personal-data-and-obligations.md#data-classes)
  — frames are a class of personal data declared there, with where they live
  and how long they stay.
- [No use policy](../../../product/transcriber-promise.md#no-use-policy) — the
  frames an agent looks at may reach its model provider; that is the person's
  choice.

## Purpose

Once this feature exists, a video recording leaves, besides its transcript,
frames of the moments that matter: what a speaker shows, such as a product or a
service, and what appears on screen, such as names and other information that
nobody reads aloud. They serve two ends:

- **Context for an agent.** An agent working on the transcript reads the names
  and terms the frames show, for example to propose names for speakers or to
  correct misheard words.
- **A compact version of the video.** The transcript and its frames keep what
  was said and what was shown, in far less space than the video, so a person
  can keep them instead of it.

## Actors

- **An agent** titles the transcript's folder, chooses the moments and takes
  the frames.
- **A person** reads the frames and keeps or deletes them with the transcript.
  They may ask the agent to look at the screen more or less often.
- **The transcriber** takes no frames and gives the folder no title.

## Preconditions

- The recording is a video, transcribed by a version that writes the
  transcript's folder.
- ffmpeg can run on the PC: its own, or the one in the transcriber's image with
  Docker Desktop running.

## When

An agent that has transcribed a video works in this order, without asking:

1. it renames the transcript's folder, as below;
2. it takes the frames;
3. it proposes names for the speakers, using names shown on screen too. A
   person still gives every name.

When correcting misheard words, an agent reads the frames already kept first.
A frame it takes around a doubtful passage is kept only when it meets the rule
below; otherwise it is thrown away.

## The transcript's folder

The agent renames the folder to the date of the recording followed by a short
Italian title drawn from what was said, written without spaces as
[the transcriber writes names](../../../product/transcriber-promise.md#what-an-update-must-not-break),
such as `2026-10-29-demo-prodotto-acme`, so that folders sort by date and say
what each recording was. The date is when the recording was made, as its file
name or its file's date says. The files inside keep their names, which come
from the recording's. Without an agent, the folder keeps the recording's name
and the person may rename it.

The frames go in a `fotogrammi` folder inside it, at the video's full
resolution, each named after its time from the start of the recording, such as
`00-12-34.jpg`, which leads to the line of the transcript said at that time.

## Which moments

A frame is kept because of what it shows, not because of when: a moment matters
when something on screen goes with what is being said, or carries information
the transcript lacks, such as names on screen, even if it stays there only a
few seconds. No two kept frames show nearly the same image.

To find those moments, the agent uses all it has:

- the transcript, where speech refers to something on screen;
- the moments where the picture changes;
- frames looked at every 20 seconds, or as often as the person asks for that
  recording, so that it sees the screen even where nothing is said about it and
  nothing changes.

The agent looks at these candidates and keeps only those that matter. Looking
at a candidate does not keep it.

## Outcomes

- **Success.** The transcript's folder carries the date and a title, and its
  `fotogrammi` folder holds the frames of the moments that matter, none nearly
  the same as another. A video with nothing worth keeping on screen gets no
  `fotogrammi` folder, and the agent says so.
- **ffmpeg cannot run**, for example because Docker Desktop is not running.
  The agent tells the person it could not see the screen. The transcript and
  its folder stay as the transcriber wrote them, apart from the title.

## Deleting the video

Neither the transcriber nor an agent deletes the video or proposes deleting it.
A person who wants to keep only the transcript and its frames gives the names
first: naming reads the recording to cut voice clips, and without it a name is
applied but adds no clips.

## Videos transcribed earlier

A video transcribed before this feature has no folder of its own. When the
person asks for its frames, the agent proposes transcribing it again; the names
given earlier are not lost, since those voices are now in the voice library.

## Non-goals

- **Frames taken by the transcriber**, at fixed intervals or otherwise.
- **Frames kept because of time alone**, such as one every 20 seconds.
- **A setting for how often the agent looks**: the person asks the agent for one
  recording.
- **Frames in the transcript's files**: the text and JSON files do not list or
  mention them.

## Security screening

`security-new-subject-or-data`: this feature adds no actor, but it adds a
class of personal data, the frame, declared on 2026-10-29 in the project-wide
[Data classes](../../../product/personal-data-and-obligations.md#data-classes)
with where it lives and how long it stays. No Security control is added: frames
stay on the PC like the recording they come from, and where they go afterwards,
including to an agent's model provider, is the person's choice under
[No use policy](../../../product/transcriber-promise.md#no-use-policy).
