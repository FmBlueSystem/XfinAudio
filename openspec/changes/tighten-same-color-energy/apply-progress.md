# Apply Progress: Tighten Same Color & Energy

Strict TDD is active. This file tracks per-slice implementation progress.

## Slice PR 1 — Phase 1: Characterization Safety Net (NO behavior change)

Scope: pin the CURRENT behavior of untouched code so later slices prove they did
not break it. Zero production behavior changed in this slice.

### Completed Tasks

- [x] 1.1 Characterize `_apply_energy_tolerance()` (`playlist_service.py:766-787`)
- [x] 1.2 Characterize shared `_apply_color_filter()` `same_color` fallback (`playlist_service.py:689-704`)
- [x] 1.3 Characterize current `same_color` / `same_energy` / `same_color_energy` descriptions + registration
- [x] 1.4 VERIFY Phase 1 green (`uv run pytest -q`)

### Files Changed

| File | Action | What was done |
|------|--------|---------------|
| `tests/test_playlist_service.py` | Modified | Added 6 characterization tests for `_apply_energy_tolerance` (`+/-1` band, `preserve_paths` bypass, `tolerance is None` passthrough, no-removal warningless case) and shared `_apply_color_filter` `same_color` unfiltered fallback + exact warning strings. Imported the two private functions. |
| `tests/test_playlist_strategies.py` | Modified | Added 3 verbatim characterization tests pinning current `same_color`, `same_energy`, and `same_color_energy` descriptions + weights/tolerance/display names. |

No production source files were modified in this slice (spec boundary honored).

### TDD Cycle Evidence

Characterization suites pin CURRENT behavior, so the correct RED->GREEN evidence
is: the test must pass against today's code on first run. If it had failed, the
test (not production) would have been corrected to match reality.

| Task | RED (test written first) | GREEN (passes against today's code) | Notes |
|------|--------------------------|-------------------------------------|-------|
| 1.1 | Added `_apply_energy_tolerance` characterization tests | PASS on first run against unchanged production | No production edit |
| 1.2 | Added `_apply_color_filter` fallback characterization tests | PASS on first run against unchanged production | No production edit |
| 1.3 | Added verbatim description characterization tests | PASS on first run against unchanged production | No production edit |

All characterization assertions matched current behavior exactly on the first
run (9/9), confirming the pinned understanding of current behavior is correct.

### Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest -q tests/test_playlist_service.py tests/test_playlist_strategies.py` -> `126 passed` |
| Characterization subset | `-k "characteriz or verbatim or apply_energy_tolerance or apply_color_filter or currently_verbatim"` -> `9 passed, 117 deselected` |
| Runtime harness | N/A — this slice adds unit-level characterization tests only; no runtime/integration boundary is crossed. |
| Rollback boundary | Delete the two appended characterization test blocks (and the two added imports in `tests/test_playlist_service.py`). No production code to revert. |

### Full Verification (exact order)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | PASS — `1431 passed` |
| 2 | `uv run pyright src tests` | PASS — `0 errors, 0 warnings, 0 informations` |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | PASS — `Total coverage: 91.34%`, `1431 passed` |
| 4 | `uv run ruff check .` | PASS — `All checks passed!` |
| 5 | `uv run ruff format --check .` | PASS — `281 files already formatted` |
| 6 | `uv run python scripts/release_gate_check.py --run` | PASS — exit 0 |

### Discovery While Characterizing

- `_apply_color_filter()` and `_apply_energy_tolerance()` had NO covering tests
  before this slice despite two callers each; that gap is exactly why the
  characterization slice exists. They are now pinned.
- On first full-suite run, `tests/test_public_open_source_docs.py` failed with
  `FileNotFoundError: AGENTS.md`. Root cause: a stray UNCOMMITTED working-tree
  deletion of `AGENTS.md` that pre-existed this slice (not committed to the
  tracker branch, not caused by these tests). Restoring `AGENTS.md`
  (`git checkout -- AGENTS.md`) made the docs tests pass. That deletion is out of
  this slice's scope and was not carried into the commit.

### Remaining (later slices, OUT of this slice's scope)

- [ ] Phase 2-7: strict combined eligibility, anchor identity, fail-closed
      warnings, strategy description, public-API/anchor protection, desktop
      wiring, final verification.

## Slice PR 2 — Phases 2, 3, 4: Core strict combined eligibility

Scope: strict color-and-exact-energy eligibility in `playlist_service.py` and
`strategies.py`. Phases 5-6 (public-API/anchor protection, desktop wiring) stay
OUT of scope for slice 3. Base branch: `test/same-color-energy-characterization`
(feature-branch-chain, immediate previous PR branch — PR #332).

### Completed Tasks

- [x] 2.1 Exact-energy membership (generated candidates equal anchor energy, no band)
- [x] 2.2 MIXED bounded gate + named constants `MIXED_RGB_L1_MAX` (0.08),
      `MIXED_CENTROID_REL_MAX` (0.15), `MIXED_ROLLOFF_REL_MAX` (0.15); inclusive
      boundary passes, just-over fails independently on L1 / centroid / rolloff
- [x] 2.3 MIXED fail-closed (zero RGB sum, zero centroid/rolloff denominator,
      missing candidate profile all ineligible; `abs(cand-anchor)/anchor` fails
      closed on zero/invalid denominator)
- [x] 2.4 RGB label-only (no continuous gate; zero centroid/rolloff + matching
      label+energy stays eligible)
- [x] 2.5 GREEN `_same_color_energy_eligible(anchor, candidate)` + 3 constants,
      private to `playlist_service.py`
- [x] 2.6 Atomic-before-cap (ineligible candidate excluded pre-cap)
- [x] 2.7 GREEN atomic strict filter wired into `same_color_energy` path without
      routing through `_apply_energy_tolerance()` or altering the `same_color`
      branch of `_apply_color_filter()`
- [x] 2.8 Camelot independence (compatible-but-different key stays eligible)
- [x] 2.9 REFACTOR Phase 2
- [x] 3.1 Anchor identity resolution (`_resolve_same_color_energy_anchor`:
      start-path -> first manual-prefix record carrying majority color -> first
      profiled record)
- [x] 3.2 Locked-control exclusion (locked controls never select the anchor)
- [x] 3.5 Empty strict pool fail-closed (only preserved controls; strict-constraint
      warning; never widens)
- [x] 3.6 Shortage warning (`requested_generated = max(0, requested_total - present_controls)`)
- [x] 3.7 Warning ownership (`recommend_playlist()` owns warnings; prefilter warningless)
- [x] 3.8 Controls preserved through strict filtering even when strict-ineligible
- [x] 3.9 GREEN fail-closed + request-aware warnings + control preservation;
      shared `_apply_color_filter()` `same_color` branch left byte-identical
- [x] 3.10 REFACTOR Phase 3; full suite green including all Phase 1 tests
- [x] 4.1/4.2 `same_color_energy` description states hard anchor-color filtering AND
      exact anchor energy; `same_color` / `same_energy` descriptions byte-unchanged
- [x] 7.1-7.6 Verification sequence (see table below)

Partial within scope: Phase 3 anchor-transport tasks that depend on the
`same_color_energy_anchor_path` parameter and dedupe/cap protection (3.3, 3.4 as
transport, dedupe survival) are structurally slice-3 (`candidate_pool.py`,
`recommendation_candidates.py`, `playlist_workflow.py`, desktop). In slice 2 the
anchor is resolved internally in `recommend_playlist()`/`prefilter_strategy_candidates()`
from the same pre-anchor pool; the injected-path transport arrives in slice 3.
The strict eligibility behavior (identity precedence, fail-closed, warnings) is
fully implemented and tested here.

### Files Changed

| File | Action | What was done |
|------|--------|---------------|
| `src/xfinaudio/recommendation/strategies.py` | Modified | `same_color_energy` description -> exact-energy wording; removed `energy_tolerance=1` (strict path enforces exact energy, not the shared +/-1 band). `same_color` / `same_energy` untouched. |
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | Added `MIXED_RGB_L1_MAX` / `MIXED_CENTROID_REL_MAX` / `MIXED_ROLLOFF_REL_MAX`; `_same_color_energy_eligible`, `_mixed_profile_close`, `_relative_delta`, `_is_finite(_positive)`, `_resolve_same_color_energy_anchor`, `_apply_same_color_energy_filter`, `_same_color_energy_warnings`. Removed `same_color_energy` from `_COLOR_FILTER_STRATEGIES`; wired the strict atomic filter (pre-cap) into `recommend_playlist()` and `prefilter_strategy_candidates()`. Shared `_apply_color_filter()` `same_color` branch untouched. |
| `tests/test_playlist_service.py` | Modified | Updated 4 `same_color_energy`-scoped tests from +/-1 band / unfiltered fallback to exact energy / fail-closed; added ~20 new strict-eligibility tests (RGB exact energy + label-only, MIXED boundary/just-over/fail-closed, atomic-before-cap, Camelot independence, control preservation, prerequisite fail-closed, MIXED proximity end-to-end). |
| `tests/test_playlist_strategies.py` | Modified | Updated 3 `same_color_energy`-scoped assertions (description verbatim, `energy_tolerance is None`, guarantees wording) to the new behavior. `same_color` / `same_energy` characterizations untouched. |

### Slice-1 characterization safety net — status

All nine slice-1 characterization tests still pass. The only assertions changed
are `same_color_energy`-scoped (its OWN old +/-1 band / old description), which
this change exists to replace:

- `test_same_color_energy_description_is_currently_verbatim` — repurposed to pin
  the NEW `same_color_energy` description (old +/-1 wording was the target of the
  change). The `same_color` and `same_energy` verbatim-description
  characterizations are byte-unchanged and still green.
- The six `_apply_energy_tolerance` and shared `_apply_color_filter` (`same_color`)
  characterization tests are untouched and green — proving `same_energy` and
  `same_color` were not regressed.

### TDD Cycle Evidence

| Task group | RED | GREEN | REFACTOR |
|------------|-----|-------|----------|
| 2.1-2.4 RGB + MIXED eligibility | `_same_color_energy_eligible` import + constant imports failed (ImportError) | Added constants + `_same_color_energy_eligible` / `_mixed_profile_close` / `_relative_delta` | Extracted `_is_finite`; inlined final gate return |
| 2.6-2.7 atomic-before-cap | `test_..._applies_strict_filter_before_capping` failed | Wired `_apply_same_color_energy_filter` pre-`apply_controls` | — |
| 2.8 Camelot independence | `test_..._compatible_different_key_stays_eligible` failed | No key gate added (eligibility ignores key) | — |
| 3.x fail-closed + warnings | prerequisite / empty-pool / shortage tests failed | Added `_same_color_energy_warnings` owned by `recommend_playlist()` | — |
| 4.x description | `test_strategy_descriptions_state_guarantees` (exact wording) failed | Edited `strategies.py` description | — |

### Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest -q tests/test_playlist_service.py tests/test_playlist_strategies.py tests/test_candidate_pool.py` -> `164 passed` |
| Runtime harness | N/A — unit-level recommendation-policy change; no runtime/desktop boundary crossed in this slice (that transport is slice 3). Offscreen MIXED/RGB listening calibration is the post-implementation acceptance gate A.1, not a slice-2 code task. |
| Rollback boundary | Revert the strict predicate + 3 constants + `_apply_same_color_energy_filter` + `_same_color_energy_warnings` + `_resolve_same_color_energy_anchor` in `playlist_service.py`, the `same_color_energy` description/`energy_tolerance` edit in `strategies.py`, and the slice-2 test edits. Restores the +/-1 contract. `same_color` / `same_energy` and the shared helper are untouched, so revert removes no unrelated work. |

### Full Verification (exact order)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | PASS — `1398 passed` |
| 2 | `uv run pyright src tests` | PASS — `0 errors, 0 warnings, 0 informations` |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | PASS — `Total coverage: 91.07%`, `1398 passed` |
| 4 | `uv run ruff check .` | PASS — `All checks passed!` |
| 5 | `uv run ruff format --check .` | PASS — `277 files already formatted` |
| 6 | `uv run python scripts/release_gate_check.py --run` | PASS — exit 0 |

### Review budget

- Changed lines (src + tests, additions + deletions vs slice-1 HEAD `3faa9e4`):
  **540** (production 226, tests 314) against the 400-line budget.
- **Over budget by 140 lines.** The entire overage is strict-TDD test volume
  (314 test lines); production is 226. This matches the slice-1 forecast note
  that the change's overage is test volume, not production sprawl. Reported to the
  maintainer per `ask-on-risk` before opening the PR rather than silently
  proceeding.
