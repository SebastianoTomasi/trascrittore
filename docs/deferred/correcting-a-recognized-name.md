# Correcting a wrongly recognized name

**State:** open
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

[Adding clips from a recognized speaker](clips-from-recognized-speakers.md)
uses the same command on the same labels, and
[listening to recognized speakers](listening-to-more-clips.md) is the first
step of both; design them together.
