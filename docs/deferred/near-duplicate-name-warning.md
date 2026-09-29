# Warning for near-duplicate names

**State:** closed
**Scope:** feature:voice-library-growth
**Destination:** product
**Revisit when:** a person ends up with two folders in `voci` for the same
voice, or the recognition check shows one person split across two names.

When a person names a speaker, the clips go to `voci/<Nome>/registrazioni`.
Two folders for one voice break recognition of that person: their clips split
into two pools that compete, and the margin between them may never be reached.

Today only differences of case and spacing are caught.
`canonical_name` in `src/transcriber/library.py` reuses an existing folder
whose name differs only in case or spacing ("marco  rossi" goes to
"Marco Rossi"), and the message says so. The user confirmed this behavior on
2026-09-25. A typo or a different form of the name ("Marco Rosi", "Marco",
"M. Rossi") still creates a new folder.

The idea is a warning such as "Intendevi Marco Rossi?" before the clips are
saved. It was listed as proposed in
[the Product artifact](../features/voice-library-growth/product/naming-grows-the-library.md),
and on 2026-09-25 the user chose to postpone it. It can wait: people name few
speakers, and they can merge two folders by hand.

## Progress

On 2026-09-29 the user chose:

- **Stop before saving.** A name similar to a folder in the library saves
  nothing until the person decides. `Trascrivi.bat` asks "Intendevi Marco
  Rossi?". The `name` command ends with a status of its own that lists the
  similar names; the agent asks the person and runs it again with the chosen
  name, or with an option confirming a new person.
- **What counts as similar:** a name that differs by one or two letters, the
  same surname with the first name reduced to an initial ("M. Rossi"), or a
  first name alone that is the first name of a person in the library
  ("Marco"). Differences of case and spacing keep going to the existing folder
  as today.

The questions below are answered by these choices; the Product rule "One folder
per person" still needs to be amended.

Former questions:

- how similar counts as "near": edit distance, a shared surname, or a
  first name alone;
- how the warning works for both paths, since commands ask nothing: the
  person's path can ask in `Trascrivi.bat`, while for an agent the `name`
  command could end with its own status and list the similar names, so the
  agent asks the person.

## Resolution

Settled on 2026-09-29 as recorded above. The rule is in
[Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules) ("Similar names stop the naming"), and the
matching in
[Similar names](../features/voice-library-growth/implementation/clip-selection-and-recognition-check.md#similar-names).
