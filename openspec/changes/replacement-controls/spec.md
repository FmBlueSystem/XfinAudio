# Requirements
- GIVEN an excluded candidate, WHEN backfilling directly or in the desktop,
  THEN that candidate is never selected, even when it is the only alternative.
- GIVEN original DJ genre and anchor/manual/locked controls, WHEN removing a track,
  THEN backfill uses that policy, and leaves surviving playlist positions intact.
- GIVEN newly excluded tracks or earlier removals, WHEN backfilling again,
  THEN those tracks remain blocked. Explicit removal remains available for anchors.
- GIVEN a genre request, WHEN producing a recommendation, THEN its applied
  metadata retains that request for subsequent operations.
