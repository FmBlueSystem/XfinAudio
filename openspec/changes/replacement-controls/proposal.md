# Preserve replacement controls
Restore the original DJ constraints during slot backfill. Excluded tracks must
never return; genre and explicit anchor/locked/manual policy must survive.
Scope: recommendation metadata, replacement helper, desktop candidate filtering.
No audio, Serato, export, or scoring-policy changes. Roll back this slice if needed.
Success: direct helper and synthetic desktop regression tests pass; <400 lines.
