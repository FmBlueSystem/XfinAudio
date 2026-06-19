# Verify Report

## Requirement: MainWindow uses explicit compatibility surfaces internally

Status: PASS

Evidence:
- RED: `uv run pytest tests/test_main_window_shell_compat.py::test_main_window_uses_explicit_shell_compatibility_surfaces -q` failed because `MainWindow` still imported `shell_compat as _shell_compat`.
- GREEN: the same focused test passed after migrating `MainWindow` to `shell_layout_compat` and `shell_state_compat`.
- Focused desktop shell suite passed: `uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py -q` — 121 passed.

## Requirement: Legacy facade remains compatible

Status: PASS

Evidence:
- Existing `shell_compat` facade tests still pass in `tests/test_main_window_shell_compat.py`.
- `shell_compat.py` remains unchanged as a re-export facade for legacy imports.

## Full verification

- `uv run pytest -q` — PASS, 925 passed.
- `uv run pyright src tests` — PASS, 0 errors.
- `uv run pytest --cov --cov-fail-under=70 -q` — PASS, 925 passed, 90.40% coverage.
- `uv run ruff check .` — PASS.
- `uv run ruff format --check .` — PASS, 219 files already formatted.
- `uv run python scripts/release_gate_check.py --run` — PASS.
