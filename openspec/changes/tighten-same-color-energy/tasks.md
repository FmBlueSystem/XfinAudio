# Tasks: Tighten Same Color & Energy

Strict TDD is active. Every behavioral task is RED -> GREEN -> REFACTOR. Test
runner: `uv run pytest -q`. No production code before a failing test. Task 1
(characterization) MUST be green against today's code before any behavior change.

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Delivery strategy | ask-on-risk |
| Review budget | 400 changed lines |

| File | Est. changed lines |
|------|-------------------:|
| `src/xfinaudio/recommendation/strategies.py` | ~6 |
| `src/xfinaudio/recommendation/playlist_service.py` | ~150 |
| `src/xfinaudio/application/recommendation_candidates.py` | ~40 |
| `src/xfinaudio/recommendation/candidate_pool.py` | ~25 |
| `src/xfinaudio/desktop/recommendation_service.py` | ~20 |
| `src/xfinaudio/desktop/window_service_wiring.py` | ~2 |
| `src/xfinaudio/desktop/main_window.py` | ~15 |
| `src/xfinaudio/application/playlist_workflow.py` | ~10 |
| `tests/test_playlist_strategies.py` | ~40 |
| `tests/test_playlist_service.py` | ~180 |
| `tests/test_application_recommendation_candidates.py` | ~40 |
| `tests/test_recommendation_service_state.py` | ~30 |
| **Total** | **~558** |

- Total exceeds 400-line budget: **Yes** (~558, driven by strict-TDD test volume).
- Chained PRs recommended: **Yes**
- 400-line budget risk: **High**
- Decision needed before apply: **Yes** — under `ask-on-risk` the orchestrator MUST ask the maintainer to pick a chain strategy (or accept `size:exception`) before apply. This forecast does NOT decide the split.

### Proposed slice boundary (if maintainer chooses to chain)

Each slice is independently reviewable, independently green, independently revertible.

| Slice | Scope | Independently green | Revert boundary |
|-------|-------|---------------------|-----------------|
| PR 1 | Task 1 — characterization safety net only (no behavior change) | Yes — pins current behavior | Delete the added characterization tests |
| PR 2 | Tasks 2-8 — core strict eligibility in `playlist_service.py` + `strategies.py` (energy, MIXED gate, RGB label-only, atomic pre-cap, anchor identity, fail-closed, warnings, description) | Yes | Revert predicate/constants/warnings/description + their tests; restores +/-1 contract |
| PR 3 | Tasks 9-13 — anchor protection in `candidate_pool.py`, internal context seam in `recommendation_candidates.py`, transport through `playlist_workflow.py`, desktop wiring + dispatch guard, wiring regression | Yes | Revert seam/callback/wiring; public list API and ordinary path unchanged throughout |

Camelot independence (spec Requirement 1) is verified within PR 2 as a guard, not a separate slice.

## Phase 1: Characterization Safety Net (MUST be green before any behavior change)

- [ ] 1.1 RED->GREEN characterize `_apply_energy_tolerance()` (`playlist_service.py:766-787`): add tests in `tests/test_playlist_service.py` pinning the current `anchor +/- 1` band — anchor E8 keeps E7/E8/E9, drops E6/E10; `preserve_paths` bypass the band; `tolerance is None` returns input unchanged; exact removal-count warning text `Filtered {n} track(s) outside {strategy.name} energy tolerance`. Target: `uv run pytest -q tests/test_playlist_service.py`.
- [ ] 1.2 RED->GREEN characterize shared `_apply_color_filter()` (`playlist_service.py:689-704`) for `same_color`: pin the unfiltered-pool fallback (returns the original `tracks` list when no non-preserve candidate matches) and the exact two warning strings — `same_color filter applied: {color}` and `same_color: no candidates match anchor color '{color}'; falling back to unfiltered scoring`. This is the byte-compatibility lock for `same_color`. Target: `tests/test_playlist_service.py`.
- [ ] 1.3 RED->GREEN characterize current `same_color` and `same_energy` strategy descriptions and membership in `tests/test_playlist_strategies.py`: assert `same_energy.description` and `same_color.description` verbatim as they stand today, and that `same_color` / `same_energy` remain registered with current weights. Target: `tests/test_playlist_strategies.py`.
- [ ] 1.4 VERIFY Phase 1: `uv run pytest -q` green. These tests now guard the untouched strategies for the remainder of the change.

## Phase 2: Strict Combined Eligibility (`playlist_service.py`, `strategies.py`)

- [ ] 2.1 RED exact-energy membership: test that under `same_color_energy` every generated (non-control) candidate `energy_level` equals the resolved anchor `energy_level` (anchor equality, not a band). `tests/test_playlist_service.py`.
- [ ] 2.2 RED MIXED bounded gate — define named constants `MIXED_RGB_L1_MAX` (`0.08`), `MIXED_CENTROID_REL_MAX` (`0.15`), `MIXED_ROLLOFF_REL_MAX` (`0.15`) in `playlist_service.py`; tests assert a MIXED candidate passes at the inclusive boundary and fails just-over on each of RGB L1 / centroid rel-delta / rolloff rel-delta independently. `tests/test_playlist_service.py`.
- [ ] 2.3 RED MIXED fail-closed profiles: invalid/zero-denominator MIXED profiles (non-finite ratios, non-positive RGB sum, zero/negative/non-finite centroid or rolloff) make the candidate ineligible. Relative delta = `abs(candidate-anchor)/anchor`; zero/invalid denominator fails closed. `tests/test_playlist_service.py`.
- [ ] 2.4 RED RGB label-only: RED/GREEN/BLUE anchors admit candidates on dominant-label equality + exact energy only, with NO continuous gate; a candidate with zero centroid/rolloff but matching label+energy remains eligible. `tests/test_playlist_service.py`.
- [ ] 2.5 GREEN add private `_same_color_energy_eligible(anchor, candidate)` and the three constants in `playlist_service.py` implementing 2.1-2.4: `energy == anchor.energy AND dominant_color == anchor.dominant_color AND (color != MIXED OR mixed_profile_close(...))`. Keep private to `playlist_service.py` per design.
- [ ] 2.6 RED atomic-before-cap: test that combined color+energy eligibility is applied BEFORE pool capping (a candidate that would survive the cap but fails eligibility is excluded pre-cap). `tests/test_playlist_service.py`.
- [ ] 2.7 GREEN wire the atomic strict filter into the `same_color_energy` path so it runs before capping, without routing through `_apply_energy_tolerance()` or altering the `same_color` branch of `_apply_color_filter()`.
- [ ] 2.8 RED->GREEN Camelot independence (spec Req 1): a candidate meeting strict eligibility whose key is compatible-but-different from the anchor stays eligible; no exact-key requirement is introduced. `tests/test_playlist_service.py`.
- [ ] 2.9 REFACTOR Phase 2: dedupe helpers, keep naming consistent, all tests green.

## Phase 3: Anchor Identity, Fail-Closed & Warnings (`playlist_service.py`)

- [ ] 3.1 RED anchor identity resolution: anchor path resolves in order start-path -> first manual-prefix record carrying the majority manual color -> first profiled record; bound ONCE after completeness + `_apply_strategy_filters()` + `_apply_requested_genre()`. Include a requested-genre fixture proving binding happens after genre filtering. `tests/test_playlist_service.py`.
- [ ] 3.2 RED locked-control exclusion: a locked control conflicting with manual-prefix majority (no start-path) does NOT select the anchor; anchor is the first manual-prefix record carrying the majority color. `tests/test_playlist_service.py`.
- [ ] 3.3 RED missing/invalid supplied anchor path fails closed and is never replaced (no re-resolution silently substituting a different track). `tests/test_playlist_service.py`.
- [ ] 3.4 GREEN implement bound resolver + immutable anchor transport into final defensive strict recheck in `recommend_playlist()` for 3.1-3.3.
- [ ] 3.5 RED empty strict pool fail-closed: when strict eligibility excludes every non-control candidate, `same_color_energy` returns only preserved controls (or none) and emits an explicit strict-constraint warning — never widens to unfiltered scoring. `tests/test_playlist_service.py`.
- [ ] 3.6 RED shortage warning: fewer eligible generated candidates than requested generated slots returns only the eligible ones and emits a shortage warning; `requested_generated = max(0, requested_total - present_controls)`. `tests/test_playlist_service.py`.
- [ ] 3.7 RED warning ownership: shortage/prerequisite/empty warnings are emitted by `recommend_playlist()`; prefilter/context planning stays warningless (assert no warnings from the prefilter path). `tests/test_playlist_service.py` (+ `tests/test_application_recommendation_candidates.py` for the warningless prefilter).
- [ ] 3.8 RED controls preserved (spec): locked/start/end/manual controls pass through combined filtering without exclusion or re-scoring and remain in their positions even if they fail strict eligibility. `tests/test_playlist_service.py`.
- [ ] 3.9 GREEN implement fail-closed + request-aware warnings + control preservation for 3.5-3.8, leaving the shared `_apply_color_filter()` `same_color` branch byte-identical (Phase 1 tests must stay green).
- [ ] 3.10 REFACTOR Phase 3; full `uv run pytest -q` green including all Phase 1 characterization tests.

## Phase 4: Strategy Description (`strategies.py`)

- [ ] 4.1 RED update `tests/test_playlist_strategies.py` to assert the `same_color_energy` description states hard anchor-color filtering AND exact anchor energy (no `+/-1` band), while `same_color` / `same_energy` descriptions from Phase 1 remain byte-unchanged.
- [ ] 4.2 GREEN edit `same_color_energy` description in `strategies.py` (`strategies.py:116`) to the exact-energy guarantee wording. Do not touch `same_color` (`:102`) or `same_energy` (`:86`).

## Phase 5: Public API Compatibility & Anchor Protection Through Dedupe/Cap

- [x] 5.1 RED public list API: `plan_recommendation_candidates(...)` still returns a `list[TrackRecord]` for the `same_color_energy` strategy AND for an ordinary strategy. `tests/test_application_recommendation_candidates.py`.
- [x] 5.2 RED anchor stability: a no-control first-profile anchor with a duplicate sibling that `dedupe_recommendation_duplicates` would otherwise replace — assert the bound anchor path survives dedupe and cap and reaches final enforcement; anchor is never re-resolved after dedupe/cap and never converted to `start_path`. `tests/test_application_recommendation_candidates.py` (+ `tests/test_playlist_service.py` for final-enforcement stability).
- [x] 5.3 GREEN add frozen internal `RecommendationCandidateContext(records, same_color_energy_anchor_path)` and `_plan_same_color_energy_candidate_context(...)` in `recommendation_candidates.py`; keep exported `plan_recommendation_candidates(...) -> list[TrackRecord]` unchanged (its combined branch may delegate internally and return `.records`).
- [x] 5.4 GREEN protect the bound anchor in `candidate_pool.py` dedupe/cap (accept it as protected without converting to `start_path` or changing playlist-order semantics).
- [x] 5.5 GREEN transport the bound path through `PlaylistWorkflowService.recommend()` (`playlist_workflow.py:124`) to `recommend_playlist(..., same_color_energy_anchor_path=None)`.
- [x] 5.6 REFACTOR Phase 5; `uv run pytest -q` green.

## Phase 6: Desktop Wiring & Dispatch (`recommendation_service.py`, `window_service_wiring.py`, `main_window.py`)

- [x] 6.1 RED wiring/dispatch regression in `tests/test_recommendation_service_state.py`: prove `RecommendationService.recommend()` invokes the new `_desktop_same_color_energy_candidate_context` callback ONLY when `strategy_name == "same_color_energy"`, and routes every other strategy through `_desktop_recommendation_records()` (combined-only dispatch AND ordinary-path compatibility). `tests/test_recommendation_service_state.py`.
- [x] 6.2 GREEN add `self._desktop_same_color_energy_candidate_context: Callable[..., RecommendationCandidateContext] = _unwired` in `RecommendationService.__init__` (`recommendation_service.py:46-67`) and the keyword-only param on `set_actions()` (`recommendation_service.py:102-125`), assigned alongside the existing ten callbacks.
- [x] 6.3 GREEN add the `strategy_name == "same_color_energy"` dispatch guard in `recommend()` (`recommendation_service.py:148-167`), forwarding `context.records` + the bound path; all other strategies keep calling `self._desktop_recommendation_records(controls, strategy_name)`.
- [x] 6.4 GREEN inject `desktop_same_color_energy_candidate_context=self._desktop_same_color_energy_candidate_context` in `wire_main_recommendation_service()` (`window_service_wiring.py:91-102`) and add `_desktop_same_color_energy_candidate_context()` on `MainWindow` next to `_desktop_recommendation_records()` (`main_window.py:473-484`), delegating to the internal context planner.
- [x] 6.5 REFACTOR Phase 6; `uv run pytest -q` green.

## Phase 7: Verification (exact order — no skipping, no reordering)

- [x] 7.1 `uv run pytest -q`
- [x] 7.2 `uv run pyright src tests`
- [x] 7.3 `uv run pytest --cov --cov-fail-under=70 -q`
- [x] 7.4 `uv run ruff check .`
- [x] 7.5 `uv run ruff format --check .`
- [x] 7.6 `uv run python scripts/release_gate_check.py --run`

## Post-Implementation Acceptance Gate (not a code task)

- [ ] A.1 Offscreen calibration against a scratch copy of `~/.xfinaudio/xfinaudio.sqlite3` (never the live DB): run multiple MIXED and RGB anchors, inspect pool sizes/warnings/boundary examples, then listen around the MIXED thresholds. A post-calibration change touches ONLY `MIXED_RGB_L1_MAX` / `MIXED_CENTROID_REL_MAX` / `MIXED_ROLLOFF_REL_MAX` definitions and their coherent reflection in proposal/spec/design/tests. This is an acceptance gate, not a design blocker.
