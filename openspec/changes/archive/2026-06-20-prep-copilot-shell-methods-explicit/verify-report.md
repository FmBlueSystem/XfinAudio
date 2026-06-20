# Verify Report: Prep Copilot shell methods explicit

Status: passed

## Requirement: Prep Copilot methods are explicit MainWindow methods

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_prep_copilot_shell_methods_are_explicit_main_window_methods -q
```

Result: `1 passed` after the three Prep Copilot names were removed from `LEGACY_LAYOUT_METHODS` and defined directly on `MainWindow`.

## Requirement: Prep Copilot behavior remains delegated

Evidence:

```bash
uv run pytest -q tests/test_main_window_shell_compat.py -k prep
uv run pytest -q tests/test_main_window.py -k "prep_copilot"
```

Result: `1 passed, 16 deselected`; `8 passed, 103 deselected`.

## Requirement: Unrelated grafts stay stable

Evidence:

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

Result:
- `932 passed, 49 warnings`
- `0 errors, 0 warnings, 0 informations`
- `932 passed`, coverage `90.03%`
- `All checks passed!`
- `219 files already formatted`
- Release gate passed, including release readiness smoke, publication docs, artifact hygiene, source package hygiene, and PyInstaller check-only.

## Legacy graft map evidence

Result:
- `remaining_legacy_layout_methods 14`
- `removed prep copilot present? False`
