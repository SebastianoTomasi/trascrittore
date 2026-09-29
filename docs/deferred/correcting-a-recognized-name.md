# Correcting a wrongly recognized name

**State:** closed
**Scope:** feature:voice-library-growth
**Destination:** product
**Revisit when:** a person finds a speaker recognized with the wrong name and
wants the transcript fixed.

The `name` command names only speakers left as "Persona N":
`_check_labels` in `src/transcriber/naming.py` refuses a label that already
holds a name. So when recognition gives a speaker the wrong person's name, no
command corrects it. The person can only edit the text file by hand, and the
JSON keeps the wrong name.

On 2026-09-25 the user chose to postpone this. It can wait for three reasons:

- the threshold and margin are set so that a wrong name is rarer than
  "Persona N";
- the recognition check measures and reports wrong names;
- the check takes as truth only the names a person gave (`named` in the JSON),
  so a wrong automatic name never counts as right.

Constraints already established:

- [No clips for speakers recognized automatically](../features/voice-library-growth/product/naming-grows-the-library.md#rules),
  so that a wrong recognition cannot feed itself.
- A name applies only after a person confirms it, with the listening check
  before any clip is saved.

Options discussed:

- correct only the transcript files, and add no clips;
- correct the transcript and, after the listening check, add the clips to the
  right person;
- in both cases, consider whether the wrongly matched person's pool needs a
  look, since it scored above the threshold for someone else's voice.

## Progress

On 2026-09-29 the user chose that a recognized name can be corrected, and that
the clips then go to the right person after the listening check. It happens
only when the person asks for it explicitly, for example by telling the agent;
neither the transcriber nor the agent starts it or offers it by itself. For parity, the person's path is
`Trascrivi.bat` when a transcript's JSON file is dropped on it: besides the
questions on "Persona N", it asks whether to confirm or correct a recognized
speaker. The questions at the end of a run stay as they are.
The wrongly matched person's clips are left untouched: the message says who was
recognized in place of whom and suggests listening to that person's clips and
running the recognition check again. The
accepted rules above stay in force until the whole change is settled and
propagated.

[Adding clips from a recognized speaker](clips-from-recognized-speakers.md)
uses the same command on the same labels, and
[listening to recognized speakers](listening-to-more-clips.md) is the first
step of both; design them together.

## Resolution

Settled on 2026-09-29 as recorded above. The rule is in
[Naming grows the library](../features/voice-library-growth/product/naming-grows-the-library.md#rules) ("A recognized speaker changes only on the
person's request"), with the reasons in
[ADR 0005](../adr/0005-recognized-speakers-get-clips-only-on-request.md) and
the commands in
[Naming speakers later](../features/agent-cli/frontend/agent-command-surface.md#naming-speakers-later).
