# Score normalization for voice recognition

**State:** open
**Scope:** feature:voice-library-growth
**Destination:** implementation
**Revisit when:** the recognition check, run on the libraries in use, shows
wrong names or missed recognitions that adjusting the threshold and margin
cannot remove.

Recognition gives a speaker a person's name when the best raw similarity score
reaches `matching.threshold` and beats the second-best person by
`matching.margin`, as
[the implementation](../features/voice-library-growth/implementation/clip-selection-and-recognition-check.md#how-recognition-scores-today)
describes. Score normalization, for example S-norm or AS-norm against a cohort
of impostor voices, could make the scores of different people comparable and
the threshold more stable as libraries grow.

It was considered and postponed while voice library growth was designed: the
recognition check had to exist first, so that normalization could be judged by
its results. The Product artifact records this as the non-goal
[No score normalization for now](../features/voice-library-growth/product/naming-grows-the-library.md#non-goals).

Adopting it changes the score scale, so the threshold and margin in the
defaults, and any threshold a person wrote in `trascrittore.ini`, would need a
new calibration. That would also have to be decided before release.
