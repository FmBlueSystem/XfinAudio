# Design: Library repository port boundary

## Architecture

Add `xfinaudio.library.ports` as the explicit contract module for repository boundaries currently embedded in concrete repository classes and local application protocols. Keep the contracts focused: scan persistence, display listing, spectral cache access, and saved-playlist persistence are separate capabilities.

The ports live in `library` for this slice because the corresponding models (`TrackRecord`, `Playlist`, `PlaylistSummary`) and concrete repositories already live there. This avoids inventing a broader `application.ports` package before there are multiple application services consuming it.

## Affected files

- `src/xfinaudio/library/ports.py` — new focused Protocol definitions (`TrackRepositoryPort`, `TrackDisplayRepositoryPort`, `TrackSpectralProfileCacheReaderPort`, `TrackSpectralProfileCachePort`, `PlaylistRepositoryPort`).
- `src/xfinaudio/application/playlist_workflow.py` — imports shared track persistence/cache port instead of defining a duplicate local protocol.
- `src/xfinaudio/desktop/playlist_coordinator.py` — depends on `PlaylistRepositoryPort` for host typing.
- Tests — add architecture/port conformance coverage.

## Safety

- No storage schema changes.
- No audio mutation.
- No DSP scope.
- No live Serato DB V2 writes.
- No UI behavior changes.

## Review budget

Expected changed lines: 180-280 including SDD artifacts and tests. Chained PRs are not expected.
