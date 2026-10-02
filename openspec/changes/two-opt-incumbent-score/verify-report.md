# Verification

## Final integrated verification — 2026-09-30
All automated gates passed at code-complete commit `9e7c894dcbe482ea1b6d6f02c9c9ca05a30c53b0`: **2921 tests**, **93.54% coverage**, clean types/lint/format, smoke, publication/source-package hygiene and PyInstaller check-only. Command: `uv run python scripts/release_gate_check.py --run`. Coverage floor remains 89% in pyproject.toml.

This supersedes earlier isolated-run pending/blocker notes below. Documentation-only closure commits are rerun through the same gate before delivery; final exact-SHA evidence accompanies the delivery. Native macOS, real music/listening, and live Serato import remain unverified. No push, merge, release, or deployment.


- Recovery RED: one operation-count failure; 30 calls versus at most 16 (`two-opt-recovery-red.log`).
- GREEN: 212 focused tests passed in 81.22 s across incumbent scoring, sequence optimization, unchanged performance thresholds, Live Assistant and MainWindow (`algorithm-recovery-green.log`).
- Ruff check and formatting pass for the changed Python files.
- The current integration release gate is pending. Focused success does not establish native macOS or real audio/Serato validation.

Tests run with an isolated writable HOME and Qt offscreen. An initial recovery attempt used the default read-only HOME and failed fixture setup; rerunning with the documented isolated HOME resolves that environment issue.
