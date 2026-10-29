# Agents may do what a person's path does not

A person and an agent use the same commands of the transcriber, but they no
longer have to reach the same results. Transcribing a recording and naming
speakers keep a path without a command line, because people who are not
technical must manage them alone. Anything else may exist
for agents only: work that needs an agent's judgment, such as correcting
misheard words or choosing the frames of a video worth keeping, and commands
that no script of the person exposes.

Some useful work needs judgment about what was said. The transcriber cannot
give it: it has no language model and calls none off the PC, as
[ADR 0001](0001-transcription-stays-on-the-pc.md) requires. A person's path
built without that judgment would do the work worse, for example frames taken
at fixed intervals, which repeat a slide that stays on screen and miss what is
shown for a few seconds. For the few people close to the maintainer, a path
for people that copies every agent capability costs more than it gives.

## Considered options

- **Keep full parity**, so every capability has both paths: rejected on
  2026-10-29, because frames would have to be chosen by time alone, as said
  above.
- **Declare each piece of agent work "not a capability"**, as
  [ADR 0007](0007-agents-correct-misheard-words-in-the-text.md) did for
  correcting misheard words: rejected on 2026-10-29, because it keeps a rule
  that is no longer true and hides where the two paths differ.

## Consequences

- A person without an agent transcribes and names speakers. Frames,
  corrections and other agent work they do by hand, or ask someone to do.
- Every command can still be called by a person at ease with a command line.
- The guide for people says what only an agent does.
