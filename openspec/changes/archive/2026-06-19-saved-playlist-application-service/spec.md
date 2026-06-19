# Spec: Saved playlist application service

- Desktop SHALL delegate create, rename, duplicate, delete, and track-order persistence to an application service while keeping UI refresh/sync in desktop.
- The service SHALL persist recommendations with explicit or strategy/date default names.
- The service SHALL build saved-playlist export recommendations with fallback complete `TrackRecord`s for missing scanned paths; desktop still invokes Serato export.
