# Plan: Fix correctness bugs in the recommendation/scoring engine
_Locked via grill — by Claude + Freddy_

## Goal
Fix four correctness issues found in `src/xfinaudio/recommendation/` (camelot key matching, candidate pooling, manual/generated track sequencing, and BPM compatibility scoring), each verified against the actual code and its test coverage before being locked into this plan. Two are confirmed logic bugs, two are design gaps the user explicitly resolved during the grill.

## Approach

1. **`candidate_pool.py:19-32` (`_camelot_compatible`) — fix Camelot wheel wrap-around.**
   Currently `abs(track_num - anchor_num) <= 1` does not treat 12 and 1 as adjacent, so pairs like `12A`/`1A` are wrongly scored incompatible even though `camelot.py::_camelot_move` (lines 132-135) already solves this correctly with `min(direct_delta, 12 - direct_delta)`. Replace the raw `abs(...)` comparison with the same circular-distance calculation, so both modules agree.
   - Test: add a case to `tests/test_recommendation_presenter.py` (imports `build_recommendation_pool`) asserting a track keyed `12A` is treated as compatible with an anchor keyed `1A` (and vice versa).

2. **`camelot.py:100-103` (`score_camelot_transition` docstring) — fix stale docstring.**
   The docstring promises a `0.7` "diagonal fuzzy" score that the function never returns; `tests/test_camelot_scoring.py:18-19` confirms the actual (and correct) diagonal value is `0.9`. Update the docstring text to describe the real branches (no code change): `"exact key 1.0, adjacent same-letter 0.9, relative A/B 0.85, diagonal (adjacent number, different letter) 0.9, configured boost 0.8, and incompatible 0.0."`
   - No test needed — this is a doc-only correction; existing tests already assert the real (0.9) behavior.

3. **`playlist_service.py` — apply the impossible-BPM-jump gate to the manual→generated seam.**
   Decision (locked with user): tracks placed via `manual_order_paths` should NOT be exempt from the adjacent-BPM-jump gate — the seam between the last manual track and the first generated track must be checked exactly like any generated→generated seam.

   **Correction from Codex Round 1**: the original draft of this step seeded the gate at `playlist_service.py:114`, which runs on `remaining_tracks` — the *unordered candidate pool*, **before** `recommend_sequence` (line 121) decides the actual final adjacency. Seeding there does not validate the true manual→generated seam in the optimizer branch; it validates an arbitrary pre-optimization order and its result gets reshuffled by the optimizer anyway. Corrected below: the two branches need different treatment because they reach "final order" at different points.

   - **Strategy-order branch** (`_uses_strategy_order` is true, ~line 103-112) — `sequenced_tracks` after `_apply_terminal_constraints` IS already the final order (no separate optimizer stage follows), so seeding at the existing single call site is correct as originally planned:
     ```python
     sequenced_tracks = _apply_terminal_constraints(remaining_tracks, start_path, applied.end_path)
     if manual_prefix:
         sequenced_tracks, dropped_bpm_jump_count = _drop_generated_tracks_after_impossible_bpm_jumps(
             [manual_prefix[-1], *sequenced_tracks]
         )
         sequenced_tracks = sequenced_tracks[1:]
     else:
         sequenced_tracks, dropped_bpm_jump_count = _drop_generated_tracks_after_impossible_bpm_jumps(sequenced_tracks)
     if dropped_bpm_jump_count:
         warnings.append(...)  # existing message text, unchanged
     ```
   - **Optimizer branch** (~line 113-130) — leave the existing pre-sequencing gate at line 114 untouched (it filters `remaining_tracks` before the optimizer runs; that's pre-existing, out-of-scope behavior). Add a **new**, second gate application *after* `sequenced_tracks = sequenced.ordered_tracks` (line 129), which is where the true final adjacency is known:
     ```python
     sequenced_tracks = sequenced.ordered_tracks
     optimizer = sequenced.optimizer
     if manual_prefix:
         seeded, post_sequencing_dropped_count = _drop_generated_tracks_after_impossible_bpm_jumps(
             [manual_prefix[-1], *sequenced_tracks]
         )
         sequenced_tracks = seeded[1:]
         if post_sequencing_dropped_count:
             warnings.append(
                 "Dropped "
                 f"{post_sequencing_dropped_count} generated track(s) because adjacent BPM jump exceeded "
                 f"{MAX_ADJACENT_BPM_DIFFERENCE_PERCENT:.1f}% relative to the manually ordered tracks"
             )
     ```
     **Correction from Codex Round 5**: the pre-sequencing gate (line 114, unchanged) and this new post-sequencing gate can both drop tracks in the same `recommend_playlist` call; before this correction both appended the *identical* generic warning text, making the two drops indistinguishable in `result.warnings` — directly undermining the Round 2 rationale for keeping their counts separate. Fixed by appending `" relative to the manually ordered tracks"` only to the post-sequencing message, so the two stages are honestly distinguishable without reintroducing the earlier "seam-only" framing (this message still describes validation against the manual anchor across the whole chain, not a narrower seam-only claim).
   - Test (new, Codex Round 5): a dual-drop case where the pre-sequencing candidate-pool filter drops one track AND the post-sequencing manual-seam check drops a different track in the same `recommend_playlist` call — assert `result.warnings` contains both messages and they are text-distinguishable.
     **Correction from Codex Round 2**: the original draft of this step labeled every drop from this call "at the manual→generated seam," but `_drop_generated_tracks_after_impossible_bpm_jumps` validates the *entire* seeded chain (manual→gen1, and — if gen1 is kept — gen1→gen2, etc.), matching exactly how the existing `start_path` gate already behaves (see `test_warmup_drops_generated_tracks_after_impossible_bpm_jump_from_selected_start`, which drops 2 tracks in a row from a single anchor, not just 1). Labeling it "seam-only" was factually wrong and would have produced misleading warnings. Fixed by reusing the same generic warning phrasing already used elsewhere in this file instead of inventing seam-specific wording — this call is honestly described as "the same anchor-validation gate applied with the manual track as the anchor," not a narrower seam-only check. Kept as a distinct count from the pre-sequencing `dropped_bpm_jump_count` (not merged) since they check different things at different stages — merging would still misreport which stage actually dropped a track.
   - Tests (both branches, since they're now fixed differently — a single test can't cover both):
     - `tests/test_playlist_service.py`: strategy-order case, mirroring `test_warmup_drops_generated_tracks_after_impossible_bpm_jump_from_selected_start` but using `manual_order_paths=["/manual.flac"]` (BPM 100) with a `warmup`-strategy candidate pool where the best-ranked generated track is at BPM 140 (>3% jump) — assert it's dropped and the warning fires.
     - `tests/test_playlist_service.py`: optimizer-branch case using `harmonic_journey` (matches the existing `test_harmonic_journey_drops_generated_tracks_after_bpm_jump_over_three_percent` pattern) with `manual_order_paths` instead of `start_path`, same BPM-jump setup — assert the generic `"Dropped 1 generated track(s) because adjacent BPM jump exceeded 3.0%"` warning fires (via `post_sequencing_dropped_count`) and the offending track is absent from `result.ordered_tracks`.

4. **`scoring.py:224-228` (`_bpm_difference_percent`) — treat half-time/double-time BPM pairs as compatible.**
   Decision (locked with user): pairs in an exact 2:1 ratio (e.g. 128 vs 64) should be normalized to near-zero difference before scoring, not penalized as a ~100% jump. This is the single shared function used by both `scoring.py::_score_bpm` and `playlist_service.py`'s jump gate, so fixing it here fixes both consistently.
   Fix: detect a ratio within tolerance of 2.0 (small tolerance for measurement noise) and halve the upper value before computing the existing percent-difference formula:
   ```python
   HALF_TIME_RATIO_TOLERANCE = 0.02  # 2% — accounts for BPM detection measurement noise

   def _bpm_difference_percent(left_bpm: float, right_bpm: float) -> float:
       lower = min(left_bpm, right_bpm)
       upper = max(left_bpm, right_bpm)
       if lower <= 0:
           return 100.0
       ratio = upper / lower
       if abs(ratio - 2.0) <= HALF_TIME_RATIO_TOLERANCE * 2.0:
           upper = upper / 2.0
       return abs(upper - lower) / lower * 100
   ```
   - Test: add cases to `tests/test_transition_scoring.py`:
     - `_bpm_difference_percent(128, 64)` and `_bpm_difference_percent(64, 128)` (both argument orderings) are near `0.0`.
     - A non-2:1 pair (e.g. 128 vs 100) is unaffected — still uses the plain formula, well above the tolerance band.
     - **Tolerance boundary (Codex Round 4)**: the band is `abs(ratio - 2.0) <= 0.04` (i.e. ratio ∈ [1.96, 2.04], since `HALF_TIME_RATIO_TOLERANCE * 2.0 = 0.04`). A pair just *inside* it — `128` vs `64.97` (ratio ≈ `1.97`) — is treated as compatible (near `0.0`). A pair just *outside* it — `128` vs `65.64` (ratio ≈ `1.95`) — falls back to the plain formula, producing a large, non-near-zero percent difference (≈95%). Both checked in both argument directions. This guards against an equality-only (`ratio == 2.0`) implementation silently passing the exact-ratio tests while ignoring the tolerance the fix promises.

## Key decisions & tradeoffs

- **#1 fixed as unambiguous bug**: `camelot.py` already has the correct wrap-around logic; `candidate_pool.py` independently reimplemented the comparison and reintroduced the bug. Fixing it aligns the two modules instead of duplicating logic differently in each — no design judgment call needed.
- **#2 is docstring-only**: the code's actual behavior (0.9 for diagonal) is already correct and already tested; changing the code to match the stale docstring's `0.7` would break `test_camelot_scoring.py` and would be the wrong fix. Only the doc comment moves.
- **#3 — manual tracks are NOT exempt from the BPM gate**: user's explicit call, prioritizing consistent sequencing quality over deferring unconditionally to manual placement. Alternative (leave manual tracks exempt) was offered and rejected.
- **#4 — half-time/double-time normalized to compatible, full merge (not partial-credit)**: user's explicit call among three options (full compatibility, partial-credit compatibility, out of scope). Chosen because it's the simplest change that matches real DJ practice, and reuses the single shared `_bpm_difference_percent` function so both scoring and the jump-gate benefit consistently.
- **Two rejected findings not in this plan**: none — all four findings raised in the grill were accepted into scope (with #3/#4 requiring the design decisions above before they could be locked).

## Risks / open questions
- #4's `HALF_TIME_RATIO_TOLERANCE = 0.02` is a judgment-call constant with no existing precedent in the codebase (checked `scoring.py` — no prior BPM-ratio tolerance existed). Codex should sanity-check whether this is too loose/tight given real BPM detection noise in this codebase.
- #3's two branches are now deliberately handled differently (single combined gate call vs. a new second gate call) rather than "identically" — see the Round 1 correction above. Codex should confirm this asymmetry is the right call rather than a sign the fix is still incomplete.

## SDD/OpenSpec process note (raised by Codex Rounds 1-2, resolved)
Codex flagged twice that `AGENTS.md`/`openspec/config.yaml` require "every non-trivial change" (and explicitly "feature/refactor work") to produce durable artifacts under `openspec/`, and that this plan — which changes real recommendation-engine behavior, not just docs — had none. Round 1's rejection ("the user chose a lighter workflow") was reconsidered and reversed after Codex's Round 2 pushback ("workflow selection cannot silently waive repository-level governance") and after confirming `openspec/changes/` is genuinely active for this repo (real commit history references it, e.g. `project-audit-remediation`). Decision, confirmed with the user: OpenSpec artifacts were authored directly under `openspec/changes/recommendation-scoring-correctness-fixes/` (proposal.md, spec.md, design.md, tasks.md, state.yaml), reusing this plan's already-locked content rather than re-deriving it via the full `sdd-propose`/`sdd-spec`/`sdd-design`/`sdd-tasks` subagent pipeline. `PLAN.md`/`PLAN-REVIEW-LOG.md` remain as the grill + adversarial-review audit trail — a superset, not a replacement. RED-first TDD ordering (write each test first, confirm it fails, then implement) remains non-negotiable per this session's Strict TDD Mode and is now also tracked in `tasks.md`.

## Out of scope
- `audio/` (spectral analysis) and `quality/` (DJ readiness scoring) clusters — excluded per scope decision at grill start; only `recommendation/` is in scope.
- Performance/complexity improvements and harmonic-mixing heuristic quality — excluded per grill scope (correctness only).
- Any refactor of `_drop_generated_tracks_after_impossible_bpm_jumps` itself beyond its two call sites — the function's internals are correct; only how it's invoked changes.
