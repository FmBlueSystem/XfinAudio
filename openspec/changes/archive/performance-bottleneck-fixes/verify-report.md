# Verify Report: performance-bottleneck-fixes

> Requirement-by-requirement verification evidence for the performance bottleneck fixes.

## Automated Gates

| Gate | Command | Result | Evidence |
|------|---------|--------|----------|
| Unit tests | `uv run pytest -q` | **PASS** | 740 passed |
| Transition scoring tests | `uv run pytest tests/test_transition_scoring.py -q` | **PASS** | all passed |
| Sequence optimizer tests | `uv run pytest tests/test_sequence_optimizer.py -q` | **PASS** | all passed |
| Playlist service tests | `uv run pytest tests/test_playlist_service.py -q` | **PASS** | all passed |
| MainWindow tests | `uv run pytest tests/test_main_window.py -q` | **PASS** | 90 passed |
| Lint | `uv run ruff check .` | **PASS** | All checks passed |
| Format | `uv run ruff format --check .` | **PASS** | 155 files already formatted |
| Release gate | `uv run python scripts/release_gate_check.py --run` | **PASS** | all automated gates pass |

## Capability: dj-recommendation-safety

### Requirement: Transition score cache eliminates redundant scoring CPU

**GIVEN** identical track pairs, weights, config and boost rules  
**WHEN** `score_transition()` is called twice within the same session cache  
**THEN** the second call returns the cached object without recomputation.

**Evidence:**
- Test: `tests/test_transition_scoring.py::test_score_transition_returns_cached_result_on_second_call` — PASS.
- Test: `tests/test_transition_scoring.py::test_score_cache_is_isolated_per_session` — PASS.
- Implementation: `scoring.py` builds key from `(left.path, right.path, id(weights), id(config), id(boost_rules))` and stores `TransitionScore` in caller-owned cache.

### Requirement: BPM-jump filter runs before the TSP optimizer

**GIVEN** a heuristic recommendation path  
**WHEN** candidates are prepared for `recommend_sequence()`  
**THEN** tracks that would violate the adjacent BPM jump guard are dropped before optimization.

**Evidence:**
- Implementation: `playlist_service.py` applies `_drop_generated_tracks_after_impossible_bpm_jumps()` to `remaining_tracks` before `recommend_sequence()` for non-strategy-order paths.
- Tests: `tests/test_playlist_service.py` — PASS.

### Requirement: Exact optimizer runs only for n≤15

**GIVEN** 15 tracks  
**WHEN** `recommend_sequence()` is called with default `exact_limit`  
**THEN** the exact solver runs.

**GIVEN** 16 tracks  
**WHEN** `recommend_sequence()` is called with default `exact_limit`  
**THEN** the greedy-2opt heuristic runs.

**Evidence:**
- Test: `tests/test_sequence_optimizer.py::test_recommend_sequence_uses_exact_solver_for_n_15` — PASS.
- Test: `tests/test_sequence_optimizer.py::test_recommend_sequence_uses_heuristic_for_n_16` — PASS.
- Implementation: `optimizer.py` default `exact_limit: int = 15`.

## Capability: desktop-main-window

### Requirement: Search filter debounce prevents UI stutter

**GIVEN** rapid keystrokes in the library search box  
**WHEN** the user types multiple characters within 150ms  
**THEN** `_apply_song_filter()` fires only once after the debounce timer expires.

**Evidence:**
- Test: `tests/test_main_window.py::test_search_filter_debounce_fires_once_for_rapid_input` — PASS.
- Implementation: `MainWindow` uses a single-shot `QTimer` with 150ms interval connected to `search_input.textChanged`.

### Requirement: Lazy tab rendering reduces redundant work

**GIVEN** the user switches workflow tabs  
**WHEN** `_sync_state()` triggers render  
**THEN** only the currently visible screen is rendered; hidden screens are skipped.

**Evidence:**
- Implementation: `MainWindow._render_screens()` reads `_current_tab_index` and renders only the active tab.
- `_on_tab_changed()` updates `_current_tab_index` and triggers `_sync_state()` for immediate visible-screen update.
- Tests: `tests/test_main_window.py` — PASS.

### Requirement: Scan and recommendation threads cannot overlap

**GIVEN** a scan is already running  
**WHEN** a second scan is requested  
**THEN** the first scan is cancelled and the new request receives a fresh request ID.

**Evidence:**
- Test: `tests/test_main_window.py::test_main_window_second_scan_cancels_first_scan` — PASS.
- Implementation: `ScanController` and `RecommendationController` track `_current_request_id`, cancel running threads, and discard stale completion callbacks.

### Requirement: Packaging/release gates never run with root build artifacts

**GIVEN** the test session starts  
**WHEN** `tests/conftest.py` autouse session fixture runs  
**THEN** it asserts project-root `build/` and `dist/` are absent.

**Evidence:**
- Implementation: `tests/conftest.py::_no_root_build_artifacts()` session-scoped autouse fixture.
- `scripts/release_gate_check.py --run` passes.

## Definition of Done

- [x] SDD change has `proposal.md`, `spec.md`, `design.md`, `tasks.md`, `apply-progress.md`, and `verify-report.md`.
- [x] `state.yaml` reflects `verify-complete`.
- [x] `uv run pytest -q` passes (740 tests).
- [x] `uv run ruff check .` passes.
- [x] `uv run ruff format --check .` passes.
- [x] `uv run python scripts/release_gate_check.py --run` passes.

## Sign-off

- **Verified by:** automated test suite + release gate check
- **Date:** 2026-06-14
- **Commit:** `27ca67c`
