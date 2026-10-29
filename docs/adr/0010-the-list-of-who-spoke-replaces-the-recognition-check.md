# The list of who spoke replaces the recognition check

After each transcription the person sees who spoke, recognized names and
"Persona N" alike, with how long each spoke, and is told to say if a name is
wrong. There is no longer a recognition check, the command and `Verifica.bat`
that replayed a PC's named recordings against its voice library and suggested
a threshold. The check was never used, and it needed the recordings
themselves, which a person may now delete once a video's transcript and
[frames](../features/video-frames/product/frames-of-a-video.md) keep what they
need. A wrong name is found by the person who knows who was there, at the
moment they read the transcript.

## Considered options

- **Keep the check as it was**: it rereads every named recording, so each
  deleted video drops out of it, and nobody ran it.
- **Keep the check without the recordings**, by storing each named speaker's
  voiceprint when they are named: it keeps more biometric data on the PC for a
  check nobody ran.

## Consequences

- Agreeing with the list, or saying nothing, changes nothing and adds no clips,
  so [ADR 0005](0005-recognized-speakers-get-clips-only-on-request.md) still
  holds: clips of a recognized person are added only on the person's explicit
  request, and saying that a name is wrong is such a request.
- The threshold stays as the maintainer calibrated it on 2026-09-24. The
  maintainer tunes it by hand when people report wrong names; nothing suggests a
  value to a person.
- Nothing measures how a change to the voice library or to recognition moves
  the scores on a PC, such as the pools of
  [ADR 0004](0004-added-clips-form-one-pool-per-person.md) and
  [ADR 0011](0011-a-missed-recognition-starts-a-new-pool.md).
- Clip records no longer keep the entries of deleted clips, which only the
  check read.
