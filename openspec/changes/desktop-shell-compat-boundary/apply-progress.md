# Apply progress: Desktop shell compatibility boundary

- Created approved issue #133.
- Created branch `refactor/desktop-shell-compat-boundary`.
- RED: `uv run pytest tests/test_main_window_shell_compat.py -q` failed because `xfinaudio.desktop.shell_compat` did not exist.
- GREEN: added `src/xfinaudio/desktop/shell_compat.py`, moved legacy MainWindow layout method grafting out of `layout.py`, and updated `main_window.py` to install through the named compatibility boundary.
- Fixed a transcription bug in the moved mapping (`metadata_main_missing_field_records`) caught by the new test.
- Focused shell tests passed: `tests/test_main_window_shell_compat.py tests/test_main_window.py` — 114 passed.
- Pyright passed: 0 errors.
- Ruff check passed.
- Ruff format check passed after formatting `layout.py`.
- Full release gate passed: 918 tests, 90.31% coverage, release smoke/docs/artifact/source-package/PyInstaller checks passed.

- Fresh review found the implementation correct but the review budget exceeded 400 because the long local implementation plan was included. Removed the plan from PR scope and kept SDD artifacts as the durable handoff.
- Marked SDD task checkboxes complete to match verified state.
