# Optional AI assists
Add explicit, disclosed AI interpretation to Library, Editor and saved playlists while retaining offline actions. Never send audio, paths or names as metadata, never save or apply editor drafts automatically. Roll back by removing the installation hook.

Delivery uses chained commits, each at most 400 changed lines: (1) opt-in panel and guarded worker, (2) Library/Editor integration, (3) saved-set integration and regression verification. Services are a separate sibling chain.
Approved scope extension: add optional, bounded read-only AI commentary for Metadata aggregate repair gaps and existing Live candidate metrics. Fourth commit implements these two surfaces; fifth, if needed, verifies installation/lifecycle. Existing local truth and ranking remain authoritative.
