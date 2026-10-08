# Tasks: remove-per-query-ai-confirmation

- [x] 1. Map the current two-layer per-query authorization (consent tick + native dialog).
- [x] 2. RED: Python test — `ai.settings.update` accepts `autoAuthorize`, `ai.status` exposes it, persistence round-trips.
- [x] 3. RED: Node host test — with `autoAuthorize`, `ask()` sends `ai.run` without `ai.confirmation`/dialog; without it, dialog still required.
- [x] 4. RED: Node security test — `saveAiSettings` accepts optional boolean `autoAuthorize`, rejects non-boolean.
- [x] 5. RED: renderer tests — `canAsk` without consent tick when enabled; `dirty` tracks the toggle; `save()` sends it; `statusCopy` requires the field; view checkbox wired.
- [x] 6. GREEN: implement Python model/protocol/preferences, security allowlist, host skip, main dialog checkbox + persist, renderer state/view.
- [x] 7. Docs: release notes bullet, README AI posture sentence, task log entry.
- [x] 8. Verify: full gate + live CDP evidence (toggle on → send without dialog).
