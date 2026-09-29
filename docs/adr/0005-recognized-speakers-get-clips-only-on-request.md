# Recognized speakers get clips only on the person's request

A speaker the transcriber recognized can have clips added to the voice library,
either to the same person when the person confirms the name, or to another
person when the person corrects it. This happens only when the person asks for
it explicitly, and only after they hear the speaker and confirm the voice.
Until 2026-09-29 no clip was ever added for a recognized speaker, so that a
wrong recognition could not feed itself. That reason does not hold once a
person listens and confirms, which is the same guard that already protects the
naming of an anonymous speaker.

## Considered options

- **No clips for recognized speakers, ever**, the rule of 2026-09-25: it keeps
  a wrong recognition out of the library, but leaves no way to strengthen a
  person recognized close to the threshold or in a new recording condition,
  and no way to fix a wrong name beyond editing the text by hand.
- **Correcting the transcript only, without clips**: it fixes the text but not
  the library that produced the wrong name.
- **Offering the step after every run, or having the agent propose it**: it
  would turn a rare correction into a routine question, and confirmations made
  by habit would weaken the guard.

## Consequences

- Neither the transcriber nor an agent starts or offers this step; the person
  asks for it.
- Clips from a recording where the person was already recognized well add
  little and can tilt their single `registrazioni` pool
  ([ADR 0004](0004-added-clips-form-one-pool-per-person.md)) towards one
  microphone, so the command shows the recognition score first and says how
  much new clips would help.
- The clips of a person recognized in place of someone else are left as they
  are; the person is told to listen to them and to run the recognition check.
