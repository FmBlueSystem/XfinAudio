# Design: Saved playlist application service

Add `SavedPlaylistService` over `PlaylistRepositoryPort` for UI-independent saved-playlist use cases.

`PlaylistCoordinator` remains the presentation adapter for signals, refresh, editor rendering, undo toolbar, tab switching, app-state replacement, and export invocation.

Safety: no schema, UI, audio, DSP, export-format, or live Serato DB V2 changes.
