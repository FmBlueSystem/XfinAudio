# Apply Progress: Recommendation shell methods explicit

Status: verified

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_recommendation_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `recommend_playlist` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow.recommend_playlist()` delegating to `RecommendationService.recommend()`.
- Added explicit recommendation lifecycle delegators for begin/end/start/finish/fail.
- Added explicit `MainWindow._populate_dj_readiness_table()` delegating to `DjReadinessController.populate_table()`.
- Added explicit `MainWindow._on_recommend_requested()` delegating to `RecommendationService.on_recommend_requested()`.
- Removed the eight Recommendation names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Preserved `_on_copilot_variant_applied` in the graft map for the bridge slice.
- Updated architecture docs and elimination plan progress.

Focused commands:

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
uv run pytest tests/test_main_window.py::test_main_window_recommendation_runs_in_background_without_blocking_ui tests/test_main_window.py::test_main_window_renders_dj_readiness_check_table_after_recommendation tests/test_main_window.py::test_main_window_colors_dj_readiness_status_cells tests/test_main_window.py::test_main_window_clears_applied_copilot_variant_badge_for_normal_recommendation -q
```

Result: `18 passed`; `4 passed`.

The legacy layout graft map now has 6 methods, and the eight Recommendation names are absent.


## VERIFY

Focused and full gates passed.

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
# 18 passed

uv run pytest tests/test_main_window.py::test_main_window_recommendation_runs_in_background_without_blocking_ui \
  tests/test_main_window.py::test_main_window_renders_dj_readiness_check_table_after_recommendation \
  tests/test_main_window.py::test_main_window_colors_dj_readiness_status_cells \
  tests/test_main_window.py::test_main_window_clears_applied_copilot_variant_badge_for_normal_recommendation -q
# 4 passed

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
# PASS
```

The legacy layout graft map has 6 methods after this slice.
