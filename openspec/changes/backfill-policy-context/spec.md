# Requirements
- GIVEN a generated recommendation, WHEN backfilling, THEN original hard energy,
  BPM, color, explicit/inferred genre and loudness eligibility applies.
- GIVEN anchor removal, reordering or a supplied color anchor, WHEN backfilling,
  THEN the originally resolved policy survives without binding another anchor.
- GIVEN an original genre fallback or missing energy anchor, WHEN backfilling,
  THEN the original documented fallback survives; no new strict genre policy.
- GIVEN preserved controls/current locks and exclusions, WHEN backfilling,
  THEN exclusions win, control exceptions survive, and surviving slots stay put.
- GIVEN a legacy recommendation without context, WHEN its policy needs original
  context, THEN generated backfill fails closed with a warning; removal remains.

- GIVEN an explicitly supplied replacement loudness band, WHEN backfilling, THEN
  that band overrides the saved band for this edit without rebinding other anchors.
  Desktop passes the current setting, preserving its existing behavior; direct
  callers without an override continue to use the saved generation-time band.
