# Proposal: Granular DJ Readiness Blocking

## Intent

Distinguish between hard blockers (data integrity) and soft warnings (quality thresholds) in the DJ readiness check, so DJs can export a playlist with minor quality warnings instead of being fully blocked.

## Scope

### In scope

- Change `_bpm_continuity_check` to return `needs_review` instead of `blocked` when the max adjacent BPM jump is just above the threshold.
- Keep hard blockers for: empty playlist, missing required metadata, Serato round-trip failure.
- Update the readiness summary to surface the distinction.
- Add a `blocker_count` and `review_count` to the report (already present) and make sure the UI uses the right gating.
- Update `can_export()` so `needs_review` allows export with a visible warning.
- Add tests proving hard vs soft behavior.

### Out of scope

- Changing the actual threshold values (3% BPM, 0.65 average score).
- Adding new readiness checks.
- Persisting a "force export" preference.

## Motivation

QA showed that a 25-track playlist with max BPM jump 3.41% and three low tag scores was fully blocked from export, even though the playlist is musically usable. DJs need to be able to export with a visible warning, and only be blocked on real data integrity issues (missing metadata, broken Serato files).

## Success criteria

1. A playlist with max BPM jump 3.41% and low tag scores is exportable (status `needs_review`).
2. A playlist with < 2 tracks or missing metadata is still blocked.
3. A Serato round-trip failure is still blocked.
4. All verification commands pass.
5. No audio files are mutated.

## Rollback plan

- Revert `_bpm_continuity_check` to return `blocked`.

## Review budget

Estimated changed lines: ~30 production + ~30 test lines, within the 400-line budget.
