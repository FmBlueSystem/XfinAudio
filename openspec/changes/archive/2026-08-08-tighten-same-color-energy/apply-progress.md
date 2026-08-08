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

## Slice PR 3 (FINAL) — Phases 5, 6: Public API compatibility, anchor protection, desktop wiring

Scope: transport a bound `same_color_energy` anchor path through dedupe/cap
(Phase 5) and wire the combined-strategy context seam into the desktop dispatch
(Phase 6), plus Phase 7 verification. Base branch:
`fix/same-color-energy-strict-eligibility` (feature-branch-chain, immediate
previous PR branch — PR #333).

### Completed Tasks

- [x] 5.1 Public list API stays `list[TrackRecord]` for combined AND ordinary strategies
- [x] 5.2 Anchor stability: bound path survives dedupe (protected against sibling
      replacement) + cap, reaches final enforcement; never re-resolved, never
      converted to `start_path`
- [x] 5.3 Frozen `RecommendationCandidateContext(records, same_color_energy_anchor_path)`
      + `_plan_same_color_energy_candidate_context(...)`; exported
      `plan_recommendation_candidates(...) -> list[TrackRecord]` unchanged (its
      combined branch delegates internally and returns `.records`)
- [x] 5.4 `candidate_pool.py` dedupe/cap protect the bound anchor via
      `protected_path` (no `start_path` conversion, no playlist-order change)
- [x] 5.5 `PlaylistWorkflowService.recommend()` forwards
      `same_color_energy_anchor_path` to `recommend_playlist(...)`
- [x] 5.6 REFACTOR Phase 5
- [x] 6.1 Wiring/dispatch regression (combined-only invocation AND ordinary-path
      compatibility) in `tests/test_recommendation_service_state.py`
- [x] 6.2 `_unwired`-initialized `_desktop_same_color_energy_candidate_context`
      callback + keyword param on `set_actions()`
- [x] 6.3 `strategy_name == "same_color_energy"` dispatch guard in `recommend()`;
      forwards `context.records` + bound path; all other strategies keep the
      byte-identical `_desktop_recommendation_records()` route
- [x] 6.4 Injected from `wire_main_recommendation_service()`;
      `MainWindow._desktop_same_color_energy_candidate_context()` delegates to the
      internal context planner
- [x] 6.5 REFACTOR Phase 6
- [x] 7.1-7.6 Verification sequence (see table below)

### Files Changed

| File | Action | What was done |
|------|--------|---------------|
| `src/xfinaudio/recommendation/candidate_pool.py` | Modified | `dedupe_recommendation_duplicates(..., protected_path=None)` adds the bound anchor to `preserve`; `build_recommendation_pool(..., protected_path=None)` retains the anchor after the cap by displacing the last trimmable slot (extracted `_build_recommendation_pool` for the unchanged core). No `start_path` conversion, no order change. |
| `src/xfinaudio/recommendation/playlist_service.py` | Modified | `recommend_playlist(..., same_color_energy_anchor_path=None)`; `_bind_supplied_anchor()`; `_apply_same_color_energy_filter(..., resolve_when_unbound=True)` so a supplied-but-invalid path fails closed (never re-resolves); public `resolve_same_color_energy_anchor_path()` runs the same pre-anchor stages and returns the bound path. |
| `src/xfinaudio/application/recommendation_candidates.py` | Modified | Frozen `RecommendationCandidateContext`; internal `_plan_same_color_energy_candidate_context(...)`; exported `plan_recommendation_candidates(...)` combined branch delegates and returns `.records`. |
| `src/xfinaudio/application/playlist_workflow.py` | Modified | `recommend(..., same_color_energy_anchor_path=None)` forwards the bound path to `recommend_playlist(...)`. |
| `src/xfinaudio/desktop/recommendation_service.py` | Modified | `_unwired`-init callback; `set_actions()` keyword param; `recommend()` dispatch guard; `same_color_energy_anchor_path` threaded through `start_recommendation` -> `_start_recommendation_worker` -> `workflow_service.recommend()`. |
| `src/xfinaudio/desktop/window_service_wiring.py` | Modified | Inject `desktop_same_color_energy_candidate_context` in `wire_main_recommendation_service()`. |
| `src/xfinaudio/desktop/main_window.py` | Modified | `_desktop_same_color_energy_candidate_context()` next to `_desktop_recommendation_records()`, delegating to the internal context planner. |
| `tests/test_application_recommendation_candidates.py` | Modified | 6 new tests (list API for combined + ordinary, frozen context, anchor survives dedupe/cap, bound-path final enforcement, supplied-missing fails closed); made the boundary-import test format-agnostic (ruff/isort groups same-module symbols). |
| `tests/test_recommendation_service_state.py` | Modified | 2 new dispatch regressions (combined-only vs ordinary-path); wired the new callback into `_wire_service`; adapted `test_recommend_reads_strategy_via_current_data` to the context route (combined strategy now dispatches through the seam). |

### Byte-untouchability of slice-1 / slice-2 tests — status

- Slice 3 did NOT touch `tests/test_playlist_service.py` or
  `tests/test_playlist_strategies.py` at all (`git diff --name-only ea79cae`
  confirms). The eight slice-1 characterization tests (`same_color` /
  `same_energy` `+/-1` band, shared unfiltered fallback + two warnings, verbatim
  descriptions) and every slice-2 strict-eligibility test are byte-untouched and
  pass (`1406 passed`).
- Ordinary desktop path proven unchanged: `recommend()`'s dispatch guard `return`s
  for `same_color_energy` only; every other strategy falls through to the exact
  original `records = self._desktop_recommendation_records(...)` -> `start_recommendation(records, strategy_name, controls, spectral_cohesion)`
  path, and `_start_recommendation_worker` passes `same_color_energy_anchor_path=None`
  (default), which `recommend_playlist` ignores for non-combined strategies.
  Regression test `test_recommend_uses_records_route_for_ordinary_strategy`
  asserts the context callback does NOT fire and no anchor path is forwarded.

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.1 | `tests/test_application_recommendation_candidates.py` | Unit | ✅ 148/148 | ✅ Written | ✅ Passed | ✅ combined + ordinary | ➖ clean |
| 5.2-5.5 | `tests/test_application_recommendation_candidates.py` | Unit | ✅ 148/148 | ✅ Written (4 failing: context planner + anchor param) | ✅ Passed | ✅ dedupe survival, final enforcement, fail-closed | ✅ extracted `_build_recommendation_pool`, `_bind_supplied_anchor` |
| 6.1-6.4 | `tests/test_recommendation_service_state.py` | Unit | ✅ 8/8 (pre-existing) | ✅ Written (7 failing: `set_actions` param + dispatch) | ✅ Passed | ✅ combined-only + ordinary-path | ➖ clean |

### Test Summary

- Total new tests written: 8 (6 candidates + 2 dispatch regressions)
- Total passing: full suite `1406 passed`
- Layers used: Unit (8)
- Approval tests: None — no refactoring-of-existing-behavior tasks (the seam is additive)
- Pure functions created: `_bind_supplied_anchor`, `resolve_same_color_energy_anchor_path`

### Work Unit Evidence

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest -q tests/test_application_recommendation_candidates.py tests/test_recommendation_service_state.py tests/test_candidate_pool.py tests/test_playlist_service.py tests/test_playlist_strategies.py` -> all pass |
| Runtime harness | N/A — additive application/desktop seam covered by unit-level dispatch and transport tests; no new runtime/DB boundary is crossed. Offscreen MIXED/RGB listening calibration remains post-implementation acceptance gate A.1, not a slice-3 code task. |
| Rollback boundary | Revert the `protected_path` params in `candidate_pool.py`, the `same_color_energy_anchor_path` param + `_bind_supplied_anchor` + `resolve_when_unbound` + public resolver in `playlist_service.py`, the context dataclass/planner in `recommendation_candidates.py`, the workflow forward, and the desktop callback/dispatch/wiring + slice-3 tests. Slice-1/slice-2 behavior, `same_color` / `same_energy`, and the ordinary desktop path are untouched, so revert removes no unrelated work. |

### Full Verification (exact order)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | PASS — `1406 passed` |
| 2 | `uv run pyright src tests` | PASS — `0 errors, 0 warnings, 0 informations` |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | PASS — `Total coverage: 91.12%`, `1406 passed` |
| 4 | `uv run ruff check .` | PASS — `All checks passed!` |
| 5 | `uv run ruff format --check .` | PASS — `277 files already formatted` |
| 6 | `uv run python scripts/release_gate_check.py --run` | PASS — exit 0 |

### Review budget

- Changed lines (src + tests, additions + deletions vs slice-2 HEAD `ea79cae`):
  **436** (production 205, tests 231) against the 400-line budget.
- **Over budget by 36 lines**, and above the tasks.md forecast (~182 for Phases
  5+6). The forecast counted production-leaning estimates; the actual overage is
  strict-TDD test volume (231 test lines vs 205 production — production is within
  budget). Same pattern the maintainer accepted for slices 2. Reported prominently
  in the PR body and this report; no check was weakened to fit the budget.
- Splitting Phase 5 (transport) from Phase 6 (wiring) into two PRs was rejected:
  Phase 6's dispatch/wiring tests reference the Phase 5 context seam, so a
  Phase-6-only PR would test code not present in its base, and a Phase-5-only PR
  would ship an unused seam — worse review, not better. This is the same
  strict-TDD splitting criterion applied on slice 2.

## Verify Correction (2026-08-05) — close F1 and F2 (on PR #334 branch, no new PR)

Scope: a small, tightly bounded correction closing the two verify-report WARNINGs
on `feat/same-color-energy-anchor-transport` (PR #334). No new slice, no new
branch. This entry MERGES with the slice 1/2/3 history above; none of it is
overwritten.

### F1 — shortage-warning scenario now has an asserting test (NO production change)

Spec R5 scenario "Strict pool is shorter than requested" was implemented
(`playlist_service.py:1057-1063`, task 3.6) but had no runtime-asserting test.
Added one; production code was NOT touched (the behavior already exists — only
the proof was missing).

- **Test**: `tests/test_playlist_service.py::test_same_color_energy_shortage_returns_only_eligible_and_warns`
- **Fixture**: MIXED anchor + 2 proximate MIXED candidates (`/near_one`, `/near_two`)
  + 1 far MIXED candidate (`/far`), driven with `start_path="/anchor.flac"` and
  `target_count=5`. One control + 5 requested => 4 requested generated slots, only
  2 strictly eligible => drives the shortage branch.
- **Asserts (eligibility never relaxed)**: returned generated set is exactly
  `{/near_one, /near_two}`; `/far` excluded despite unfilled slots; for every
  returned generated candidate, `_same_color_energy_eligible(anchor, candidate) is True`,
  `energy_level == anchor.energy_level`, and `dominant_color == "MIXED"` (exercises
  the MIXED proximity gate).
- **Exact warning asserted** (the real string the implementation emits):
  `same_color_energy: strict eligibility left 2 generated candidate(s) for 4 requested slot(s)`
- **RED evidence** (behavior pre-exists, so RED proves the test truly hits the
  shortage branch): temporarily re-pointed the warning assertion at the empty-pool
  string (`strict color-and-exact-energy eligibility excluded every generated candidate`)
  → test FAILED with `assert False` on the warning check, because the pool is NOT
  empty (2 eligible survive) — confirming the test exercises the shortage branch,
  not the empty/prerequisite branch. The eligibility assertions (which precede the
  warning assert) passed in that run. Restored the correct shortage assertion → GREEN.

### F2 — tasks.md checkbox reconciliation (planning-drift correction)

`tasks.md` under-claimed shipped work. Reconciled checkboxes to shipped reality:

- Phase 1 (1.1–1.4): `[ ]` → `[x]` — shipped in slice 1, PR #332.
- Phase 2 (2.1–2.9): `[ ]` → `[x]` — shipped in slice 2, PR #333.
- Phase 3 (3.1–3.10): `[ ]` → `[x]` — shipped in slice 2, PR #333; 3.6's asserting
  test is completed by this F1 correction (annotated inline in tasks.md).
- Phase 4 (4.1–4.2): `[ ]` → `[x]` — shipped in slice 2, PR #333.
- Phases 5, 6, 7: already `[x]` (slice 3, PR #334) — unchanged.
- A.1: left `[ ]` — genuinely NOT shipped; it is an open post-implementation
  listening-calibration acceptance gate, not a code task.

### TDD Cycle Evidence (F1)

| Task | RED (test written first) | GREEN | Notes |
|------|--------------------------|-------|-------|
| 3.6 shortage-warning proof | Warning assertion mis-pointed at empty-pool branch → FAILED for the right reason (pool not empty) | Correct shortage-string assertion → PASS | No production edit; proof-only |

### Work Unit Evidence (F1 + F2)

| Evidence | Value |
|----------|-------|
| Focused test command | `uv run pytest -q tests/test_playlist_service.py::test_same_color_energy_shortage_returns_only_eligible_and_warns` → `1 passed` |
| Runtime harness | N/A — unit-level test proving an already-implemented recommendation-policy branch; no runtime/DB/desktop boundary crossed. F2 is a docs-only checkbox reconciliation. |
| Rollback boundary | Delete the single appended test block in `tests/test_playlist_service.py`; revert the checkbox `[x]`→`[ ]` edits in `tasks.md`. No production code changed; nothing unrelated removed. |

### Slice-1 characterization safety net — status

The eight slice-1 `same_color` / `same_energy` characterization tests are
byte-untouched (this correction only appends one new test and edits none) and
pass in the full green suite. No characterization test was edited to accommodate
new code.

### Full Verification (exact order)

| # | Command | Result |
|---|---------|--------|
| 1 | `uv run pytest -q` | PASS — `1407 passed` (1406 prior + 1 new) |
| 2 | `uv run pyright src tests` | PASS — `0 errors, 0 warnings, 0 informations` |
| 3 | `uv run pytest --cov --cov-fail-under=70 -q` | PASS — `Total coverage: 91.15%`, `1407 passed` |
| 4 | `uv run ruff check .` | PASS — `All checks passed!` |
| 5 | `uv run ruff format --check .` | PASS — `277 files already formatted` |
| 6 | `uv run python scripts/release_gate_check.py --run` | PASS — exit 0 |

### Review budget

- Changed lines for this correction: 1 test block (~40 lines in
  `tests/test_playlist_service.py`) + `tasks.md` checkbox/annotation edits + these
  openspec artifact updates. Well inside the 120-line correction budget; zero
  production source lines changed.
