# Verify Report

## Requirement: Library shell methods are explicit MainWindow methods

Status: PASS

Evidence:
- RED: `uv run pytest tests/test_main_window_shell_compat.py::test_library_shell_methods_are_explicit_main_window_methods -q` failed because `choose_folder` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- GREEN: the same test passed after adding explicit `MainWindow` delegators and removing `choose_folder` plus `_refresh_idle_action_state` from the graft map.
- Focused shell/MainWindow/visual tests passed: `uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py tests/test_visual_integration.py -q` — 137 passed.

## Requirement: Remaining legacy layout grafting stays stable

Status: PASS

Evidence:
- `test_shell_compat_names_legacy_layout_methods` still verifies `_apply_song_filter` remains in the compatibility map.
- `test_main_window_keeps_legacy_layout_methods_available` verifies `choose_folder`, `_apply_song_filter`, and `_refresh_idle_action_state` remain callable on `MainWindow`.

## Full verification

- `uv run pytest -q` — PASS, 926 passed.
- `uv run pyright src tests` — PASS, 0 errors.
- `uv run pytest --cov --cov-fail-under=70 -q` — PASS, 926 passed, 90.38% coverage.
- `uv run ruff check .` — PASS.
- `uv run ruff format --check .` — PASS, 219 files already formatted.
- `uv run python scripts/release_gate_check.py --run` — PASS.
