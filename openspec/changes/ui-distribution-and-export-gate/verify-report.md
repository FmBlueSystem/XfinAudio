# Verify Report: Review Layout Distribution + Unified Export Gate

Status: pending — completed after apply.

| Req | Description | Evidence | Status |
|-----|-------------|----------|--------|
| R1 | Review tables in QSplitter | — | pending |
| R2 | history_table min <= max | — | pending |
| R3 | Single export-gate predicate | — | pending |

## Verification commands
- [ ] uv run pytest -q
- [ ] uv run pyright src tests
- [ ] uv run pytest --cov --cov-fail-under=70 -q
- [ ] uv run ruff check .
- [ ] uv run ruff format --check .
- [ ] uv run python scripts/release_gate_check.py --run
