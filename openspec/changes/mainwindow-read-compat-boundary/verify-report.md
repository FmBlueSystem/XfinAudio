# Verify Report: MainWindow Read Compatibility Boundary

## Requirement: Explicit legacy state read compatibility
Status: PASS

Evidence:
- `uv run pytest tests/test_main_window_shell_compat.py::test_shell_compat_exposes_legacy_state_read_boundary -q` failed during RED because `try_get_legacy_app_state_attribute` did not exist.
- `uv run pytest tests/test_main_window_shell_compat.py -q` passed after adding the explicit shell compatibility read boundary.

## Requirement: Delegated shell reads remain available
Status: PASS

Evidence:
- `test_shell_compat_handles_delegated_reads_and_missing_private_attributes` verifies `undo`, `redo`, and `_on_track_remove_requested` delegate through the compatibility helper.
- `uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py -q` passed: 119 passed.

## Requirement: Missing private attributes stay protected
Status: PASS

Evidence:
- `test_shell_compat_handles_delegated_reads_and_missing_private_attributes` verifies unsupported private reads raise `AttributeError`.
- `uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py -q` passed: 119 passed.

## Full Verification
Status: PASS

Commands:
- `uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py -q` — PASS, 119 passed.
- `uv run pyright src tests` — PASS, 0 errors.
- `uv run ruff check .` — PASS.
- `uv run ruff format --check .` — PASS, 217 files already formatted.
- `uv run pytest -q` — PASS, 923 passed.
- `uv run pytest --cov --cov-fail-under=70 -q` — PASS, 923 passed, 90.40% coverage.
- `uv run python scripts/release_gate_check.py --run` — PASS.

## Safety
Status: PASS

- No audio mutation.
- No DSP scope added.
- No live Serato DB V2 writes.
- No dependency changes.
- No project-root `build/` or `dist/` artifacts created.
