# Verify Report: arc-subset-sequencing

**Change**: arc-subset-sequencing
**Status: pending** — an independent verification has NOT been performed.
**Commit range under test**: `490f79a..3245943` on `feat/arc-subset-sequencing`
(`04eeace` optimizer primitive, `b0c25fa` service routing, `3245943` governance).

The commands below were measured by the orchestrating session on this branch
(`feat/arc-subset-sequencing`, macOS, Python 3.11, `uv`). They are recorded here as
local validation evidence, not as independent verification.

## Measured evidence

```text
uv run pytest tests/test_sequence_optimizer.py tests/test_playlist_service.py -q
-> 241 passed in 3.51s

uv run pytest -q
-> 1901 passed, 45 warnings in 77.13s

uv run pytest --cov --cov-fail-under=70 -q
-> TOTAL 11622 statements, 978 missed, 91.58%
-> 1901 passed

uv run pyright src tests
-> 0 errors, 0 warnings, 0 informations

uv run ruff check .
-> All checks passed!

uv run ruff format --check .
-> 309 files already formatted

uv run python scripts/release_gate_check.py --run
-> exit 0; every gate PASS (publication docs, publication artifact hygiene, source
   package hygiene with sdist and wheel inspected, PyInstaller check-only, root
   artifact hygiene); working tree clean afterwards
```

## Not verified

The following remain outstanding and are tracked as open tasks in `tasks.md`:

1. **Aggregate 40-anchor before/after re-measurement** (all four arc strategies,
   desktop-capped-pool and raw-library conditions, `target_count=12`) against a
   **scratch copy** of the SQLite library — never the live DB. The only measurement
   numbers on record are the frozen spec's pre-change baseline (SPEC-WU25); no
   after-change table exists yet (open task 6.1).
2. **Frozen spec's required-properties checklist** (SPEC-WU25 test items 1–13)
   confirmed item by item in a verify pass (open task 6.2).
3. **Independent review/verification** of this change — none has been performed; this
   report is authored by the implementation-documenting session itself (open task 6.3).
4. **Review-budget disposition** — the change is ~999 lines against the 400-line budget
   in `AGENTS.md`; neither a chained-PR plan nor a recorded accept decision exists yet
   (open task 6.4).
