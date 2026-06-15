# Apply Progress: Replace Tab Sidebar

## Completed

- [x] Implemented `QListWidget` sidebar + `QStackedWidget` content in `MainWindow._build_layout`.
- [x] Wired sidebar row changes to stacked-widget navigation and kept `workflow_tabs` as a stack alias with tab-like compatibility methods.
- [x] Added sidebar dark-theme styling in `theme.py`.
- [x] Updated `tests/test_main_window.py` to assert the sidebar labels, accessible item names, and seven stacked screens.
- [x] Verified with the required focused and full command suite.

## TDD Cycle Evidence

| Task | RED | GREEN | REFACTOR |
|---|---|---|---|
| Sidebar layout replacement | `uv run pytest tests/test_main_window.py -q` failed after test update because `workflow_sidebar` did not exist. | Production code replaced `QTabWidget` with sidebar + stack; focused tests passed (`93 passed`). | Added stack compatibility for existing tests/coordinators and kept lint/format clean. |

## Verification

- `uv run pytest tests/test_main_window.py -q` — PASS, 93 passed.
- `uv run pytest -q` — PASS, 815 passed.
- `uv run pyright src tests` — PASS.
- `uv run pytest --cov --cov-fail-under=70 -q` — PASS, coverage 88.62%.
- `uv run ruff check .` — PASS.
- `uv run ruff format --check .` — PASS.
- `uv run python scripts/release_gate_check.py --run` — PASS.
