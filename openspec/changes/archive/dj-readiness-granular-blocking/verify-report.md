# Verify Report: Granular DJ Readiness Blocking

## Verification commands

| Command | Result |
|---|---|
| `uv run pytest -q` | PENDING |
| `uv run pyright src tests` | PENDING |
| `uv run pytest --cov --cov-fail-under=70 -q` | PENDING |
| `uv run ruff check .` | PENDING |
| `uv run ruff format --check .` | PENDING |
| `uv run python scripts/release_gate_check.py --run` | PENDING |

## Requirement verification

| Requirement | Evidence | Status |
|---|---|---|
| R1. Soft warnings | `tests/test_dj_readiness.py` | PENDING |
| R2. Hard blockers | `tests/test_dj_readiness.py` | PENDING |
| R3. Export gating | `tests/test_review_view_model.py` | PENDING |
