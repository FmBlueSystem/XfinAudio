# Design

A pure application helper interprets supported English/Spanish edit phrases into deterministic tuple-based proposals. Validation accepts only a subset of the original paths, retains locked source members, and excludes forbidden paths. Shortening preserves source order; energy ordering uses actual energy_level and fixed locked slots. Duration targets require complete positive finite durations.

PlaylistEditor owns transient draft/preview state and renders named ordered proposals. Context fingerprints invalidate previews when relevant metadata or constraints change. PlaylistCoordinator refreshes context at preview/confirm/save boundaries, verifies repository snapshot before Save, and delegates draft reorder undo without persistence. Session guards prevent cross-playlist undo contamination. The parent supplies _show_playlist_editor(). AppState remains immutable and is never mutated here.

MyPlaylistsScreen receives real saved playlists and scanned records through the coordinator. A pure helper matches local names/metadata tokens and produces descriptive comparison text with coverage counts. Requests never invoke a network provider. Existing CRUD buttons remain explicit actions.
