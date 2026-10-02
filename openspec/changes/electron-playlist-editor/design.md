# Design

The backend owns edit identities, original saved revision and opaque-ID/path mapping. It composes SavedPlaylistService, validate_edit, propose_edit and assess_playlist_edit. A narrowly scoped repository compare-and-update operation may be added for atomic name/order writes without changing existing Qt callers. Input is bounded (at most 500 track references per edit request) and resolved only against the authorized library/original set.

The renderer editor module owns draft presentation and explicit preview/apply/save/discard controls. Main owns narrow IPC, trusted native confirmation for dirty-close and graceful core shutdown only after close is confirmed. Existing safe/balanced/adventurous and metadata flows remain unchanged.
