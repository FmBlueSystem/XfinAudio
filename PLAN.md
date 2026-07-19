# Plan: Recalibrate spectral color classification

_Locked via grill — by Claude + Freddy_

## Goal

The current dominant-color rule (any band ratio >= 0.55, else MIXED) fails to discriminate on real data: measured against the user's live library of 10,390 analyzed tracks, 78.5% classify as MIXED and only 9 tracks (0.1%) as BLUE. Replace the classification rule with per-band thresholds so the color badge and spectral-shift warnings become meaningful, without re-analyzing any audio.

## Approach

1. Change `_dominant_color` in `src/xfinaudio/audio/spectral_profile.py` to per-band thresholds:
   - RED dominant when `red_ratio >= 0.45`
   - GREEN dominant when `green_ratio >= 0.45`
   - BLUE dominant when `blue_ratio >= 0.25` (lower bar: high-frequency energy is structurally smaller)
   - If more than one band passes its threshold, pick the band with the largest excess over its own threshold; on an exact excess tie, resolve by fixed priority RED > GREEN > BLUE (documented, deterministic).
   - If none passes, classify MIXED.
2. Expose the classification for reuse by the repository layer (public wrapper in the same module, e.g. `dominant_color_for_ratios(red, green, blue)`).
3. Update `_deserialize_profile` in `src/xfinaudio/library/track_repository.py` to recompute `dominant_color` from the stored ratios instead of trusting the persisted value. Order matters: parse the JSON into a dict first, overwrite/insert `dominant_color` with the recomputed value, then validate the reconstructed `SpectralProfile` once — so profiles with stale, missing, or invalid persisted `dominant_color` values still load as long as their ratios are valid. The stored field remains in the JSON for backward compatibility.
4. TDD (strict): first write/extend tests, then implement:
   - `tests/audio/test_spectral_profile.py`: each band dominance, BLUE at its lower threshold, multi-band tie-break by largest excess, exact-excess tie resolved RED > GREEN > BLUE, near-tie boundary values, all-below-threshold -> MIXED.
   - `tests/test_track_repository.py`: stored profiles with stale, missing, and invalid `dominant_color` values are recomputed on read from their ratios; profiles with invalid ratios still return `None`.
   - `tests/test_transition_scoring.py`: `_spectral_color_penalty` regression — with `spectral_cohesion > 0`, adjacent tracks whose colors differ under the NEW rule are penalized and same-color pairs are not (the penalty reads `dominant_color`, so recalibration changes which pairs it fires on).
   - Default-path regression: building a recommendation with default `AppSettings` (`spectral_cohesion = 0.5`) exercises the color penalty under the new rule — pin that the penalty fires for differing-color adjacents and not for same-color adjacents through the settings-driven path.
5. Empirical validation (reproducible): run the classification over all stored `(red_ratio, green_ratio, blue_ratio)` triples in `~/.xfinaudio/xfinaudio.sqlite3` (`tracks.spectral_profile_json`, denominator = rows with a non-null profile). Expected on the reference library of 10,390 profiles: RED 3,192 / GREEN 3,940 / BLUE 1,071 / MIXED 2,187 (tolerance: exact match for this frozen snapshot; if the library changed, shares within ±2 percentage points). Record the observed counts in the review log; do not commit any library data.

## Key decisions & tradeoffs

- **Per-band absolute thresholds** over the two rejected alternatives:
  - *Margin-over-second-place*: structurally cannot rescue BLUE (max 0.4% of tracks at any margin) because high-frequency energy never outweighs bass+mids.
  - *Library-relative normalization* (divide by library mean ratio): balances all colors (~25% each) but makes a track's color depend on which other tracks exist — non-deterministic across libraries, breaks cache/profile comparability. Rejected.
- **Thresholds (0.45 / 0.45 / 0.25)** calibrated by simulation against the user's real 10,390-track library.
- **Recompute-on-deserialize** over a one-shot DB migration: self-healing (old and future profiles always reflect the current rule), no partial-migration failure modes, no external consumer reads the JSON directly.
- **Analyzer signal chain unchanged** (`power=1.0` mel spectrogram, first-30s window, 250/2000 Hz band edges): changing any of these forces re-analyzing 10k audio files; deferred as a possible phase 2.
- `score_spectral_similarity` uses raw ratios, not `dominant_color` — unaffected by design. However, `_spectral_color_penalty` (`recommendation/scoring.py:320`) DOES read `dominant_color`, and the effective desktop default enables it: `ScoringSettings.spectral_cohesion` defaults to 0.5 (`config/settings.py:37`) and the Build screen slider initializes at 50%. `TransitionScoringConfig`'s internal 0.0 default only applies to library-level callers that bypass settings. Recalibration therefore changes recommendation ordering for default desktop users. This is accepted as intended behavior (fewer meaningless MIXED pairs makes the penalty informative instead of near-inert) and is pinned by regression tests, including one through the default settings-to-recommendation path.

## Risks / open questions

- Thresholds are tuned against one library (Latin/DJ-heavy); other libraries may skew differently. Mitigation: constants are trivial to retune, and recompute-on-read makes retuning retroactive for free.
- Tracks near two thresholds can flip color under the largest-excess tie-break; acceptable for a coarse 4-value badge. Exact ties resolve deterministically (RED > GREEN > BLUE).
- Recommendation ordering WILL change for default desktop users (effective default `spectral_cohesion = 0.5`) because the color penalty now fires on different pairs; accepted and covered by the scoring regression tests.
- `_spectral_jump_warnings` in playlists will report more shifts now that fewer tracks are MIXED — expected and desirable, not a regression.

## Out of scope

- Changing `power`, band edges, sample window, or any part of `analyze_spectral_profile`'s signal chain (would require full library rescan).
- DB migrations or schema changes.
- UI changes beyond the existing badge rendering.
- Tuning `score_spectral_similarity` or scoring weights.
