# Warning for near-duplicate names

**State:** open
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

Remaining questions:

- how similar counts as "near": edit distance, a shared surname, or a
  first name alone;
- how the warning works for both paths, since commands ask nothing: the
  person's path can ask in `Trascrivi.bat`, while for an agent the `name`
  command could end with its own status and list the similar names, so the
  agent asks the person.
