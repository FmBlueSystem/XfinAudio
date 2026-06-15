# Design: Granular DJ Readiness Blocking

## Decision question

How do we let DJs export with quality warnings while still blocking on real data integrity issues?

## Alternatives considered (Arbor-style)

| Route | Pros | Cons | Verdict |
|---|---|---|---|
| A. Demote BPM/score/warnings to `needs_review`; keep size/metadata/Serato as `blocked` | Simple; matches user intent; minimal code. | Behavior change for existing users who relied on strict blocking. | **Selected.** |
| B. Add a "force export" user setting | Maximum flexibility. | More UI; complicates the semaphore. | Rejected. |
| C. Make every check return `needs_review` | Maximum permissiveness. | Loses the safety net for real data issues. | Rejected. |
| D. Add a per-check override list | Granular. | Too much UI for a small win. | Rejected. |

## Architecture impact

- `_bpm_continuity_check` in `dj_readiness.py` returns `needs_review` instead of `blocked`.
- `_average_score_check` already returns `needs_review` — no change.
- `_transition_warning_check` already returns `needs_review` — no change.
- `ReviewViewModel.can_export` already allows `needs_review` — no change.
- Update `build_dj_readiness_report` summary text to reflect the new policy.

## Affected files

- `src/xfinaudio/quality/dj_readiness.py`
- `tests/test_dj_readiness.py`
- `tests/test_review_view_model.py`

## Safety

- No audio mutation.
- No DSP scope expansion.
- No live Serato Database V2 writes.
- Real data integrity issues (missing metadata, broken Serato files) still block.
