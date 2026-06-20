# Verify Report: Recommendation shell methods explicit

Status: passed

## Requirement: Recommendation methods are explicit MainWindow methods

Passed. The RED test failed before production changes because `recommend_playlist` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`. After GREEN, the selected Recommendation methods are direct `MainWindow` methods and absent from the graft map.

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_recommendation_shell_methods_are_explicit_main_window_methods -q
# RED: failed as expected before production changes

uv run pytest tests/test_main_window_shell_compat.py -q
# 18 passed
```

## Requirement: Recommendation behavior remains delegated

Passed. The explicit methods delegate to `RecommendationService` and `DjReadinessController` while preserving existing recommendation and DJ readiness behavior.

Evidence:

```bash
uv run pytest tests/test_main_window.py::test_main_window_recommendation_runs_in_background_without_blocking_ui   tests/test_main_window.py::test_main_window_renders_dj_readiness_check_table_after_recommendation   tests/test_main_window.py::test_main_window_colors_dj_readiness_status_cells   tests/test_main_window.py::test_main_window_clears_applied_copilot_variant_badge_for_normal_recommendation -q
# 4 passed
```

## Requirement: Bridge and spectral grafts stay stable

Passed. `LEGACY_LAYOUT_METHODS` now contains 6 methods. `_on_copilot_variant_applied` remains grafted for its dedicated bridge slice, and the five spectral completion grafts remain unchanged.

Remaining grafts:

```text
_on_copilot_variant_applied
_start_spectral_completion_worker
_cancel_spectral_completion_worker
_on_spectral_progress_updated
_on_spectral_profile_ready
_on_spectral_completion_finished
```

## Full verification

Passed.

```bash
uv run pytest -q
# 933 passed, 42 warnings

uv run pyright src tests
# 0 errors, 0 warnings, 0 informations

uv run pytest --cov --cov-fail-under=70 -q
# 933 passed, 22 warnings; total coverage 89.95%

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
