## Exploration: Tighten Same Color & Energy

### Current State

`same_color_energy` currently composes two independent filters:

- `_apply_color_filter` accepts every non-control track whose `dominant_color` label equals the resolved anchor label.
- `energy_tolerance=1` accepts the anchor energy and both adjacent levels.

This makes the strategy name stronger than its behavior. Playlist 43 demonstrates both gaps: its E8 anchor produced nine E8 and seven E7 tracks, while all 16 profiles passed because `MIXED == MIXED`. `MIXED` is a fallback label for any RGB ratio vector that crosses none of the RED/GREEN/BLUE thresholds, not a cohesive spectral region. The stored vectors in that playlist span RGB L1 distances up to approximately 0.185 from the anchor even though their cosine scores remain very high; normalized positive three-band vectors make cosine similarity insufficiently discriminating in this dense region.

The profile already stores the data needed for a tighter read-only comparison: red/green/blue ratios, spectral centroid, spectral rolloff, and RMS. No new audio analysis, schema migration, or DSP is required.

Camelot key is already a separate harmonic dimension. The playlist's keys form valid scored moves even though only three tracks are 12A: for example, 12A to 11B is a supported diagonal move, and every adjacent transition in playlist 43 has a non-zero Camelot score. Exact anchor-key matching would therefore confuse harmonic compatibility with spectral color and would unnecessarily reduce viable sequences.

Real-library read-only measurements show the stricter strategy is feasible. The current library contains 691 complete E8 tracks with profiles, including 305 `MIXED` profiles. For the playlist-43 anchor, an RGB L1 distance of at most 0.08 leaves 114 exact-E8 `MIXED` tracks; additionally requiring centroid and rolloff to remain within 15% of the anchor leaves 91 tracks before duplicate removal and sequencing. That is ample raw material for the usual 15-track slot, although the real end-to-end pool must still be verified after BPM, Camelot, duplicate, and target-duration constraints.

### Affected Areas

- `src/xfinaudio/recommendation/strategies.py` — `same_color_energy` currently declares `energy_tolerance=1` and promises a +/-1 band.
- `src/xfinaudio/recommendation/playlist_service.py` — color and energy are filtered separately; `MIXED` is matched by label only, and the color filter widens back to the unfiltered pool when empty.
- `src/xfinaudio/audio/spectral_profile.py` — owns the existing continuous profile values and cosine similarity helper; a bounded color-distance helper belongs here if shared, but the analyzer and persisted model need not change.
- `src/xfinaudio/recommendation/candidate_pool.py` — Camelot, BPM, vibe, and energy rank the capped pool after strategy prefiltering; spectral eligibility must therefore be applied before this cap.
- `tests/test_playlist_service.py` — existing combined-strategy tests encode +/-1 membership and unfiltered fallback, so they must change under strict TDD while preserving `same_color` and `same_energy` characterization tests.
- `tests/test_playlist_strategies.py` and `tests/audio/test_spectral_profile.py` — strategy semantics and any new pure distance rule require focused coverage.
- `openspec/specs/same-color-energy-strategy/spec.md` — the durable spec currently mandates +/-1 and fallback-to-unfiltered behavior and must receive an explicit delta.

### Approaches

1. **Change only the energy tolerance** — set `same_color_energy.energy_tolerance` to zero and retain dominant-label color matching.
   - Pros: Smallest code change; playlist 43 becomes exact E8; existing filter structure remains intact.
   - Cons: Does not fix the central `MIXED` bucket defect; spectrally distant tracks still satisfy the advertised color guarantee.
   - Effort: Low

2. **Use a single continuous similarity threshold for every color** — replace dominant-label filtering with a threshold over the current cosine score.
   - Pros: Uniform rule and minimal branching.
   - Cons: Current cosine similarity is poorly separated for real `MIXED` profiles (the playlist-43 tracks score about 0.976-1.000); selecting a meaningful global threshold would be brittle and could unexpectedly change RED/GREEN/BLUE behavior.
   - Effort: Medium

3. **Tighten only `same_color_energy`, with exact energy and an anchor-relative `MIXED` gate** — keep exact dominant-label matching for RED/GREEN/BLUE, but require `MIXED` candidates to be close to the anchor's stored continuous profile.
   - Pros: Directly fixes both observed causes; leaves `same_color` and `same_energy` byte-compatible; uses existing cached data; keeps the change understandable and bounded.
   - Cons: Initial thresholds require explicit calibration and real-library verification; a strict result can be shorter than the requested slot.
   - Effort: Medium

### Recommendation

Use approach 3 and give `same_color_energy` strict, strategy-specific semantics:

1. **Energy membership is exact.** A non-control candidate MUST have the same integer `energy_level` as the resolved anchor (`energy_tolerance=0` or an equivalent exact predicate). Keep `same_energy` at +/-1 for backward compatibility. The optimizer's adjacent-energy ceiling remains a sequencing safety rule, not a candidate-membership definition.
2. **Color membership remains spectral, not tonal.** RED/GREEN/BLUE candidates continue to require the same dominant label. When the anchor is `MIXED`, label equality is necessary but not sufficient: compare each candidate directly with the anchor profile and initially require RGB L1 distance `<= 0.08`, relative centroid difference `<= 15%`, and relative rolloff difference `<= 15%`. These bounds retain 91 exact-E8 candidates for the reported anchor in the real library. Do not hard-filter on RMS in this slice because it is sensitive to mastering gain and exact Mixed In Key energy already constrains perceived intensity; RMS may remain a ranking signal or future calibration input.
3. **Apply the combined filter atomically before pool capping.** A dedicated combined-strategy predicate/helper is safer than widening the shared `_apply_color_filter`, because it can evaluate final eligibility after both constraints and cannot accidentally change `same_color`.
4. **Do not silently widen an empty pool.** For `same_color_energy`, return only preserved DJ control tracks (or an empty recommendation when there are none) and emit an explicit warning that no tracks satisfy exact energy plus spectral proximity. Also warn when the strict pool cannot fill the requested slot. Falling back to unfiltered scoring contradicts the strategy guarantee and recreates the reported surprise. Keep the existing fallback behavior and warning text for `same_color` unchanged.
5. **Keep Camelot independent.** Retain harmonic scoring, candidate ranking, and the existing non-zero Camelot transition gate. Do not require the anchor's exact Camelot key and do not fold key into spectral color.
6. **Fail closed when the required anchor data is unavailable.** The combined strategy should not infer a different track's profile as the anchor or claim strict matching without anchor energy/profile data. Preserve explicit control tracks and explain the missing prerequisite.

Thresholds should be constants with rationale and pure boundary tests. Before accepting them as product defaults, run the real-library offscreen recommendation flow against a database copy and inspect both pool size and listening-quality examples at the boundary. This is calibration of existing metadata, not new DSP.

### Risks

- The proposed numeric thresholds are evidence-based for the reported anchor but still need listening validation across RED/GREEN/BLUE and multiple `MIXED` anchors; one anchor is not a universal calibration set.
- Exact energy plus strict spectral proximity can produce short playlists for sparse libraries. Honest shortage is preferable to silently violating the selected strategy, but the UI warning must make that tradeoff clear.
- Existing tests and the durable spec explicitly require +/-1 and unfiltered fallback for `same_color_energy`; those are intentional compatibility breaks for this strategy and must be changed explicitly, not accidentally.
- Control tracks remain user-owned exceptions and may violate the strict color/energy rule. Warnings and specs must continue to distinguish control tracks from generated candidates.
- Legacy or missing spectral profiles cannot satisfy the stricter guarantee and should not be treated as neutral matches.

### Ready for Proposal

Yes. The proposal should define exact-energy membership, the anchor-relative `MIXED` proximity gate, strict empty-pool behavior, unchanged `same_color`/`same_energy` behavior, separate Camelot semantics, and a real-library calibration/verification criterion.
