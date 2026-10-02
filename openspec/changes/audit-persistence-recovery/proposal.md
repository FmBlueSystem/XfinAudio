# Audit persistence recovery

Intent: close CQ-2, CQ-4 and CQ-5 from the 2026-09-30 audit without changing audio, Serato, DSP or recommendation behavior.
Scope: atomic settings replacement, explicit startup recovery with preserved invalid bytes and visible diagnostics, settings-dialog save failure handling, playlist foreign-key enforcement and orphan migration, deterministic SQLite connection disposal.
Out: broad state refactors, non-Serato improvements, publication or deployment.
Risks: recovery must never overwrite an unreadable/unsupported future configuration; SQLite migration must preserve valid playlists and ordering.
Rollback: revert individual code commits; invalid settings are preserved alongside their original location; orphan cleanup removes references with no parent only.
Success: failure-injection and migration regressions pass, bounded connection ownership, full configured release gate passes.

## Explicit chained-PR delivery plan
The complete audit exceeds 400 changed lines. Local commits form reviewable future PR slices (no PR creation authorized):
1. Atomic settings writes and failure-injection tests.
2. Recoverable malformed-settings startup and actionable UI save errors.
3. SQLite deterministic connection lifecycle and playlist orphan migration.
4. Integrated verification evidence only.
Each production slice targets <=400 changed lines; artifacts belong to the shared chain. No broad architectural rewrite.
