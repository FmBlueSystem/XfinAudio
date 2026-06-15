# Apply Progress: Phase 3 - Quick Filter Bar

## Completed

- Added a persistent `QHBoxLayout` quick filter bar above the Library track table.
- Added checkable `QPushButton` filters for Complete, Incomplete, Missing BPM, Missing Key, and Missing Energy.
- Added a Clear Filters button and an active filter count label.
- Wired quick filters through existing `LibraryViewModel.tracks_for_display(..., LibraryFilters(...))` filtering.
- Added focused Library screen tests for checkable filters, active count, filtering, and clearing.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2-5 | `tests/test_library_screen.py` | UI integration | ✅ 6/6 baseline | ✅ New quick-filter test failed on missing widgets | ✅ 7/7 focused tests passed | ✅ Filtered row + clear-to-all paths covered | ✅ Formatted and release gate passed |

## Verification

- `uv run pytest tests/test_library_screen.py tests/test_library_view_model.py -q` — PASS, 7 passed
- `uv run python scripts/release_gate_check.py --run` — PASS
