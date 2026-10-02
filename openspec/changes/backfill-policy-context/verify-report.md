# Verification

## Final integrated verification — 2026-09-30
All automated gates passed at code-complete commit `9e7c894dcbe482ea1b6d6f02c9c9ca05a30c53b0`: **2921 tests**, **93.54% coverage**, clean types/lint/format, smoke, publication/source-package hygiene and PyInstaller check-only. Command: `uv run python scripts/release_gate_check.py --run`. Coverage floor remains 89% in pyproject.toml.

This supersedes earlier isolated-run pending/blocker notes below. Documentation-only closure commits are rerun through the same gate before delivery; final exact-SHA evidence accompanies the delivery. Native macOS, real music/listening, and live Serato import remain unverified. No push, merge, release, or deployment.

- Context RED: 3 missing-policy failures; initial helper RED: 17 failures/2 passes;
  expanded direct/desktop RED: 21 failures/12 passes; tie-order RED: 1 failure.
- GREEN: 393 tests across replacement policy/context/controls, playlist service,
  DJ controls, app-state transitions, editor, JSON/file exporters, saved playlists,
  workflow/candidate planning, service/presenter/coordinator and synthetic
  scan-recommend-export. Additional export-screen/coordinator editing: 7 passed.
- `pyright --pythonpath /workspace/shared/xfinaudio/.venv/bin/python src tests`:
  0 errors, 0 warnings. `ruff check .`, `ruff format --check .` (376 files), and
  `git diff --check` passed. Existing environment reused without dependencies.
- Matrix reproduction: E5 a/b/c + E10 outside replacing b => a/c, energies 5/5.
- Covered: energy/BPM hard ranges, active explicit/inferred genre, original genre
  fallback, custom loudness/unknown-measurement exception, bounded color/exact
  energy, anchor removal/reordering/JSON round-trip, current lock exceptions and
  exclusions, missing anchor behavior, legacy context and equal-score ordering.
- Compatibility limit: legacy objects without a policy snapshot cannot recover
  original anchors or loudness band. Context-dependent generated backfill fails
  closed with a warning; removal and valid control exceptions remain available.
- Full aggregate gate intentionally not run here. Integration owner runs it on
  the combined commit; focused success does not establish release readiness.

## Integrated current-setting compatibility
An explicit loudness override is tested with real measured profiles rather than a mocked private prefilter. The desktop honors its current target; direct API defaults preserve the saved target. Legacy objects accept an explicit band only where it resolves the missing loudness context, while other missing anchors remain closed. Three initial RED failures plus the non-default legacy-band RED were followed by 305 passing focused tests.
