# Change: quality-manual-overlap

## Intent
Make recommendation quality manual-overlap reporting robust when manual reference playlists contain duplicate paths.

## Scope
- Update the pure quality reporting module only.
- Treat manual overlap as coverage of distinct manual reference tracks.
- Preserve manual prefix order matching as sequence-based.
- Add focused regression coverage.

## Out of scope
- Desktop/UI changes.
- Recommendation sequencing changes.
- Export format changes.
- Audio mutation, DSP, or Serato DB V2 writes.

## Risks
- Existing callers may have interpreted duplicates as weighted manual votes. Current code already uses set intersection, so the intended behavior is distinct-path overlap; this change aligns the denominator with that behavior.

## Rollback
Revert the quality helper and regression test.

## Success criteria
- Duplicate manual reference paths do not artificially lower `manual_overlap_ratio`.
- Empty manual references still return `0.0`.
- All focused and full verification gates pass.
