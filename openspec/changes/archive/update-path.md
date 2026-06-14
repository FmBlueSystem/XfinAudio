---
status: completed
priority: P2
---

# Change: update-path

## Goal
Document and verify the XfinAudio update approach so users can install a new version without losing the app database or user settings.

## Acceptance criteria
1. A user-facing doc explains where app data lives and how it survives updates.
2. Settings repository preserves existing settings when a new app version reads the same file.
3. Track repository preserves existing scan records when a new app version opens the same database.
4. Automated tests cover update/preservation behavior.
5. All standard verification gates pass.

## Implementation
- Created `docs/update-path.md` documenting app-owned paths (`~/.xfinaudio/xfinaudio.sqlite3` and `~/.xfinaudio/settings.json`), package update commands, settings/database compatibility rules, and environment overrides.
- Added `tests/test_update_path.py` with 4 tests verifying default paths, settings preservation across repository loads, track preservation across repository opens, and `MainWindow.with_defaults` loading pre-existing settings and tracks.

## Files changed
- `docs/update-path.md`
- `tests/test_update_path.py`

## Verification
- `uv run pytest tests/test_update_path.py -q` → 4 passed
- `uv run pytest -q` → 741 passed
- `uv run pytest --cov --cov-fail-under=70 -q` → 89.17% coverage
- `uv run ruff check .` → pass
- `uv run ruff format --check .` → pass
- `uv run pyright src tests` → 0 errors
- `uv run python scripts/release_gate_check.py --run` → pass
