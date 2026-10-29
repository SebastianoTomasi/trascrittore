# Library growth architecture

**Status:** accepted

## Scope

This artifact states where the clips of a named speaker come from, and how the
voice library holds the clips added from recordings: the pools they form, the
record that tells an added pool from one made by hand, and which clips the cap
may remove. Algorithms are left to
[the implementation](../implementation/clip-selection-and-pools.md).
The rules the person sees are in
[the Product artifact](../product/naming-grows-the-library.md).

## Dependencies

- [Rules](../product/naming-grows-the-library.md#rules) — this architecture
  realizes naming that adds to the library, recognized speakers confirmed or
  corrected on request, nothing saved without a name, the listening check, only
  the selected clips saved, a new pool for a missed recognition, and the caps
  on added clips.
- [Transcript JSON](../../agent-cli/architecture/agent-cli-architecture.md#transcript-json)
  — clips are cut from the windows that this contract adds to the transcript.
- [The transcript's folder](../../agent-cli/architecture/agent-cli-architecture.md#the-transcripts-folder)
  — a new pool takes its name from that folder, and the recording is looked for
  inside it.
- [Components](../../agent-cli/architecture/agent-cli-architecture.md#components)
  — every new command runs through the host launcher, which mounts the voice
  library writable only for the commands that change it: naming, and the
  removal of clips over the cap.
- [What an update must not break](../../../product/transcriber-promise.md#what-an-update-must-not-break)
  — the added clips live in folders that every version reads: one folder per
  person, with clips directly inside it or in subfolders.

## Where clips come from

When a speaker is named, or a recognized speaker is confirmed or corrected on
the person's request, clips are cut from the original recording using that
speaker's windows in the transcript JSON. The recording is looked for where the
transcript records it, then beside the transcript, so a folder the agent
renamed still finds it. No clip or voiceprint exists for a speaker before a
name is given or confirmed. When the recording or the windows are missing, or
the file found does not last as long as the transcript says, no clips are
added.

## Where added clips go

A person's clips taken from recordings go into subfolders of that person's
folder, the added pools. Each one is a pool for recognition, like any
subfolder, and holds a clip record, which is how the transcriber tells it from
a folder made by hand:

- `voci/<Nome>/registrazioni/`, the first added pool of a person;
- one pool per missed recognition, named after the transcript's folder, such
  as `voci/<Nome>/2026-10-29-demo-prodotto-acme/`.

Which pool a naming chooses follows the
[Product rules](../product/naming-grows-the-library.md#rules); the reasons for
a pool per miss are in
[ADR 0011](../../../adr/0011-a-missed-recognition-starts-a-new-pool.md). Each
clip's file name starts with the recording's name and ends with the time of the
window, both written without spaces, so a person can tell where each clip came
from.

Subfolders a person makes by hand for a recording condition, such as
`voci/<Nome>/macchina/` or `voci/<Nome>/telefono/`, stay pools of their own, as
they were before this feature, and never receive clips from a naming. A person
may move clips from an added pool into such a folder, and may rename an added
pool, since its record goes with it.

Recognition reads only the folders and the audio files in them, as before this
feature. The clip record below is never needed to recognize anyone.

## Clip record

Each added pool holds `clip.json`, a record of every clip saved there: the
recording and the transcript it came from, the speaker's label in that
transcript, the window's times, and how much the clip resembles the rest of the
speaker's voice. The record serves the cap and tells added pools apart, and it
goes away with its folder. When the transcriber next writes a record, it drops
the entries of clips the person deleted.

## Clips over the cap

The cap counts, in each added pool, the clips that have an entry in its clip
record. Only those clips can be proposed for removal; a clip placed by hand,
in any folder, never is. A proposal names the pool and the clips by file name,
and a removal deletes only clips the person confirmed that are still in one of
that person's added pools. A file name found in more than one of them is
refused, since the person could not tell which one they confirmed.
