# Archive Report: Spectral Cohesion Control

**Change**: `spectral-cohesion-control`
**Archived to**: `openspec/changes/archive/2026-06-14-spectral-cohesion-control/`
**Archived date**: 2026-08-08
**Artifact store mode**: openspec

## Why This Was Archived Late

`state.yaml` recorded `status: completed`, `state: completed`,
`review_status: completed` and every phase `complete` — but carried
`next_recommended: verify` and `step: verify`, a stale pointer back at a phase
its own `phases:` map already marked done. That contradiction is likely why the
archive step never ran. Both fields are corrected in this pass (see State
Correction). One of nineteen stale directories found by the 2026-08-08 audit.

## What Shipped

Shipped in commit `7a52cdc`, "Release v1.0.2: spectral color analysis, cohesion
control, lazy completion" (2026-06-14).

A user-facing cohesion control that lets the operator bias transition scoring
toward spectral colour consistency. Verified on `main` at archive time:

| Layer | Symbol | Location |
|---|---|---|
| Config field | `spectral_cohesion` on `TransitionScoringConfig` | `src/xfinaudio/recommendation/scoring.py:91` |
| Weight adjustment | `_effective_weights` | `src/xfinaudio/recommendation/scoring.py:331` |
| Colour penalty | `_spectral_color_penalty` | `src/xfinaudio/recommendation/scoring.py:337` |
| Penalty call site | applied in `score_transition` | `src/xfinaudio/recommendation/scoring.py:200` |
| Default (backward compatible) | `DEFAULT_SCORING_CONFIG(..., spectral_cohesion=0.0)` | `src/xfinaudio/recommendation/scoring.py:102` |
| UI control | `spectral_cohesion_slider` | `src/xfinaudio/desktop/screens/build_screen.py:114-124` |
| Persistence | `spectral_cohesion` on `ScoringSettings` | `src/xfinaudio/config/settings.py:37` |

The slider is a real user-facing control, not internal plumbing: it carries an
accessible name (`build_screen.py:120`, re-applied at `:253`) and sits in the
tab order after the recommend button (`build_screen.py:269`).

## State Correction

| Field | Before | After | Reason |
|---|---|---|---|
| `step` | `verify` | `archive` | `phases.verify` was already `complete` |
| `next_recommended` | `verify` | `archive` | Stale self-referential pointer; no SDD work remained |

`status`, `state`, `review_status`, `created`, `updated`, `phases` and the two
original note lines are untouched.

## Verification Verdict

**PASS** — recorded in `verify-report.md`.

- `uv run pytest -q` — 778 tests passed
- `uv run pyright src tests` — 0 errors, 0 warnings, 0 informations
- `uv run pytest --cov --cov-fail-under=70 -q` — 88.15% coverage
- `uv run ruff check .` — PASS
- `uv run ruff format --check .` — PASS
- `uv run python scripts/release_gate_check.py --run` — PASS

Nine requirements (R1.1–R5) trace to named tests, chiefly
`tests/test_transition_scoring.py` and `tests/test_playlist_strategies.py`.

**One honest caveat carried forward from the original report**: requirement
R4.2 ("Slider persists value") is evidenced as "Manual + `main_window.py`
wiring" — a manual check plus code inspection, not an asserting automated test.
That is recorded here rather than upgraded, because this archive pass changes no
source and adds no tests.

## Specs Synced

**No.** This change carries `spec.md` but has no `specs/` delta directory and no
durable capability spec is created or updated by this archive pass. Archiving
here is a lifecycle-record correction only.

Note for readers tracing the colour lineage: the `Same Color` strategy this
change registered (task 7) is now described by the durable capability specs
`openspec/specs/same-color-strategy/` and
`openspec/specs/same-color-energy-strategy/`, both of which were shaped by later
colour-strategy changes archived on 2026-07-20 and 2026-08-08. Those successors
own the current strategy semantics; this change owns the cohesion scoring knob.

## Archive Contents

- [x] `proposal.md` — intent, scope, risks, success criteria
- [x] `spec.md` — GIVEN/WHEN/THEN scenarios for scoring, UI and wiring
- [x] `design.md` — slider-versus-strategy comparison and scoring formula
- [x] `tasks.md` — 12 tasks, all `[x]`
- [x] `apply-progress.md` — apply record
- [x] `verify-report.md` — full gate results, requirement table, safety check
- [x] `state.yaml` — corrected as described above

## Task Completion

All 12 tasks `[x]`, including the nested RED/GREEN/REFACTOR sub-items under
task 4. No unchecked items.

`state.yaml` note 1 records honestly that "Implementation applied retroactively
after initial coding; artifacts created to document the change." The TDD claim is
scoped accordingly by note 2 — RED→GREEN→REFACTOR was followed for the
behaviour-changing scoring and wiring tasks, not for the whole change. That
scoping is preserved, not tidied away.

## Follow-Up Items

**(a) Automate R4.2 slider persistence (OPEN, low priority).** The only
requirement in this change without an asserting test. Would close the last
manual-evidence gap.

## Archive Metadata

- **Created**: 2026-06-14
- **Updated**: 2026-06-14
- **Shipped**: 2026-06-14 (`7a52cdc`, v1.0.2)
- **Archived**: 2026-08-08

**SDD Cycle Status**: COMPLETE — proposed, specified, designed, planned,
implemented, verified and archived. Spec fold-in not applicable (see Specs
Synced).
