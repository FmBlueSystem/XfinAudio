# Requirements

- Given a folder-label read is pending, when newer root-count events arrive and that read succeeds, then one coalesced subsequent read starts and eventually displays the latest labels.
- Given that overlap, when the older read fails, then the queued newer event still receives one read.
- Given a failed read with no newer root notification, when the application becomes idle, then no automatic retry occurs.
- Across these reads, local volume/watch drafts, save revision, active route, focus and playback remain unchanged. Existing explicit refresh remains available.
