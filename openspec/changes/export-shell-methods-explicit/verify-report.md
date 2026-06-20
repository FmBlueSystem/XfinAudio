# Verify Report: Export shell methods explicit

Status: passed

## Requirement: Export shell methods are explicit MainWindow methods

Evidence:
- RED command failed as expected before production changes:
  `uv run pytest tests/test_main_window_shell_compat.py::test_export_shell_methods_are_explicit_main_window_methods -q`
- GREEN focused command passed after explicit delegators and graft-map removal:
  `uv run pytest tests/test_main_window_shell_compat.py::test_export_shell_methods_are_explicit_main_window_methods -q` → `1 passed`.
- Focused shell/main-window suite passed:
  `uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py tests/test_visual_integration.py -q` → `138 passed`.

## Requirement: Export behavior remains delegated to the existing export boundary

Evidence:
- `MainWindow` explicit methods delegate to `self._export_actions` for export behavior.
- `_format_safe_export_folder_label` delegates to `self._settings_controller.format_safe_export_folder_label()` when the settings controller exists, preserving the previous fallback for early initialization.
- Full release gates passed locally.

## Requirement: Remaining legacy layout grafting stays stable

Evidence:
- `test_shell_compat_names_legacy_layout_methods` still verifies unrelated grafted methods remain in the compatibility map.
- Focused shell/main-window suite passed.

## Full Local Verification

Command:

```bash
uv run pytest -q && uv run pyright src tests && uv run pytest --cov --cov-fail-under=70 -q && uv run ruff check . && uv run ruff format --check . && uv run python scripts/release_gate_check.py --run
```

Result:
- `uv run pytest -q` → `927 passed`.
- `uv run pyright src tests` → `0 errors, 0 warnings, 0 informations`.
- `uv run pytest --cov --cov-fail-under=70 -q` → `927 passed`, total coverage `90.23%`.
- `uv run ruff check .` → passed.
- `uv run ruff format --check .` → `219 files already formatted`.
- `uv run python scripts/release_gate_check.py --run` → passed release readiness smoke, publication docs, artifact hygiene, source package hygiene, PyInstaller check-only, and root artifact hygiene.

## Safety

No audio mutation, DSP scope, dependency changes, packaging changes, or live Serato DB V2 writes were introduced.
