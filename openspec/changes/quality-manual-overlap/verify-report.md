# Verify report: quality-manual-overlap

## Requirement: Manual overlap uses distinct manual reference paths

### Evidence
- Focused RED confirmed duplicate manual paths previously lowered `manual_overlap_ratio` to `0.333333`.
- GREEN implementation now reports `0.5` when one of two distinct manual reference paths is present in the generated recommendation.

## Architecture boundary evidence
- `xfinaudio.exporting` and `xfinaudio.recommendation` package exports are lazy to avoid package-level dependency cycles.
- Runtime public import smoke passed for `SeratoExportPlan`, `export_playlist_json`, `recommend_playlist`, and `score_transition`.

## Full verification
- `uv run pytest -q` -> 951 passed.
- `uv run pyright src tests` -> 0 errors, 0 warnings.
- `uv run pytest --cov --cov-fail-under=70 -q` -> 951 passed, total coverage 90.01%.
- `uv run ruff check .` -> pass.
- `uv run ruff format --check .` -> 228 files already formatted.
- `uv run python scripts/release_gate_check.py --run` -> pass, including release readiness smoke, publication docs, artifact hygiene, source package hygiene, PyInstaller check-only, and root artifact hygiene.
