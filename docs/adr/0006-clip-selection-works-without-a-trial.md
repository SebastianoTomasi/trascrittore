# The clip selection works without a trial

From the first naming, the voice library takes only the clips the automatic
selection keeps: at most 8 per speaker and recording, none below the minimum
consistency. Until 2026-10-22 the selection had to pass a trial first: every
candidate clip was saved with the selection's vote, the person deleted the bad
ones, and after 10 named speakers without a disagreement the person confirmed
the review. We dropped it because reviewing every clip of 10 speakers by hand
asked the person too much, and the listening check before naming already stops
the worst error, a whole speaker given the wrong name.

## Considered options

- **Keep the trial**: it would confirm the selection's settings before trusting
  them, at the cost of a review few people would finish.
- **Save every candidate clip, with no selection**: it needs no settings to
  trust, but with nobody reviewing the clips, those with other voices, laughter
  or noise would stay in the library.

## Consequences

- The selection's settings, 8 clips and a minimum consistency of 0.60, were a
  first guess the trial was meant to confirm, and no review has confirmed them.
  A bad clip can reach the library unseen; that is the accepted price.
- The cap on added clips and its proposals apply from the first naming.
- Naming opens no folder: the person can still find the added clips, and delete
  a bad one, through the folder the result gives.
- Votes in clip records and the trial result already on a PC are ignored, not
  cleaned up. A clip record outlives the deleted clip, because the recognition
  check finds the named transcripts through it.
