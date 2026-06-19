# Verify Report

## Requirement: Legacy shell methods remain available

Status: PASS

Evidence:
- `tests/test_main_window_shell_compat.py::test_main_window_keeps_legacy_layout_methods_available` passed.
- `MainWindow.choose_folder`, `MainWindow._apply_song_filter`, and `MainWindow._refresh_idle_action_state` remain callable.

## Requirement: Compatibility grafting is explicit

Status: PASS

Evidence:
- `tests/test_main_window_shell_compat.py::test_shell_compat_names_legacy_layout_methods` passed.
- `tests/test_main_window_shell_compat.py::test_layout_no_longer_owns_legacy_method_installation` passed.
- `src/xfinaudio/desktop/shell_compat.py` owns `LEGACY_LAYOUT_METHODS` and `install_legacy_layout_methods`.
- `src/xfinaudio/desktop/layout.py` no longer exposes `install_layout_methods`.

## Requirement: Product behavior is unchanged

Status: PASS

Evidence:
- RED observed: `uv run pytest tests/test_main_window_shell_compat.py -q` failed before `shell_compat` existed.
- GREEN observed: `uv run pytest tests/test_main_window_shell_compat.py -q` passed with 3 tests.
- Focused desktop shell tests passed: `uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py -q` passed with 114 tests.
- `uv run pyright src tests` passed with 0 errors.
- `uv run ruff check .` passed.
- `uv run ruff format --check .` passed.
- `uv run python scripts/release_gate_check.py --run` passed.
- Full suite: 918 passed.
- Coverage: 90.31%, above the 70% gate.

Safety:
- No product behavior, UI copy, business logic, AppState transition, audio, export, storage, or Serato behavior changes were introduced.
