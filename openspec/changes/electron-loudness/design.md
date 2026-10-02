# Design

A headless loudness facade owns lazy engine composition, settings access, immutable previews and one active run. It reuses existing LoudnessCompletionService/FfmpegLoudnessAdapter/write_loudness_tags and TrackRepository. Opaque track IDs are resolved from the authorized library; renderer cannot provide paths, FFmpeg arguments, credentials or confirmation flags.

The tag writer opens the expected canonical directory lineage and regular file with O_NOFOLLOW, binds descriptor identity to the confirmed source, and uses Mutagen file-object loading/saving on that descriptor. Original bytes are copied into an exclusive app-owned backup before a changed save. Backups use unsupported .bak extensions and are not scanned as music. Advisory file locking prevents cooperating app instances from overlapping commits. Errors retain backups and report partial outcomes honestly.

Trusted main owns native confirmation and active-run drainage. Cancellation reaches the original service and its child-process lifecycle; generic bridge kill timeouts must not cut an in-progress metadata commit. UI supports explicit review/run/cancel, real status/values, a bounded selection and single-track force-reanalysis. Provider services remain uncomposed.
