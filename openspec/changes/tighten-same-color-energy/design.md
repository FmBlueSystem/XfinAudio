# Design: Tighten Same Color & Energy

## Technical Approach

Add one strategy-specific atomic eligibility path in `playlist_service.py`. It binds one anchor from the same pre-anchor pool currently seen by `same_color`, protects that identity through dedupe/capping, and supplies it to final defensive enforcement. Generated candidates require exact energy and the applicable spectral rule; controls remain explicit exceptions. Empty strict results never widen. `same_color`, `same_energy`, and Camelot behavior remain unchanged.

## Architecture Decisions

| Decision | Alternative | Rationale |
|---|---|---|
| Keep thresholds and `_same_color_energy_eligible()` private to `playlist_service.py` | Add an audio-domain helper | These bounds are single-strategy recommendation policy, not profile analysis. |
| Bind and transport one immutable `anchor_path` | Re-resolve after dedupe/cap | A duplicate sibling or new first profile would change anchor-relative eligibility. |
| Preserve exported list planning; add a dedicated internal context seam | Change `plan_recommendation_candidates()` return type | Existing callers and every other strategy retain their contract. |
| Compute shortages only in `recommend_playlist()` | Warn during prefilter | Only recommendation knows requested count/duration and present controls. |

Anchor resolution occurs only after the input passes, in order, completeness filtering, `_apply_strategy_filters()` (shared energy/BPM range controls), and `_apply_requested_genre()`. This is the exact pool from which current `same_color` next calls `_resolve_anchor_color()`. The strict resolver then uses unchanged precedence: `start_path`; first manual-prefix record carrying the majority manual color; first profiled record. Locked paths never select the anchor; they are preserved exceptions.

## Data Flow

```text
full library -> complete -> shared strategy/range -> requested genre
  -> bind anchor_path -> atomic strict filter -> dedupe/protect anchor
  -> cap/retain anchor -> {records, anchor_path}
  -> desktop worker -> workflow -> recommend_playlist(bound anchor)
  -> defensive strict recheck -> existing BPM/Camelot sequencing
```

`src/xfinaudio/application/recommendation_candidates.py` adds frozen internal `RecommendationCandidateContext(records, same_color_energy_anchor_path)` and `_plan_same_color_energy_candidate_context(...)`. The exported `plan_recommendation_candidates(...) -> list[TrackRecord]` remains unchanged and continues serving all existing callers/strategies; its `same_color_energy` branch may delegate internally and return `.records`.

Only the desktop combined-strategy path uses the context seam. Because `RecommendationService.recommend()` (`src/xfinaudio/desktop/recommendation_service.py:148-167`) calls only `self._desktop_recommendation_records(controls, strategy_name)` at line 164 and has no context callback today, the seam must be added as an injected callback following the existing wiring discipline:

1. **New callback parameter.** `RecommendationService.set_actions()` (`recommendation_service.py:102-125`) gains one new keyword-only parameter, `desktop_same_color_energy_candidate_context: Callable[..., RecommendationCandidateContext]`, appended to the existing ten keyword callbacks.
2. **Stored, `_unwired`-initialized.** `RecommendationService.__init__` (`recommendation_service.py:46-67`) initializes `self._desktop_same_color_energy_candidate_context: Callable[..., RecommendationCandidateContext] = _unwired`, matching the module-level `_unwired` sentinel discipline used by every other injected callback. `set_actions()` assigns it alongside the others.
3. **Injected from wiring.** `wire_main_recommendation_service()` in `src/xfinaudio/desktop/window_service_wiring.py:91-102` passes `desktop_same_color_energy_candidate_context=self._desktop_same_color_energy_candidate_context`; `MainWindow` (`src/xfinaudio/desktop/main_window.py`) adds that method next to `_desktop_recommendation_records()` (`main_window.py:473-484`), delegating to the internal context planner.
4. **Dispatch guard.** `RecommendationService.recommend()` invokes the new callback ONLY when `strategy_name == "same_color_energy"`; every other strategy continues through `self._desktop_recommendation_records(controls, strategy_name)` unchanged. When invoked, the service forwards `context.records` plus the optional bound path through `_start_recommendation_worker()` and `PlaylistWorkflowService.recommend()` to `recommend_playlist()`.

Direct recommendation callers without a path bind once after their own identical pre-anchor stages. A supplied missing/invalid path fails closed and is never replaced. Candidate dedupe/cap accept the bound path as protected without converting it to `start_path` or changing playlist-order semantics.

For each non-control candidate:

```text
candidate.energy_level == anchor.energy_level
AND candidate.dominant_color == anchor.dominant_color
AND (anchor.dominant_color != MIXED OR mixed_profile_close(anchor, candidate))
```

RED/GREEN/BLUE use label equality plus exact energy only; zero centroid/rolloff remains eligible. MIXED alone uses named, calibration-provisional constants: `MIXED_RGB_L1_MAX` (initial value `0.08`), `MIXED_CENTROID_REL_MAX` (initial `0.15`), and `MIXED_ROLLOFF_REL_MAX` (initial `0.15`). The rule SHAPE — label equality plus a bounded anchor-relative RGB L1 / centroid / rolloff proximity gate — is normative; the literal numeric values are PROVISIONAL pending listening calibration and MUST be expressed as named constants so a post-calibration change touches only the constant definitions, not the rule. MIXED profiles require finite ratios with positive sums and finite positive centroid/rolloff. Relative delta is `abs(candidate-anchor)/anchor`; zero/invalid denominators fail closed.

**Why the bounded gate is required at all (not provisional).** Over the simplex `r+g+b=1`, the MIXED region — the ELSE of three independent threshold tests in `_dominant_color()` (`src/xfinaudio/audio/spectral_profile.py:177-194`: RED >= 0.45, GREEN >= 0.48, BLUE >= 0.22) — has an L1 diameter of 0.30 and occupies only 2.21% of the simplex area, yet holds 44% of the real library's E8 tracks (305 of 691, per `exploration.md:16`). MIXED is therefore not a spectral region; it means "no threshold was crossed". Label equality on MIXED constrains nothing, so a bounded proximity gate is structurally required. The provisional `0.08` L1 bound is ~3.75x tighter than the bucket's own 0.30 diameter, which is why calibration adjusts the magnitude but never the need for a gate.

## File Changes

| File | Action | Description |
|---|---|---|
| `src/xfinaudio/recommendation/strategies.py` | Modify | Exact-energy contract and description. |
| `src/xfinaudio/recommendation/playlist_service.py` | Modify | Pre-anchor stages, bound resolver, atomic filter, warnings. |
| `src/xfinaudio/application/recommendation_candidates.py` | Modify | Internal context planner while preserving exported list API. |
| `src/xfinaudio/recommendation/candidate_pool.py` | Modify | Protect bound anchor during dedupe/cap. |
| `src/xfinaudio/desktop/recommendation_service.py` | Modify | Add `_unwired`-initialized combined-context callback, new `set_actions()` param, and `strategy_name == "same_color_energy"` dispatch guard in `recommend()`. |
| `src/xfinaudio/desktop/window_service_wiring.py` | Modify | Inject `desktop_same_color_energy_candidate_context` in `wire_main_recommendation_service()` (lines 91-102). |
| `src/xfinaudio/desktop/main_window.py`, `src/xfinaudio/application/playlist_workflow.py` | Modify | Add `_desktop_same_color_energy_candidate_context()`; transport bound path to `recommend_playlist()`. |
| `tests/test_playlist_strategies.py`, `tests/test_playlist_service.py`, `tests/test_application_recommendation_candidates.py`, `tests/test_recommendation_service_state.py` | Modify | Strict TDD and transport compatibility coverage. |

## Interfaces / Contracts

Prefilter/context planning stays warningless. `recommend_playlist(..., same_color_energy_anchor_path=None)` owns warnings. Requested total is `target_count`, or duration converted with `played_seconds_per_track`/existing mean-duration fallback. It counts preserved paths actually present and computes `requested_generated = max(0, requested_total - present_controls)`. Fewer eligible non-controls emits shortage; no request size emits none. Missing prerequisites or zero eligible generated candidates always warn and never fall back.

## Testing Strategy

**Characterization first (safety net before any change).** `_apply_energy_tolerance()` (`src/xfinaudio/recommendation/playlist_service.py:766-787`) currently has NO covering tests despite two callers; this is a characterization gap that MUST be closed before touching behavior. Add characterization tests pinning the CURRENT behavior of `same_color` and `same_energy` — including the anchor `+/-1` energy band produced by `_apply_energy_tolerance()` and the unfiltered fallback of the SHARED `_apply_color_filter()` (`playlist_service.py:689-704`, which returns the unfiltered `tracks` list with its warning on an empty eligible pool). These characterization tests are the only proof the untouched strategies stay intact, so they are RED-before-change prerequisites, not afterthoughts.

**Compatibility constraint (FINDING F).** `_apply_color_filter()` is shared by `same_color` and `same_color_energy`. The fix MUST NOT alter that helper's empty-pool fallback behavior or its warning text for `same_color`. A characterization test MUST pin `same_color`'s exact fallback path and warning string; the `same_color_energy` fail-closed path is implemented WITHOUT changing the shared helper's `same_color` branch.

**Strict TDD.** RED tests cover exact/just-over MIXED bounds (using the provisional named constants), MIXED zero/missing failure, RGB label-only behavior, controls, Camelot independence, and unchanged existing strategies. Add a requested-genre fixture proving anchor binding happens after genre filtering. Add a no-control first-profile anchor with a duplicate that dedupe would otherwise replace; assert the bound path survives cap/final enforcement. Assert public `plan_recommendation_candidates()` still returns a list for combined and ordinary strategies, while the desktop combined path alone transports context.

**Wiring/dispatch regression (`tests/test_recommendation_service_state.py`).** A regression MUST prove that `RecommendationService.recommend()` invokes the new `_desktop_same_color_energy_candidate_context` callback ONLY when `strategy_name == "same_color_energy"`, and continues through `_desktop_recommendation_records()` for every other strategy — proving combined-only invocation AND ordinary-path compatibility. Test count/duration shortages with absent controls excluded.

Calibrate using a scratch copy of `~/.xfinaudio/xfinaudio.sqlite3`; run `MainWindow.with_defaults(...)` offscreen for multiple anchors, inspect candidates/warnings, capture Review Mix evidence, and listen around boundaries.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable classification, or process boundary.

## Migration / Rollout

No schema migration, analysis, or DSP. Keep implementation within 400 changed lines.

## Open Questions

The combined-strategy service-wiring gap identified in prior revisions is now RESOLVED in this design: the typed `desktop_same_color_energy_candidate_context` callback is specified as `_unwired`-initialized on `RecommendationService`, added to `set_actions()`, injected from `window_service_wiring.py`, dispatch-guarded to `strategy_name == "same_color_energy"`, and covered by a wiring/dispatch regression in `tests/test_recommendation_service_state.py`. No unresolved architecture blocker remains.

Remaining non-blocking item, enumerated (not implied): the provisional MIXED numeric constants (`MIXED_RGB_L1_MAX`, `MIXED_CENTROID_REL_MAX`, `MIXED_ROLLOFF_REL_MAX`) require listening calibration across multiple real-library anchors AFTER implementation exists. This is an acceptance gate, not a design blocker; the rule shape is normative and the constants are isolated so calibration touches only their definitions.
