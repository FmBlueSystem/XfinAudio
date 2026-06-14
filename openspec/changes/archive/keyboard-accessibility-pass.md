---
status: completed
priority: P2
---

# Change: keyboard-accessibility-pass

## Goal
Ensure the main XfinAudio desktop workflow can be driven from the keyboard with readable labels and a predictable tab order.

## Acceptance criteria
1. Global keyboard shortcuts exist for the most common actions:
   - `Ctrl+O` → Choose music folder.
   - `Ctrl+S` → Scan metadata.
   - `Ctrl+R` → Recommend playlist.
   - `Ctrl+E` → Export recommendation.
   - `Esc` → Cancel active scan.
2. Each screen defines a logical tab order for its primary controls.
3. Primary interactive widgets expose descriptive `accessibleName` text.
4. Automated tests verify shortcuts, tab order, and accessible names.

## Implementation
- Added `MainWindow._connect_keyboard_shortcuts()` registering `QShortcut` instances for the main workflow actions; shortcuts are stored in `self._keyboard_shortcuts` for introspection/testing.
- Added `_setup_accessibility()` and `_setup_tab_order()` helpers to `LibraryScreen`, `BuildScreen`, `ReviewScreen`, `ExportScreen`, and `MetadataScreen`.
- Accessible names were set on every primary interactive control (buttons, inputs, tables, combos).
- Logical tab chains were declared within each screen.
- Added `tests/test_keyboard_accessibility.py` with 12 tests covering accessible names, shortcut registration, shortcut action invocation, and focus policies.

## Files changed
- `src/xfinaudio/desktop/main_window.py`
- `src/xfinaudio/desktop/screens/library_screen.py`
- `src/xfinaudio/desktop/screens/build_screen.py`
- `src/xfinaudio/desktop/screens/review_screen.py`
- `src/xfinaudio/desktop/screens/export_screen.py`
- `src/xfinaudio/desktop/screens/metadata_screen.py`
- `tests/test_keyboard_accessibility.py`

## Verification
- `uv run pytest tests/test_keyboard_accessibility.py -q` → 12 passed
- `uv run pytest -q` → 737 passed
- `uv run pytest --cov --cov-fail-under=70 -q` → 89.13% coverage
- `uv run ruff check .` → pass
- `uv run ruff format --check .` → pass
- `uv run pyright src tests` → 0 errors
- `uv run python scripts/release_gate_check.py --run` → pass
