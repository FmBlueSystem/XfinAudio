# Apply Progress: performance-bottleneck-fixes

## Status

All tasks complete. Commit delivered as part of the consolidated XfinAudio refactor commit.

## Completed Tasks

### Task 1 — Session-scoped transition score cache

- [x] 1.1 Added optional `cache: dict | None = None` parameter to `score_transition()` in `src/xfinaudio/recommendation/scoring.py`.
- [x] 1.2 Built cache key from `(left.path, right.path, id(weights), id(config), id(boost_rules))`.
- [x] 1.3 Threaded `cache` through `optimizer.py` → `_score_matrix()` and `playlist_service.py` → `_score_ordered_tracks()`.
- [x] 1.4 Verified `tests/test_transition_scoring.py` cache behavior.

### Task 2 — Debounce search filter with QTimer

- [x] 2.1 Added `QTimer` state in `MainWindow._initialize_window_state` (single-shot, 150ms).
- [x] 2.2 Connected `search_input.textChanged` to `_search_debounce.start`.
- [x] 2.3 Connected `_search_debounce.timeout` to `_apply_song_filter(clear_selection=True)`.
- [x] 2.4 Verified `tests/test_main_window.py::test_search_filter_debounce_fires_once_for_rapid_input`.

### Task 3 — Move BPM pre-filter before optimizer

- [x] 3.1 Applied `_drop_generated_tracks_after_impossible_bpm_jumps()` to `remaining_tracks` before `recommend_sequence()` for the heuristic optimizer path.
- [x] 3.2 Preserved post-optimizer drop for the strategy-order path, which does not use the TSP optimizer.
- [x] 3.3 Verified `tests/test_playlist_service.py`.

### Task 4 — Lazy-render only visible tab screen

- [x] 4.1 Added `_current_tab_index` tracking in `MainWindow._initialize_window_state`.
- [x] 4.2 Connected `workflow_tabs.currentChanged` to `_on_tab_changed`.
- [x] 4.3 Modified `_render_screens()` to render only the screen at the current tab index.
- [x] 4.4 Verified `tests/test_main_window.py` and screen tests.

### Task 5 — Lower exact optimizer cap to n=15

- [x] 5.1 Changed `exact_limit` default from `20` to `15` in `src/xfinaudio/recommendation/optimizer.py`.
- [x] 5.2 Verified `tests/test_sequence_optimizer.py::test_recommend_sequence_uses_exact_solver_for_n_15` and `test_recommend_sequence_uses_heuristic_for_n_16`.

### Task 6 — Thread lifecycle guards

- [x] 6.1 Added `_current_request_id` to `ScanController` and `RecommendationController`.
- [x] 6.2 Added cancel-and-wait logic at the start of `start_scan()` / `start_recommendation()`.
- [x] 6.3 Wrapped completion/failure handlers with stale-request checks.
- [x] 6.4 Updated `MainWindow.closeEvent()` to call `cancel()` on both controllers.
- [x] 6.5 Verified `tests/test_main_window.py::test_main_window_second_scan_cancels_first_scan`.

### Task 7 — Fix packaging/release-gate tests

- [x] 7.1 Ensured project-root `build/` and `dist/` are absent.
- [x] 7.2 Added session-scoped autouse fixture `_no_root_build_artifacts()` in `tests/conftest.py`.
- [x] 7.3 Verified `scripts/release_gate_check.py --run` passes.
