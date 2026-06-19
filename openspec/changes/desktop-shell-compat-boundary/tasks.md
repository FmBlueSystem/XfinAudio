# Tasks: Desktop shell compatibility boundary

- [x] RED: Add focused tests proving the compatibility boundary is explicit and legacy methods remain available.
- [x] GREEN: Add `desktop/shell_compat.py`, move the legacy method map/installer there, and update `main_window.py` to use it.
- [x] REFACTOR: Remove the installer from `layout.py` and keep layout focused on layout helpers.
- [x] VERIFY: Run focused tests, pyright, ruff, format check, and full release gate.
- [x] REVIEW: Fresh review before PR.
