# Optional AI assists
Add explicit, disclosed AI interpretation to Library, Editor and saved playlists while retaining offline actions. Never send audio, paths or names as metadata, never save or apply editor drafts automatically. Roll back by removing the installation hook.

Delivery uses chained commits, each at most 400 changed lines: (1) opt-in panel and guarded worker, (2) Library/Editor integration, (3) saved-set integration and regression verification. Services are a separate sibling chain.
