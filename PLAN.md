# Plan: Analyze mid-track window for spectral color (analyzer phase 2)

_Locked via grill — by Claude + Freddy_

## Goal

Spectral color is currently computed from the first 30 seconds of each track. An experiment on 80 randomly sampled library tracks (seed 42, read-only) showed the intro window disagrees with a mid-track window on 46.2% of color classifications — DJ intros (sparse percussion, fade-ins) misrepresent the track's body. Switch the analysis window to 30 seconds centered at the track middle, keep everything else in the signal chain unchanged, and re-analyze the library lazily in the background via profile versioning — without wiping existing colors while the rescan runs.

## Empirical basis (recorded 2026-07-19)

- Window stability intro vs mid (power=1, current thresholds): 53.8% agreement — material improvement potential.
- power=2.0 was evaluated and REJECTED: mean ratios become R=0.756/G=0.221/B=0.024, 88% of tracks classify RED, BLUE and MIXED die entirely. The magnitude domain (power=1.0) is what keeps the 3-band scheme discriminative. Do not revisit.
- Sanity: recomputing with the current chain reproduces stored profiles 100%.

## Approach

1. Add `analysis_version: int = Field(default=1, ge=1)` to `SpectralProfile`. Old persisted JSON (no field) deserializes as version 1. Define `CURRENT_ANALYSIS_VERSION = 2` in `spectral_profile.py`; `analyze_spectral_profile` stamps it on new profiles.
2. Change `analyze_spectral_profile` windowing: resolve track duration with `librosa.get_duration(path=...)`; analyze `offset = max(0, duration/2 - window/2)`, `duration = 30s`. Fallback: if duration cannot be resolved or is <= the window, analyze from offset 0. Keep power=1.0, sample rate 22050, 64 mels, band edges 250/2000 Hz, and the shared-STFT optimization unchanged.
3. ONE canonical window enforced by construction: REMOVE the `max_duration_seconds` parameter from `analyze_spectral_profile` and the `LibrosaSpectralAnalyzer` adapter (and the constants that feed it in `scan_service.py:286` / `spectral_completion_worker.py:26`) — the 30-second mid-track window is a module constant, not a caller choice, so version 2 CANNOT be stamped on any other window. Today `batch_analyzer._analyze_one` (:29) and the sequential fallback (:128) analyze the FULL track while scan/worker pass 30s; after this change every path is identical by construction. Cross-path test plus a test that the parameter no longer exists (signature).
4. Staleness gates — exact-equality freshness (`analysis_version != CURRENT_ANALYSIS_VERSION` is stale; a future version 3 must NOT pass a version-2 gate) at EVERY eligibility point:
   - `TrackRepository.load_spectral_profile_cache`: non-current profiles are cache misses for analysis purposes.
   - `_SpectralCompletionRunner._run_completion` (spectral_completion_worker.py:81): pending = profile is None OR non-current version.
   - `LibraryController.start_spectral_completion_worker` (library_controller.py:381): same predicate — today it filters `spectral_profile is None`, which would prevent the rescan from ever starting; controller-level regression test required.
   - `analysis_planning.try_cached_profile` and `scan_service._lookup_previous_profile`: both trust mtime/size identity alone today, so caller-supplied caches (`analyze_paths(cache=...)`, `scan_folder(previous_profile_cache=...)`) would resurrect v1 profiles. Apply the same exact-version predicate at both consumption helpers, with RED tests covering identity-matched v1, v2, and future-version profiles.
5. Scan must not erase preserved colors — identity-guarded, in BOTH layers:
   - Repository: `save_scan_results` keeps the stored `spectral_profile_json` when the incoming record carries no profile AND the stored `file_mtime_ns`/`file_size_bytes` match the incoming file identity; if the file changed, store NULL (an unconditional COALESCE would pair an old profile with new identity fields and make an obsolete profile look cache-current after an interrupted rescan). Scan-during-rescan and file-changed regression tests.
   - Live UI: `PlaylistWorkflowService.scan_folder` returns profile-less records that `show_tracks` renders directly, so the Color column would blank even with the DB preserved. After saving, attach identity-matched stored profiles (any version — display is not version-gated) to the returned records; the version predicate still queues them for re-analysis. Regression test: scan result records carry the stale profile.
6. Display is NOT gated on version: `list_tracks`/`list_display_tracks` keep returning stale-version profiles (with recomputed dominant_color) so the UI shows the old color until the new profile lands — no blank Color column during the hours-long rescan.
7. TDD (strict, RED first):
   - `tests/audio/test_spectral_profile.py`: synthetic audio whose intro and middle have different band content — analyzer classifies by the middle; short-file fallback analyzes from 0; new profiles carry version 2; cross-path window/version consistency (direct call, batch `_analyze_one`, sequential fallback).
   - `tests/test_track_repository.py`: non-current-version profiles excluded from `load_spectral_profile_cache`; still returned by `list_tracks`; old JSON without the field deserializes as version 1; `save_scan_results` with a profile-less incoming record preserves the stored profile.
   - `tests/test_spectral_completion_worker.py`: worker re-analyzes tracks with non-current profiles, skips current ones.
   - `tests/test_main_window.py` (or controller-level): `start_spectral_completion_worker` enqueues stale-version tracks.
8. Rollout with provable completion: the worker already emits progress counts; completion is validated with SQL using `COALESCE(json_extract(spectral_profile_json, '$.analysis_version'), 1)` (legacy JSON without the field counts as v1, not SQL NULL) filtered on version = 2 — total, current-version, stale-version, and NULL counts are recorded in the review log. Failed analyses (worker emits None and keeps counting) surface as stale/NULL remainder in that query. NO threshold retune decision until every readable track is version-2 or explicitly accounted for as unreadable.

## Key decisions & tradeoffs

- **Mid-track window over intro**: the track body is what a DJ actually hears in the mix; 46.2% of sampled tracks change color, confirming intros are unrepresentative.
- **power=1.0 kept**: empirically superior for band discrimination (see basis above); the original suspicion against it is refuted with data.
- **Versioned lazy re-analysis over destructive wipe or one-shot migration**: old colors keep displaying during the rescan; interrupted rescans resume naturally (version gate persists); no migration script to babysit.
- **Thresholds (0.45/0.45/0.25) unchanged for now**: mid-window sample skews GREEN-heavier (56% in the sample); a retune decision is deferred until the full-library distribution is measured — retuning is retroactively free.
- **`librosa.get_duration` for the offset** instead of threading DB duration into the analyzer: keeps `analyze_spectral_profile` self-contained; duration reads are header-based and cheap relative to decode+STFT.

## Risks / open questions

- Mid-window distribution may need a threshold retune (GREEN-heavy sample); mitigated by the frozen post-rescan validation step and free retroactive retuning.
- ~10,390 track re-analysis takes hours in the background; interruptions are safe (per-track persistence, version gate resumes).
- Tracks with unresolvable duration silently fall back to the intro window (logged by absence of failure; acceptable).
- A normal metadata re-scan during the rescan window must not wipe colors — covered by the save_scan_results preservation change and its regression test.
- `analysis_version` added to serialized JSON grows each profile by ~24 bytes; negligible.

## Out of scope

- Changing `power`, band edges, sample rate, mel parameters, or thresholds in this change.
- `score_spectral_similarity`, scoring weights, or any recommendation logic.
- UI changes; DB schema changes (the version lives inside the existing JSON column).
- Multi-segment analysis (e.g., averaging 3 windows) — possible phase 3 if mid-window proves insufficient.
