# Transcription stays on the PC

The transcriber processes each recording on the PC where it runs, sends nothing
it reads or produces off that PC, and needs no network connection to transcribe.
Recordings carry the voices of the people in them together with what they
said, and naming speakers relies on voiceprints, so keeping every step on the
PC leaves no transfer, no third-party processor and no shared machine to
account for.

## Considered options

- **A company server with a GPU** that PCs send recordings to: fast for every
  PC, including those without an NVIDIA card, but recordings and voice data
  would travel over the network and be processed on a shared machine.
- **An external transcription service**: nothing to install locally, but
  recordings and voices would reach a third party.

## Consequences

- Every PC holds the whole system, models included: about 20 GB in Docker.
- A PC without an NVIDIA GPU transcribes on its CPU, which can take longer than
  the recording lasts.
- Central processing, such as a shared GPU server, stays excluded while this
  decision stands.
