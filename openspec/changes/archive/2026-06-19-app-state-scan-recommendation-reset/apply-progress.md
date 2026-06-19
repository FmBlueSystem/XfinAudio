# Apply Progress: AppState scan recommendation reset boundary

## Completed

- RED: Added focused test for immutable scan-context reset behavior in `tests/test_app_state_transitions.py`; observed failing assertion because `apply_scan_context_reset` did not exist.
- GREEN: Added `apply_scan_context_reset()` to `src/xfinaudio/desktop/app_state_transitions.py`.
- REFACTOR: Updated `LibraryController.clear_scan_dependent_state()` to call the pure transition instead of directly mutating scan/recommendation fields.

## Evidence

- `uv run pytest tests/test_app_state_transitions.py::test_apply_scan_context_reset_clears_scan_and_recommendation_state_immutably -q` initially failed as expected.
- `uv run pytest tests/test_app_state_transitions.py tests/test_main_window.py::test_track_removal_is_undoable_and_redoable tests/test_main_window.py::test_main_window_recommend_with_no_scanned_records_clears_review_state -q` passed.
- `uv run pyright src tests` passed.
