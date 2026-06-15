# Apply Progress: Live Assistant Guidance

## Completed

- Added `LiveAssistantScreen` guidance banner with `QLabel`, `objectName="guidanceLabel"`, `setWordWrap(True)`, and i18n via `self.tr(...)`.
- Banner explains the three-step flow, shortcut hints, and scan-first candidate population fallback.
- Banner is visible by default and hidden when `set_current_track(...)` loads the now-playing content.
- Added focused Qt widget tests for visible empty-state guidance and hidden guidance after a current track is set.

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| Add guidance banner | `tests/test_live_assistant_screen.py` | UI widget | ✅ `11 passed` baseline | ✅ New guidance test failed: no `guidanceLabel` found | ✅ `13 passed` after implementation | ✅ Added hide-when-current-track assertion | ➖ None needed |

## Verification

- ✅ `uv run pytest tests/ -k live_assistant -q` — 28 passed, 787 deselected.
- ❌ `uv run pytest -q` — unrelated failures in `tests/test_main_window.py` and `tests/test_visual_integration.py`.
- ✅ `uv run pyright src tests` — 0 errors.
- ❌ `uv run pytest --cov --cov-fail-under=70 -q` — coverage threshold met, but unrelated test failures in `tests/test_keyboard_accessibility.py` and `tests/test_visual_integration.py`.
- ❌ `uv run ruff check .` — unrelated import formatting / line length in `tests/test_main_window.py`.
- ❌ `uv run ruff format --check .` — unrelated `tests/test_main_window.py` would reformat.
- ❌ `uv run python scripts/release_gate_check.py --run` — fails at full pytest due unrelated keyboard/navigation failures.

## Pending

- Resolve unrelated existing full-suite/release gate failures before PR readiness.
