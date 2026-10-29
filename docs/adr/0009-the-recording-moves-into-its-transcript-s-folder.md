# The recording moves into its transcript's folder

At the end of a successful transcription, the transcriber writes the
transcript in a folder named after the recording and moves the recording into
it. Until 2026-10-29 the transcriber never moved a recording, and wrote the
transcript's files next to it. Recordings land where the recording program
saves them, such as the OBS folder, so after a few transcriptions that folder
mixed recordings, transcripts and, with
[frames](../features/video-frames/product/frames-of-a-video.md), folders of
images, and nobody could tell what belonged to what. One folder per recording
keeps together everything that came from it.

## Considered options

- **Leave the recording where it is and write only the transcript's folder**:
  the recording program's folder would still fill with recordings next to
  folders of transcripts.
- **Let the agent move it**: a person without an agent would keep the mixed
  folder, and the problem is the same for everyone.

## Consequences

- A recording dropped on `Trascrivi.bat` is no longer where it was after the
  transcription; the closing message says where it went. It also takes its
  name written without spaces, like its folder and the transcript's files, as
  the user chose the same day to keep the names the transcriber creates
  programmatic.
- When the person chooses another place for the transcript, the recording
  stays where it is, since moving a large file to another place was not asked.
- A failed transcription moves nothing. When the move fails, for example
  because the recording is open in a player, the transcript is still written
  and the message says so.
- Commands that read the recording later, such as naming, look for it inside
  the transcript's folder too, because a renamed folder leaves the path the
  transcript recorded behind.
