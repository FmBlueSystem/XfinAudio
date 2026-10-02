# Requirements

## R1 Immutable equivalent snapshots
GIVEN ordered library records and cached spectral, danceability, edge, or loudness
results WHEN a UI tick applies pending results THEN both record views contain the
latest profile for each path, ordered rows and unrelated fields stay unchanged,
and earlier published states/records are unchanged. Unknown paths stay absent.

## R2 Bounded publication work
GIVEN many cached completions before a tick WHEN they are received THEN full
collection copying and state publication occur once per tick rather than once
per result. Repeated profile values coalesce to the latest result; loudness
progress still counts every delivered result up to its bounded total.

## R3 Timely and terminal results
GIVEN pending results WHEN the scheduled tick fires THEN spectral cells and
selected-track loudness details reflect the new snapshot without a full render.
GIVEN pending results WHEN a stage finishes/cancels or shutdown begins THEN already
received results are applied before completion or next-stage handoff. Replacing
library context cannot later replay pending values over the replacement library.

## R4 Row correctness after UI changes
GIVEN sort/filter/rebuild changes before delivery WHEN spectral color is painted
THEN only the current matching row is updated; a missing row is safely ignored.
Repeated result lookup does not linearly traverse Qt rows.

## R5 Preserved analysis and persistence contracts
GIVEN completed/persisted synthetic profiles WHEN published in a batch THEN their
profile values, cache versions, analysis order, loudness policy, and persistence
behavior remain the same. No table-model or audio-engine rewrite is required.
