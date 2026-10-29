# When to run the recognition check again

**State:** closed
**Scope:** feature:voice-library-growth
**Destination:** implementation
**Revisit when:** the first trial ends, after 10 named speakers, and there are
at least two runs of the check to compare.

[The Product rules](../features/voice-library-growth/product/naming-grows-the-library.md#rules)
say the recognition check runs again after a number of additions and before
the trial ends. The number was left open in
[the implementation](../features/voice-library-growth/implementation/clip-selection-and-pools.md).

Today nothing counts additions. `Verifica.bat` runs the check and then the
trial report. `LEGGIMI.md` tells the person to use it "ogni tanto, dopo aver
dato qualche nome", and the agent skill tells the agent to suggest it after a
few new names. On 2026-09-25 the user chose to leave it at that for now.

It can wait: until the trial ends the person runs `Verifica.bat` anyway, and a
number chosen now would have no data behind it. After the first trial, how much
the check's scores and suggested threshold move between runs shows how many
additions are worth a new run.

Remaining questions:

- the number of named speakers, or of added clips, that makes a new run worth
  it;
- who says it is time: the `name` command's message, `Trascrivi.bat`, or only
  the agent skill.

## Resolution

Closed on 2026-10-29: the recognition check and `Verifica.bat` are gone,
replaced by the list of who spoke after every transcription, as
[ADR 0010](../adr/0010-the-list-of-who-spoke-replaces-the-recognition-check.md)
records. There is no check left to run again.
