# Verify Report: Remove empty shell layout compatibility surface

Status: passed

## Requirement: Layout graft surface removed

Passed. `main_window.py` no longer references `shell_layout_compat` or `install_legacy_layout_methods`; `shell_compat` no longer exposes layout graft names; `src/xfinaudio/desktop/shell_layout_compat.py` was deleted.

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_layout_compat_graft_surface_is_removed -q
# RED: failed as expected before removal

uv run pytest tests/test_main_window_shell_compat.py -q
# 19 passed
```

## Requirement: Explicit behavior preserved

Passed. MainWindow focused regression tests passed.

```bash
uv run pytest tests/test_main_window.py -q
# 111 passed
```

## Full verification

Passed after updating durable specs to reflect the removed layout graft surface.

```bash
uv run pytest -q
# 934 passed

uv run pyright src tests
# 0 errors, 0 warnings, 0 informations

uv run pytest --cov --cov-fail-under=70 -q
# 934 passed, total coverage 89.88%

uv run ruff check .
# All checks passed

uv run ruff format --check .
# 218 files already formatted

uv run python scripts/release_gate_check.py --run
# PASS tests
# PASS type-check
# PASS coverage
# PASS lint
# PASS format
# PASS release readiness smoke
# PASS open-source publication docs
# PASS publication artifact hygiene
# PASS source package hygiene
# PASS PyInstaller check-only
# PASS root artifact hygiene
```

## Safety

- No audio files were mutated.
- No DSP scope was added.
- No live Serato database V2 writes were introduced.
- No dependencies were changed.
- No project-root `build/` or `dist/` artifacts were created.
