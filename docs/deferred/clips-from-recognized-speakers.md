# Adding clips from a recognized speaker

**State:** closed
**Scope:** feature:voice-library-growth
**Destination:** product
**Revisit when:** [correcting a wrongly recognized name](correcting-a-recognized-name.md)
is taken up, since both use the same command, or sooner if the recognition
check shows a person recognized close to the threshold or missed in a new
recording condition.

On 2026-09-25 the user asked whether a person can get more clips of a speaker
the transcriber recognized, for example of themselves, by giving `name` a label
other than "Persona N". It was postponed for lack of time.

Today it cannot. `_check_labels` in `src/transcriber/naming.py` refuses a label
that already holds a name, following two accepted rules of
[Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules),
"Only speakers left as Persona N are named" and "No clips for speakers
recognized automatically", and the non-goal "No clips from speakers recognized
automatically". Their reason is that a wrong recognition cannot feed itself.
Changing them changes an accepted rule, so the answer goes through
`advisor-propagate-change`.

The agent's assessment, not a decision: that reason largely falls when the
person listens and confirms, which is the same guard that protects the naming
of a "Persona N". Clips from a recognized speaker could then be added only
after an explicit confirmation, never automatically.

## Progress

On 2026-09-29 the user chose to allow clips from a recognized speaker after
the listening check and an explicit confirmation. It happens only when the
person asks for it explicitly, for example "vorrei aggiungere delle clip di
Sebastiano"; neither the transcriber nor the agent starts it or offers it by
itself. For parity, the person's path is `Trascrivi.bat` when a
transcript's JSON file is dropped on it: besides the questions on "Persona N",
it asks whether to confirm or correct a recognized speaker. The questions at
the end of a run stay as they are.
When the person confirms a recognized speaker, the clips are added even when
they help little, since the person asked. Before that, the command shows the
recognition score and says plainly whether new clips help little (score well
above `matching.threshold`) or much (score close to it). During the trial,
speakers confirmed or corrected this way count towards the 10 named speakers
like any other, since their clips go through the same selection and listening.
The accepted rules above stay in force until the whole change is
settled and propagated.

Questions to settle:

- **The command.** A confirmation that reads clearly, for example
  `name <transcript.json> --conferma "Sebastiano Tomasi"` or a command of its
  own, rather than `"Sebastiano Tomasi=Sebastiano Tomasi"`. A pair such as
  `"Sebastiano Tomasi=Antonio Gassner"` on a recognized label is the case of
  [correcting a wrongly recognized name](correcting-a-recognized-name.md), so
  one syntax should serve both.
- **When it is worth it.** Clips from a recording where the person was already
  recognized well add little, and can make their `registrazioni` pool depend on
  one recording or one microphone, since added clips form a single pool
  ([ADR 0004](../adr/0004-added-clips-form-one-pool-per-person.md)) and there
  is no [cap on clips per person](clip-cap-per-person.md) yet. The command
  could show the recognition score against `matching.threshold` and say when
  new clips would help little. They help most when the score is close to the
  threshold or the recording condition is new.
- **The trial.** Whether such clips count towards the named speakers the
  [trial period](../features/voice-library-growth/product/naming-grows-the-library.md#rules)
  needs, since they were confirmed but not named.
- **Listening first.** It needs `listen` to accept recognized speakers, which
  [Listening to more clips, and to recognized speakers](listening-to-more-clips.md)
  covers.

## Resolution

Settled on 2026-09-29 as recorded above. The rule is in
[Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules) ("A recognized speaker changes only on the
person's request", and the trial), with the reasons in
[ADR 0005](../adr/0005-recognized-speakers-get-clips-only-on-request.md).
