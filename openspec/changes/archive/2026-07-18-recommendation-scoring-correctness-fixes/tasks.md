# Tasks: Recommendation/Scoring Engine Correctness Fixes

1. [x] **Proposal** — document intent, scope, success criteria.
2. [x] **Specification** — GIVEN/WHEN/THEN for R1-R4.
3. [x] **Design** — alternatives considered for F1/F3/F4 and the OpenSpec-governance meta-decision.
4. [x] **TDD: Camelot wrap-around (F1 / R1)** — RED (failing test for `12A`/`1A` compatibility) → GREEN (circular-distance fix in `_camelot_compatible`) → REFACTOR.
5. [x] **TDD: Camelot docstring (F2 / R2)** — doc-only, no test required; existing `test_camelot_scoring.py` already asserts the real (0.9) behavior.
6. [x] **TDD: Manual→generated BPM seam, strategy-order branch (F3 / R3)** — RED (failing `manual_order_paths` + `warmup` test) → GREEN (seed gate with `manual_prefix[-1]`) → REFACTOR.
7. [x] **TDD: Manual→generated BPM seam, optimizer branch (F3 / R3)** — RED (failing `manual_order_paths` + `harmonic_journey` test, plus a dual-drop test asserting the pre-sequencing and post-sequencing warnings are text-distinguishable when both fire) → GREEN (new post-sequencing gate call with distinguishable warning wording) → REFACTOR.
8. [x] **TDD: Half-time/double-time BPM (F4 / R4)** — RED (failing `_bpm_difference_percent(128, 64)` ≈ 0 test in both argument directions; a non-2:1 pair unaffected test; and tolerance-boundary tests just inside `[1.96, 2.04]` and just outside it, both directions) → GREEN (ratio-normalization fix) → REFACTOR.
9. [x] **Verify** — run focused and full verification commands (`uv run pytest -q`, `uv run pyright src tests`, `uv run pytest --cov --cov-fail-under=70 -q`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run python scripts/release_gate_check.py --run`).
10. [x] **Native review** — `gentle-ai review start`/`finalize` (4R lenses, high risk). 3 lineages: found+fixed 6 non-blocking findings (round 1), found+fixed 1 CRITICAL cross-module inconsistency in `quality/dj_readiness.py` (round 2, escalated then re-reviewed), final round approved with receipt `review-78d1fed3f42157d4`. See `apply-progress.md`.
11. [x] **Archive** — merge delta spec into `openspec/specs/`, move this change folder to `openspec/changes/archive/`.
