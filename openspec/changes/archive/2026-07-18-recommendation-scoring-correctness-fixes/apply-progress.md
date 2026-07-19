# Apply Progress: Recommendation/Scoring Engine Correctness Fixes

## Completed

- [x] F1 — `candidate_pool.py::_camelot_compatible` uses the same circular-distance
      comparison as `camelot.py::_camelot_move`, so `12A`/`1A` pairs (and any pair
      wrapping around 12→1) are correctly treated as adjacent-compatible.
- [x] F2 — `camelot.py::score_camelot_transition` docstring corrected to describe the
      real diagonal branch score (`0.9`), removing the stale, never-returned `0.7`
      "diagonal fuzzy" claim. Code unchanged.
- [x] F3 — `playlist_service.py::recommend_playlist` applies the impossible-BPM-jump
      gate to the manual→generated seam in both sequencing branches:
      - strategy-order branch: single combined gate call seeded with
        `manual_prefix[-1]` when a manual prefix is present (unchanged warning text).
      - optimizer branch: existing pre-sequencing gate at `remaining_tracks` left
        untouched; new second gate call added after `sequenced_tracks =
        sequenced.ordered_tracks`, seeded with `manual_prefix[-1]`, using warning
        text with the `" relative to the manually ordered tracks"` suffix so the two
        stages are text-distinguishable when both fire in the same call.
- [x] F4 — `scoring.py::_bpm_difference_percent` normalizes BPM pairs within
      `HALF_TIME_RATIO_TOLERANCE = 0.02` (2%) of an exact 2:1 ratio by halving the
      upper value before computing the existing percent-difference formula, so
      half-time/double-time pairs (e.g. 128 vs 64) score near-zero difference
      instead of ~100%. Non-2:1 pairs are unaffected (unchanged formula).

## TDD Cycle Evidence

| Task | Test File | Test Name(s) | RED | GREEN | REFACTOR |
|---|---|---|---|---|---|
| F1 Camelot wrap-around | `tests/test_recommendation_presenter.py` | `test_build_pool_treats_camelot_wrap_around_as_compatible` | ✅ Failed pre-fix — `paths.index("/wrap.mp3")` (2) was not `<` `paths.index("/incompatible.mp3")` (1); both fell into the same incompatible key bucket and tie-broke alphabetically | ✅ Passed after circular-distance fix in `_camelot_compatible` | ✅ No further changes needed; `tests/test_recommendation_presenter.py` full suite green (9 passed) |
| F2 Camelot docstring | `tests/test_camelot_scoring.py` (existing, unchanged) | `test_score_camelot_transition_scores_harmonic_moves` (pre-existing, already asserts `0.9` for the diagonal case) | N/A — doc-only fix, no code path changed | N/A | N/A — verified existing suite (5 passed) still green after the docstring edit |
| F3 Manual→generated BPM seam, strategy-order branch | `tests/test_playlist_service.py` | `test_warmup_drops_generated_track_after_impossible_bpm_jump_from_manual_prefix` | ✅ Failed pre-fix — `ordered_tracks` kept the un-gated 140 BPM track (`["/manual.flac", "/too-fast.flac"]`) instead of dropping it | ✅ Passed after seeding the combined gate call with `manual_prefix[-1]` | ✅ No further changes needed |
| F3 Manual→generated BPM seam, optimizer branch | `tests/test_playlist_service.py` | `test_harmonic_journey_drops_generated_track_after_bpm_jump_from_manual_seam` | ✅ Failed pre-fix — `ordered_tracks` retained `/too-fast.flac` and no suffixed warning was present | ✅ Passed after adding the new post-sequencing gate call | ✅ No further changes needed |
| F3 Manual→generated BPM seam, dual-drop distinguishability | `tests/test_playlist_service.py` | `test_harmonic_journey_pre_and_post_sequencing_bpm_gates_drop_different_tracks` | ✅ Failed pre-fix — only the pre-sequencing (unsuffixed) warning was present; the post-sequencing suffixed warning was missing | ✅ Passed after the new post-sequencing gate call; both warnings present, string-distinct (unsuffixed vs. `" relative to the manually ordered tracks"` suffix), each dropping a different track | ✅ No further changes needed |
| F4 Half-time/double-time BPM | `tests/test_transition_scoring.py` | `test_bpm_difference_percent_treats_exact_double_time_pairs_as_compatible`, `test_bpm_difference_percent_non_half_time_pair_is_unaffected`, `test_bpm_difference_percent_tolerance_boundary_inside_band_is_near_zero`, `test_bpm_difference_percent_tolerance_boundary_outside_band_falls_back_to_plain_formula` | ✅ 2 of 4 failed pre-fix (exact-ratio and inside-boundary cases returned ~100%/~97% instead of near-zero); the non-2:1 and outside-boundary cases passed both before and after by design (they assert unchanged behavior) | ✅ All 4 passed after adding `HALF_TIME_RATIO_TOLERANCE` and ratio normalization | ✅ No further changes needed |

## Deviations from Design

None — implementation matches `design.md` and `PLAN.md` exactly, including both
Codex-review corrections in F3 (post-sequencing gate placed after
`sequenced.ordered_tracks`, and the distinguishable `" relative to the manually
ordered tracks"` warning suffix).

## Verification

- ✅ Full pytest: 1015 passed.
- ✅ Pyright (`src tests`): 0 errors, 0 warnings.
- ✅ Coverage: 90.29% total, above the 70% gate.
- ✅ Ruff check: all checks passed.
- ✅ Ruff format check: all files formatted (one test file auto-reformatted by
  `ruff format` for line width — no logic change).
- ✅ Release gate (`scripts/release_gate_check.py --run`): PASS (tests, type-check,
  coverage, lint, format, release readiness smoke, open-source docs, publication
  hygiene, source package hygiene, PyInstaller check-only all green).

Full command-by-command results are in `verify-report.md`.

## Native review corrections (post-apply, `gentle-ai review`)

After apply/verify above, the native bounded-review lifecycle (`gentle-ai review
start`/`finalize`) ran the full 4R lens set (risk, resilience, readability,
reliability — high risk tier, 23+ changed files). Three lineages were needed:

1. **`review-79e5d8dc8c1146b5`** — reviewed the original F1-F4 implementation.
   Approved (0 BLOCKER/CRITICAL), but surfaced 6 non-blocking findings:
   resilience found the post-sequencing warning could misattribute
   compound-chain drops to the manual seam, and inconsistent diagnostic
   granularity between branches; readability found missing comments explaining
   the branch asymmetry, an undocumented effective tolerance band, and 3x
   duplicated warning-string construction (DRY); reliability found the
   half-time normalization changed `score_transition`'s human-readable
   explanation string with no test coverage.
2. **`review-27ab3f92fd4eeceb`** — re-reviewed after fixing all 6: extracted a
   `_bpm_jump_warning()` helper (closes the DRY finding and both resilience
   findings at once, by describing the warning's *mechanism* — "while
   re-validating the sequence anchored on the manually ordered tracks" — instead
   of claiming causal attribution), added branch-asymmetry comments, corrected
   the tolerance-band comment, and added
   `test_score_transition_explanation_reports_zero_percent_for_half_time_pair`.
   Risk/resilience/readability confirmed clean, but reliability found a **new
   CRITICAL**: `src/xfinaudio/quality/dj_readiness.py` had its own private,
   unfixed duplicate of `_bpm_difference_percent` — the DJ export-readiness
   check still flagged half-time BPM pairs as a ~100% "impossible" jump even
   though the recommendation engine now treats them as compatible, a real
   cross-module inconsistency introduced by the F4 fix. This lineage was
   correctly **escalated** (governance requires stopping, not silently
   reopening) once the finding was captured.
3. **`review-78d1fed3f42157d4`** — final lineage, after fixing the CRITICAL:
   `dj_readiness.py` now imports the shared `_bpm_difference_percent` from
   `scoring.py` instead of maintaining a duplicate (the duplicate was deleted);
   added `test_dj_readiness_treats_half_time_bpm_pair_as_continuous` in
   `tests/test_dj_readiness.py`. All 4 lenses confirmed clean. Reliability
   noted one further WARNING — `src/xfinaudio/desktop/screens/live_assistant_screen.py`
   has a *third*, independent BPM-jump formula with the same missing
   normalization — but classified it `causal_disposition: base-only` (predates
   this diff entirely, untouched by it), so it does not block and is **not
   fixed here** — flagged as a follow-up for a future change.
   **Approved**, receipt at
   `.git/gentle-ai/review-transactions/v2/review-78d1fed3f42157d4/review-receipt.json`.

Final full-suite verification after all corrections: 1017 passed, pyright 0
errors, ruff check/format clean. See `verify-report.md` for the final
command-by-command table.
