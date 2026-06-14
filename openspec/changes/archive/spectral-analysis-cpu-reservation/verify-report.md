# Verify Report: Reserve One CPU Core for UI During Spectral Analysis

## Verification commands

| Command | Result |
|---|---|
| `uv run pytest tests/test_batch_analyzer.py tests/test_spectral_completion_worker.py -q` | PASS — 12 passed |
| `uv run pytest -q` | PASS — 788 passed, 2 warnings |
| `uv run pyright src tests` | PASS — 0 errors, 0 warnings |
| `uv run pytest --cov --cov-fail-under=70 -q` | PASS — 788 passed, 2 warnings; total coverage 88.09% |
| `uv run ruff check .` | PASS — all checks passed |
| `uv run ruff format --check .` | PASS — 184 files already formatted |
| `uv run python scripts/release_gate_check.py --run` | PASS — release gate checks passed |

## Requirement verification

| Requirement | Evidence | Status |
|---|---|---|
| R1. Background worker uses `cpu_count - 1` | `tests/test_spectral_completion_worker.py` | PASS |
| R2. Batch analyzer uses `cpu_count - 1` | `tests/test_batch_analyzer.py` | PASS |
| R3. Test seam deterministic | Same tests | PASS |
