# Verification — 2026-09-30

## Final integrated verification — 2026-09-30
All automated gates passed at code-complete commit `9e7c894dcbe482ea1b6d6f02c9c9ca05a30c53b0`: **2921 tests**, **93.54% coverage**, clean types/lint/format, smoke, publication/source-package hygiene and PyInstaller check-only. Command: `uv run python scripts/release_gate_check.py --run`. Coverage floor remains 89% in pyproject.toml.

This supersedes earlier isolated-run pending/blocker notes below. Documentation-only closure commits are rerun through the same gate before delivery; final exact-SHA evidence accompanies the delivery. Native macOS, real music/listening, and live Serato import remain unverified. No push, merge, release, or deployment.


## Requirement evidence
- R1: Public 60/90/120 harmonic_journey repro now returns 60→120 and drops only
  90. The exhaustive all-pairs BFS agrees for 1,008 deterministic randomized
  corpora across seven ceilings. Boundary cases include both directions and
  adjacent floating-point values around the direct/folded windows.
- R2: The oracle covers protected paths, unknown/zero BPM, absent/unknown anchors,
  largest-component ties, input-order preservation, and exact drop counts.
  An explicit test ensures protected controls survive without becoming bridges.
- R3: Dense 2,001-track regression retains 2,000 reachable tracks using 1,999
  comparator calls, below its linear comparison-budget assertion.
- Additional external probe: 20,000 varied-scale corpora agree with all-pairs BFS,
  including thresholds -1 through 1000, duplicate BPMs, and boundary ULPs.

## TDD and checks
- RED, before production edits: 85 failed / 7 passed in the new focused file.
- GREEN: 92 new cases pass; 322 combined reachability/playlist-service tests pass.
- Full src/tests pyright: zero errors/warnings. Ruff lint and format check pass.
- Remaining aggregate stages, run independently after the early stop: release
  readiness smoke, 24 publication-doc tests, five artifact-hygiene tests, source
  package hygiene, and PyInstaller check-only all pass.
- Required aggregate release gate attempted: tests/coverage reached 2,629 passed,
  6 failed, 93.20% coverage (configured floor 89%). The aggregate stopped there.
- Unrelated failures on base 34550a4: four desktop_app FakeQApplication stubs lack
  setWindowIcon after the asset-resolution fix; one extracted-boundaries test
  expects a state object instead of the new accessor; the narrow Color-column
  offscreen layout test still fails. Integration owners were notified; these
  files are outside this slice and unchanged here. Full integration gate remains
  required after the corresponding slices land. No green aggregate is claimed.

Evidence logs live in the external audit directory as reachability-red.log,
reachability-green.log, reachability-focused.log, reachability-fuzz.log,
reachability-release-gate.log/json, reachability-pyright.log, and
reachability-remaining-gates.log. No audio/DSP,
Serato writes, dependencies, root build/dist, publication, or deployment changes.
