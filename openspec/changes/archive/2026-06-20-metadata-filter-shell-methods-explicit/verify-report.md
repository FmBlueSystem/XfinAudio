# Verify Report: Metadata filter shell methods explicit

Status: passed

## Requirement: Metadata filter methods are explicit MainWindow methods

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_metadata_filter_shell_methods_are_explicit_main_window_methods -q
```

Result: `1 passed` after the four Metadata filter names were removed from `LEGACY_LAYOUT_METHODS` and defined directly on `MainWindow`.

## Requirement: Metadata filter behavior remains delegated

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py tests/test_library_filter.py -q
```

Result: `24 passed`.

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
- `931 passed, 44 warnings`
- `0 errors, 0 warnings, 0 informations`
- `931 passed`, coverage `90.06%`
- `All checks passed!`
- `219 files already formatted`
- Release gate passed, including release readiness smoke, publication docs, artifact hygiene, source package hygiene, and PyInstaller check-only.

## Legacy graft map evidence

Result:
- `remaining_legacy_layout_methods 17`
- `removed metadata filter present? False`
