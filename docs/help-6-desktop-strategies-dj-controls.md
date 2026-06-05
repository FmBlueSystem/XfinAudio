# HELP-6 Desktop Playlist Strategies and DJ Controls

HELP-6 adds metadata-only playlist recommendation controls for desktop use. The implementation builds on the HELP-5 deterministic optimizer and does not perform DSP, key/BPM detection, beat tracking, audio rendering, audio mutation, exports, Serato integration, or mixing.

## Strategy profiles

Supported strategies are exposed by `xfinaudio.recommendation.strategies`:

- `harmonic_journey`: emphasizes Camelot-compatible movement.
- `warmup`: filters to low/mid energy and starts from lower energy selections.
- `build`: prefers ascending energy movement.
- `peak_time`: filters to high-energy selections.
- `chill`: filters to lower energy and lower BPM selections.
- `same_energy`: emphasizes stable energy with a narrow tolerance hint.
- `same_vibe`: emphasizes tags/genre when available and falls back gracefully when vibe metadata is absent.

Each profile contains scoring weights plus eligibility and ordering hints. Ordering strategies such as `warmup`, `build`, `peak_time`, and `chill` preserve their strategy order instead of letting the optimizer re-sort by path. Strategy policy remains pure Python and outside the PySide6 UI.

## DJ controls

`xfinaudio.recommendation.controls.DJControls` supports:

- locked paths;
- excluded paths;
- start path;
- end path;
- manual order path prefix.

Controls validate impossible overlaps such as excluding a locked, start, or end path. Duplicate manual order paths are rejected to prevent duplicate playlist rows. `apply_controls()` removes excluded tracks, validates known start/end/manual/locked paths, and returns resolved candidate tracks plus an applied-controls summary.

## Playlist recommendation service

`xfinaudio.recommendation.playlist_service.recommend_playlist()` combines:

1. complete-track filtering;
2. strategy filtering and sort hints;
3. DJ controls;
4. HELP-5 `recommend_sequence()`;
5. optional scoring weight overrides.

The returned `PlaylistRecommendation` includes ordered tracks, transition scores, selected strategy, warnings, applied-controls summary, optimizer name, and total score.

Manual order is treated as a fixed prefix where feasible. Remaining tracks are regenerated around the available start/end constraints. If a manual prefix conflicts with `start_path`, the manual prefix wins and the result includes a warning. If `end_path` is present inside manual order, the end constraint wins so the track remains terminal instead of crashing or being duplicated.

## Desktop integration

The main window now includes:

- strategy dropdown;
- `Recommend Playlist` button;
- recommendation table;
- status text with strategy and count.

The UI is intentionally thin: it passes scanned `TrackRecord` objects to the recommendation service and renders the resulting order. It does not contain scoring or control business logic.

## Current limitations

- Recommendation is synchronous in the UI thread.
- Controls have a domain model and service behavior, but the desktop surface only exposes strategy selection and recommendation generation for now.
- No drag-and-drop ordering UI.
- No persistent desktop strategy/control settings.
- No audio analysis, rendering, mutation, export, Serato, or DSP functionality.
