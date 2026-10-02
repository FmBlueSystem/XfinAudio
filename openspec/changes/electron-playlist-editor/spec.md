# Requirements

Opening a saved set creates an editable snapshot with opaque track IDs and honest missing-file markers. Reorder/removal and name changes are drafts until explicit Save. Discard restores the saved version. Rename/duplicate use the existing repository/service behavior. Unknown identities, added duplicates, oversized input and stale edit sessions are rejected. Concurrent saved-version changes cannot be overwritten silently; name/order commit atomically.

Offline text suggestions use the existing deterministic parser and assessment, show a reviewable proposal, and affect the draft only after Apply; Save remains separate. Missing/invalid metadata is reported honestly. No fabricated metadata or new recommendation algorithm.

Navigation preserves unsaved drafts or asks before discarding them. Window close with unsaved changes offers continue editing or discard/exit; cancel leaves the Python core available. Save-like mutations are not falsely reported cancelled after committing. No deletion or export is added in this slice.
