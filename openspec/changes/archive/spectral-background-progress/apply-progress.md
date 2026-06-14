# Apply Progress: Spectral Background Progress Indicator

## Completed

- Created SDD proposal, spec, design, tasks, state, and verify-report skeleton.
- Added `progress_updated(processed_count, total_count)` signal to `SpectralCompletionWorker`.
- Fixed a pre-existing QThread lifetime bug where the runner was destroyed while still referenced, causing segfaults in the worker tests.
- Added `is_completing_spectral`, `spectral_progress_count`, and `spectral_total_count` to `AppState` with an immutable `model_copy(update=...)` helper.
- Wired `MainWindow` to update `AppState` on `progress_updated` and reset it when the worker finishes or is cancelled.
- Updated `LibraryViewModel.status_text()` to show `Analyzing spectral colors {count}/{total}` while completion is active.
- Added unit/integration tests for worker counts, ViewModel status text, and MainWindow state updates.

## TDD Cycle Evidence

| Task | Test File | Layer | RED | GREEN | REFACTOR |
|------|-----------|-------|-----|-------|----------|
| 4. Worker progress | `tests/test_spectral_completion_worker.py` | Unit | ✅ New test failed before signal existed | ✅ Worker emits `[(1, 2), (2, 2)]` for cached + analyzed | ✅ Fixed pre-existing runner destruction bug |
| 5. AppState fields | `tests/test_library_view_model.py`, `tests/test_main_window.py` | Unit/UI | ✅ Constructors failed before fields existed | ✅ Progress text and state updates pass | ➖ Minimal |
| 6. MainWindow wiring | `tests/test_main_window.py` | UI integration | ✅ Slots missing before implementation | ✅ Active/finish state paths pass | ➖ Minimal |
| 7. LibraryViewModel status | `tests/test_library_view_model.py` | Unit | ✅ Status text failed before branch existed | ✅ Spectral progress message passes | ➖ Minimal |

## Test Summary

- **New tests**: 4
- **Focused GREEN**: `uv run pytest tests/test_spectral_completion_worker.py tests/test_library_view_model.py tests/test_main_window.py -q` → 101 passed
- **Full suite**: `uv run pytest -q` → 782 passed

## Verification status

- `uv run pytest -q`: PASS — 782 tests passed
- `uv run pyright src tests`: PASS — 0 errors
- `uv run pytest --cov --cov-fail-under=70 -q`: PASS — 88.05% coverage
- `uv run ruff check .`: PASS
- `uv run ruff format --check .`: PASS
- `uv run python scripts/release_gate_check.py --run`: PASS

## Notes

- `AppState` now exposes `model_copy(update=...)` to make immutable updates explicit.
- Root `dist/` artifacts were present before this work and blocked pytest via `tests/conftest.py`; they were removed so verification could run.
