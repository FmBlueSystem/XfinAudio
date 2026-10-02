# Verification

## Final integrated verification — 2026-09-30
All automated gates passed at code-complete commit `9e7c894dcbe482ea1b6d6f02c9c9ca05a30c53b0`: **2921 tests**, **93.54% coverage**, clean types/lint/format, smoke, publication/source-package hygiene and PyInstaller check-only. Command: `uv run python scripts/release_gate_check.py --run`. Coverage floor remains 89% in pyproject.toml.

This supersedes earlier isolated-run pending/blocker notes below. Documentation-only closure commits are rerun through the same gate before delivery; final exact-SHA evidence accompanies the delivery. Native macOS, real music/listening, and live Serato import remain unverified. No push, merge, release, or deployment.


## RED → GREEN evidence

- Before implementation, the four snapshot contract tests failed: direct field mutation and unknown update keys were accepted, and shell selection/runtime refresh mutated already-published snapshots.
- After recovery, the same four tests pass within the 190-test state/scan/view-model subset.
- The final focused subset adds three accessor/type-contract tests, totaling 193 tests.

## Requirement coverage

- Frozen fields and checked names: `test_state_snapshot_contract.py` rejects direct assignment and misspelled update keys.
- Published replacements: shell folder selection, scan start/progress and runtime selection refresh preserve previous snapshots and synchronize current state across the shell, app/library controllers and scan/recommendation services.
- Read-only compatibility access: `test_main_window_shell_compat.py` verifies that reading the current scan token leaves the published snapshot unchanged.
- Typed boundaries: `test_state_access.py` runs Pyright against a valid accessor and five deliberately invalid uses; it requires diagnostics on exactly the invalid getter, publisher, replacement value, frozen assignment and screen-name lines.
- Current-state derivation: accessor updates start from the latest owner snapshot, publish exactly once, and never publish after an unknown-field error.

## Checks

Environment: Linux, Python 3.12, Qt offscreen; existing shared dependency environment. A temporary writable HOME/cache isolates repository fixtures from the read-only system home. Pyright uses the same Python interpreter explicitly.

- Focused tests: **193 passed** (5.62 seconds).
- Full-source/test Pyright: **0 errors, 0 warnings**.
- `ruff check .`: passed.
- `ruff format --check .`: passed (358 files).
- `git diff --check`: passed.
- Aggregate release gate: pending integration. The first attempt encountered read-only HOME errors in unrelated window setup; the corrected isolated run was stopped to avoid duplicating the integration owner's combined-tree gate. Neither attempt is reported as a full pass.

## Limits

Field immutability is shallow: unchanged list/dict payloads remain structurally shared, and update value types are not validated at runtime. Unknown field names are rejected at runtime; current/replacement callbacks are checked statically. Existing broad shell compatibility and other controller interfaces remain for later incremental migration. This slice changes no audio, DSP, export, or live Serato database behavior. Real macOS/manual audio QA is outside this Linux verification.
