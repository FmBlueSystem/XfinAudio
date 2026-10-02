# Apply progress

2026-09-30: Proposal, specification, design, and tasks complete. Isolated branch
starts at 34550a4. Production unchanged. Preparing RED regression coverage.

RED captured before production edits: `uv run --no-sync pytest -q
 tests/test_bpm_reachability.py` yielded 85 failed, 7 passed (1.66s).
Log: external audit evidence `reachability-red.log`. Failures include the public
60/90/120 repro, independent exhaustive-component properties, folded-window
boundaries, and dense folded components. Existing passthrough coverage passed.

GREEN: 92 new cases pass (1.76s). Focused existing/new coverage: 322 passed
(4.31s). Only _bpm_reachable_from changed in production. Rounding-padded BPM
windows are validated by the shared comparator; successor compression and
skipping equal rejected BPMs avoid repeated dense scans. Ruff lint/format pass.
REFACTOR reviewed passthrough, tie-breaking, input order, and zero/100% ceilings.

VERIFY: Full gate attempted: 2,629 passed, six unrelated desktop/test failures,
93.20% coverage; exact failures recorded in verify-report.md and sent to the
integration owner. Independent full type/lint/format checks pass. An additional
20,000-corpus all-pairs BFS probe passes. Dense pool uses 1,999 comparisons for
2,001 candidates. No out-of-scope fixes; final green aggregate belongs to the
integrated branch after its baseline fixes arrive.
