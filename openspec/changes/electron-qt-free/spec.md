# Observable requirements

- Given a user-selected copied music folder, scanning reads tags through the existing metadata service, displays honest counts/progress and never modifies audio or live Serato data.
- Given parsed tracks, Prep uses the existing algorithm's balanced variant, shows warnings/readiness, and requires separate Save after review.
- Given a saved playlist, reopening restores its ordered tracks and reports missing files.
- Given an authorized FLAC track, preview supports play, pause, seeking and switching without permitting arbitrary filesystem reads.
- Given cancellation, navigation, a newer job or shutdown, older responses cannot replace the current view; work is cancelled/drained with a bounded shutdown.
- Given hostile paths, unknown commands, overlarge frames, remote URLs or malformed ranges, the app rejects them without exposing arbitrary paths or commands to its renderer.
- The new process imports no Qt module; the old Qt executable remains intact for rollback.
