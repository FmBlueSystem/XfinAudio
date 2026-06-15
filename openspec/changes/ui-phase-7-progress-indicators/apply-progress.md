# Apply Progress: Phase 7 - Progress Indicators

## Completed

- Added inline `QProgressBar` widgets and ETA labels for scan, recommend, and export button rows.
- Added shared progress percentage and estimated-time formatting in `scan_controller.py`.
- Added transient progress fields to `AppState` for scan, recommend, and export render state.
- Added focused UI tests for visible progress, percentage/ETA text, and hide-on-complete behavior.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Add scan progress bar | `tests/test_library_screen.py` | UI unit | ✅ 27/27 existing screen tests | ✅ Failed on missing progress state/widget | ✅ 7 focused tests passed | ✅ visible + completion-hide cases | ✅ shared progress helpers |
| Add recommend progress bar | `tests/test_build_screen.py` | UI unit | ✅ 27/27 existing screen tests | ✅ Failed on missing progress state/widget | ✅ 7 focused tests passed | ✅ visible + completion-hide cases | ✅ shared progress helpers |
| Add export progress bar | `tests/test_export_screen.py` | UI unit | ✅ 27/27 existing screen tests | ✅ Failed on missing progress state/widget | ✅ 7 focused tests passed | ✅ visible + completion-hide cases | ✅ shared progress helpers |
| Add estimated time calculation | `tests/test_library_screen.py`, `tests/test_build_screen.py`, `tests/test_export_screen.py` | UI unit | ✅ 27/27 existing screen tests | ✅ Failed before formatter/state existed | ✅ 7 focused tests passed | ✅ 25%, 40%, and 50% cases | ✅ centralized in `progress_status_text` |

## Verification

- PASS: `uv run pytest tests/test_library_screen.py tests/test_build_screen.py tests/test_export_screen.py -q` — 7 passed.
- PASS: `uv run pytest -q` — 825 passed.
- PASS: `uv run pyright src tests` — 0 errors.
- PASS: `uv run pytest --cov --cov-fail-under=70 -q` — 825 passed, coverage 89.06%.
- PASS: `uv run ruff check .`.
- PASS: `uv run ruff format --check .`.
- PASS: `uv run python scripts/release_gate_check.py --run`.
