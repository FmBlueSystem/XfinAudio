# Tasks: Technical Debt Cleanup

## Review Workload Forecast

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

| Field | Value |
|-------|-------|
| Estimated changed lines | ~610 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Items 1–3 (~160 lines); PR 2: Item 4 (~450 lines) |

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Trivial cleanup + missing tests | PR 1 | Items 1/2/3; self-contained; ~160 lines |
| 2 | Extract ExportCoordinator | PR 2 | Item 4; self-contained; ~450 lines; depends on PR 1 for clean main |

## Phase 1: Foundation (Items 1 & 2)

- [x] 1.1 Delete `_populate_prep_copilot_table` method from `main_window.py` (L1668–1677)
- [x] 1.2 Change `exact_limit` default `20`→`15` in `settings.py` L28

## Phase 2: Core Implementation (Item 4)

- [ ] 2.1 Add `ExportCoordinator` class to `export_coordinator.py` with `host: "MainWindow"` protocol
- [ ] 2.2 Move `_selected_export_software`, `preview_export`, `export_recommendation`, `preview_serato_export`, `export_recommendation_to_serato` bodies into coordinator
- [ ] 2.3 Move `_plan_current_serato_export`, `export_metadata_status_to_serato`, `_export_missing_metadata_worklist_to_serato`, `_record_serato_export`, `_render_serato_export_history` bodies into coordinator
- [ ] 2.4 Construct `ExportCoordinator(host=self)` in `MainWindow.__init__`
- [ ] 2.5 Replace export method bodies in `MainWindow` with 1-line delegation wrappers
- [ ] 2.6 Add `TYPE_CHECKING` import to avoid circular import
- [ ] 2.7 Verify: `uv run pytest tests/ -q --tb=short`

## Phase 3: Testing (Item 3)

- [ ] 3.1 Add `test_score_transition_cache_returns_same_object_for_identical_pair` to `test_transition_scoring.py`
- [ ] 3.2 Add `test_score_transition_new_session_cache_starts_empty` to `test_transition_scoring.py`
- [ ] 3.3 Add `test_recommend_sequence_routes_n15_exact_and_n16_heuristic` to `test_sequence_optimizer.py`
- [ ] 3.4 Add `test_main_window_second_scan_cancels_previous_run` to `test_main_window.py`
- [ ] 3.5 Add `test_main_window_search_debounce_fires_filter_once_after_rapid_keystrokes` to `test_main_window.py`
- [ ] 3.6 Verify: `uv run pytest tests/test_transition_scoring.py tests/test_playlist_service.py tests/test_sequence_optimizer.py tests/test_main_window.py -x -q`
