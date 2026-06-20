# Verify Report: Copilot variant shell bridge explicit

Status: passed

## Requirement: Explicit Copilot variant bridge

Passed. `_on_copilot_variant_applied` is now a direct `MainWindow` method and absent from `LEGACY_LAYOUT_METHODS`.

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_prep_copilot_shell_methods_are_explicit_main_window_methods -q
# RED: failed as expected before production changes

uv run pytest tests/test_main_window_shell_compat.py -q
# 18 passed
```

## Requirement: Behavior preservation

Passed. The explicit bridge delegates to `PrepCopilotController.on_variant_applied(index)`, and focused Prep Copilot behavior tests passed.

Evidence:

```bash
uv run pytest tests/test_main_window.py -q -k "prep_copilot or copilot_variant or applied_copilot_variant_badge"
# 11 passed, 100 deselected
```

## Remaining grafts

The legacy layout graft map now has 5 methods, all spectral completion methods:

```text
_start_spectral_completion_worker
_cancel_spectral_completion_worker
_on_spectral_progress_updated
_on_spectral_profile_ready
_on_spectral_completion_finished
```

## Full verification

Passed after formatting the updated shell compatibility test.

```bash
uv run pytest -q
# 933 passed, 36 warnings

uv run pyright src tests
# 0 errors, 0 warnings, 0 informations

uv run pytest --cov --cov-fail-under=70 -q
# 933 passed, total coverage 89.94%

uv run ruff check .
# All checks passed

uv run ruff format --check .
# 219 files already formatted

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
