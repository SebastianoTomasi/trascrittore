# Library growth architecture

**Status:** accepted

## Scope

This artifact states where the clips of a named speaker come from, and how the
voice library holds the clips added from recordings. It also states what the
recognition check must keep. Algorithms are left to
[the implementation](../implementation/clip-selection-and-recognition-check.md).
The rules the person sees are in
[the Product artifact](../product/naming-grows-the-library.md).

## Dependencies

- [Rules](../product/naming-grows-the-library.md#rules) — this architecture
  realizes naming that adds to the library, recognized speakers confirmed or
  corrected on request, nothing saved without a name, the listening check, only
  the selected clips saved, the cap on added clips and the recognition check.
- [Transcript JSON](../../agent-cli/architecture/agent-cli-architecture.md#transcript-json)
  — clips are cut from the windows that this contract adds to the transcript.
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
speaker's windows in the transcript JSON. No clip or voiceprint exists for a
speaker before a name is given or confirmed. When the recording or the windows are missing,
or the file found does not last as long as the transcript says, no clips are
added.

## Where added clips go

A person's clips taken from recordings go into one subfolder of that person's
folder, `voci/<Nome>/registrazioni/`, and form a single pool. Each file name
starts with the name of the recording and ends with the time of the window, so
a person can tell where each clip came from. The reasons and the measurement
behind a single pool are in
[ADR 0004](../../../adr/0004-added-clips-form-one-pool-per-person.md).

Subfolders a person makes by hand for a recording condition, such as
`voci/<Nome>/macchina/` or `voci/<Nome>/telefono/`, stay pools of their own, as
they were before this feature. `registrazioni` is one more pool beside them, and
a person may move clips from it into a condition folder.

Recognition reads only the folders and the audio files in them, as before this
feature. The clip record below is never needed to recognize anyone.

## Clip record

Each person's `registrazioni` folder holds `clip.json`, a record of every clip
saved there: the recording and the transcript it came from, the speaker's label
in that transcript, the window's times, and how much the clip resembles the
rest of the speaker's voice. The record serves the cap and the recognition
check, and it goes away with the person's folder. The entry of a clip the
person deleted stays, so the check still finds the transcript it came from.
Records written before
[ADR 0006](../../../adr/0006-clip-selection-works-without-a-trial.md) also
hold the selection's vote, which nothing reads any more.

## Clips over the cap

The cap counts the clips in a person's `registrazioni` folder that have an
entry in its clip record. Only those clips can be proposed for removal; a clip
placed by hand, in any folder, never is. A proposal names the clips by file
name, and a removal deletes only clips the person confirmed that are still in
the folder.

## Recognition check

The check runs on the PC whose library it measures. It reads that PC's named
transcripts and their recordings: those listed in the clip records, and any the
person or the agent gives it.

When the check scores a recording, it leaves out of the library every clip cut
from that recording, recognized by the recording's name at the start of the
clip's file name. A clip that lost its record, or was moved, is still left out,
so no speaker is matched against their own clips.

The check reads the configuration and suggests a threshold, but it never writes
`trascrittore.ini`.
