# Apply Progress: Library scan planning boundary

## 2026-06-20

- Created SDD artifacts for the next library boundary slice.
- RED: added `tests/test_scan_planning.py` and duplicate-candidate scan behavior coverage; focused run failed because `xfinaudio.library.scan_planning` did not exist.
- GREEN: added `xfinaudio.library.scan_planning`, moved supported-extension ownership there, wired `scan_folder()` to plan candidates before metadata reads, and moved config's supported-extension import away from the full scan service.
- REFACTOR: kept scan planning pure, made the planner available from `xfinaudio.library`, and kept scan service focused on execution.
- DOCS: updated `docs/architecture/layered-architecture.md` to record the pure scan planning boundary.
- Focused evidence: `uv run pytest tests/test_scan_planning.py tests/test_scan_service.py tests/test_settings.py -q` passed (`26 passed`).
- Full local evidence: `uv run pytest -q`, `uv run pyright src tests`, `uv run pytest --cov --cov-fail-under=70 -q`, `uv run ruff check .`, `uv run ruff format --check .`, and `uv run python scripts/release_gate_check.py --run` passed.
