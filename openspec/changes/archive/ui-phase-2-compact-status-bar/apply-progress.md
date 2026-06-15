# Apply Progress: Phase 2 - Compact Status Bar

## Completed

- [x] Create `StatusBar` widget with folder, guidance, and scan progress sections.
- [x] Move `folder_label`, `library_guidance_label`, and `scan_progress_label` into the bottom compact status bar.
- [x] Add a `Status` toggle button for manual show/hide.
- [x] Show the status bar automatically when scan state begins.
- [x] Verify focused and full command suite.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| StatusBar widget + moved labels | `tests/test_main_window.py` | UI integration | ✅ `95 passed` baseline | ✅ 4 tests failed before implementation | ✅ `99 passed` focused | ✅ hidden/default, layout sections, toggle, scan auto-show | ✅ Extracted `StatusBar` widget |

## Verification

- ✅ `uv run pytest tests/test_main_window.py -q` — 99 passed
- ✅ `uv run pytest -q` — 822 passed, 4 warnings
- ✅ `uv run pyright src tests` — 0 errors
- ✅ `uv run pytest --cov --cov-fail-under=70 -q` — 822 passed, coverage 88.93%
- ✅ `uv run ruff check .` — all checks passed
- ✅ `uv run ruff format --check .` — 186 files already formatted
- ✅ `uv run python scripts/release_gate_check.py --run` — passed

## Notes

- No audio files were mutated.
- No DSP scope was added.
- Commit/PR remains pending.
