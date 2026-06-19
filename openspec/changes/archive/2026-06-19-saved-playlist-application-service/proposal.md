# Proposal: Saved playlist application service

Move saved-playlist use-case orchestration from `desktop.playlist_coordinator` into UI-independent `xfinaudio.application.saved_playlists`.

In: CRUD commands, recommendation save naming/persistence, export recommendation construction, repository-port usage, desktop delegation.

Out: UI redesign, DB/storage changes, export format changes, audio mutation, DSP, live Serato DB V2 writes.
