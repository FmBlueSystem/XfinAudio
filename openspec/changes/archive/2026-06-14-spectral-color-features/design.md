# Design: Spectral Color Features

## Overview

Add a lightweight, read-only spectral analyzer module that extracts color profiles from audio files during scan, caches them in SQLite, and feeds a new spectral similarity component into transition scoring and review warnings.

## New modules

### `src/xfinaudio/audio/spectral_profile.py`

Pure-Python domain model and analyzer interface.

- `SpectralProfile` pydantic model:
  - `red_ratio: float` (0.0–1.0)
  - `green_ratio: float` (0.0–1.0)
  - `blue_ratio: float` (0.0–1.0)
  - `centroid_hz: float`
  - `rolloff_hz: float`
  - `rms: float`
  - `dominant_color: Literal["RED", "GREEN", "BLUE", "MIXED"]`

- `analyze_spectral_profile(path: Path) -> SpectralProfile | None`
  - Loads audio at `sr=22050`, mono.
  - Computes mel-spectrogram with `n_mels=64`, `n_fft=1024`, `hop_length=512`.
  - Sums energy in bands mapped to Serato-style colors:
    - RED: 20–250 Hz
    - GREEN: 250–2000 Hz
    - BLUE: 2000+ Hz
  - Computes spectral centroid, rolloff, and RMS.
  - Returns `None` on any failure without raising.
  - Does not mutate the source file.

- `score_spectral_similarity(left: SpectralProfile, right: SpectralProfile) -> float`
  - Returns 1.0 when both profiles share the same dominant color.
  - Returns a lower value as color distance increases.
  - Uses cosine similarity over the (red, green, blue) vector as the numeric base.

### `src/xfinaudio/audio/__init__.py`

Re-exports `SpectralProfile`, `analyze_spectral_profile`, `score_spectral_similarity`.

## Modified modules

### `src/xfinaudio/library/models.py`

Add optional `spectral_profile: SpectralProfile | None = None` to `TrackRecord`.

### `src/xfinaudio/library/track_repository.py`

- Bump `SCHEMA_VERSION` to 2.
- Add nullable JSON column `spectral_profile_json` to the `tracks` table.
- Update `_record_to_row` / `_row_to_record` to serialize/deserialize the profile.
- Provide migration path for existing v1 databases: add the column if missing, then set `PRAGMA user_version = 2`.

### `src/xfinaudio/library/scan_service.py`

- After parsing Mixed In Key metadata, call `analyze_spectral_profile(path)`.
- Attach the result to the `TrackRecord`.
- Keep analysis optional: if the dependency is missing or analysis fails, `spectral_profile` remains `None`.
- Cancellation remains cooperative: check the token between the metadata read and spectral analysis steps.

### `src/xfinaudio/recommendation/scoring.py`

- Add `spectral: float = 0.10` to `ScoringWeights`.
- Add `spectral` to `TransitionScore.component_scores`.
- In `score_transition`, when both tracks have a profile, compute `score_spectral_similarity(left.profile, right.profile)` and include it in the weighted total.
- When one or both profiles are missing, ignore the spectral weight (do not redistribute it; the remaining components keep their configured weights).

### `src/xfinaudio/quality/recommendation_quality.py` or review warnings

- Add a spectral jump warning when adjacent tracks have different dominant colors.
- Warning text: e.g., "Spectral shift: RED → GREEN".

### `src/xfinaudio/desktop/screens/library_screen.py` and `review_screen.py`

- Display a small color badge (🔴/🟢/🔵/⚪) in the library table when a profile exists.
- Show the color badge and warning in the review transition table.

## Dependency management

Add to `pyproject.toml` under optional or runtime dependencies:

```toml
dependencies = [
  # existing deps
  "librosa>=0.10,<0.12",
  "numpy>=1.24,<3.0",
]
```

Run `uv lock` after changing `pyproject.toml`.

If librosa import fails at runtime, the analyzer returns `None` for every track and the app degrades to metadata-only behavior.

## Performance strategy

- Use `ProcessPoolExecutor` in `scan_service` for batch spectral analysis after metadata scanning completes.
- The UI worker thread submits batches and reports progress incrementally.
- Cache results in SQLite; incremental scans only re-analyze files whose mtime or size changed.
- Default analyzer settings are tuned for speed over precision:
  - `sr=22050`
  - `n_mels=64`
  - `n_fft=1024`

## Safety

- No audio file mutation.
- No BPM/key/beatgrid detection.
- No real-time analysis during playback.
- No Serato Database V2 writes.
- Analysis failures are caught and logged; missing profiles are tolerated.

## Tests

- `tests/audio/test_spectral_profile.py`: synthetic fixture classification, real-file classification, failure handling.
- `tests/library/test_track_repository.py`: schema migration and profile persistence.
- `tests/recommendation/test_scoring.py`: spectral component scoring and missing-data fallback.
- `tests/quality/test_recommendation_quality.py`: spectral jump warnings.
