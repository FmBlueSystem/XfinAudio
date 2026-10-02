# Requirements

- Given an absent, blocked, needs-review or stale applied review, opening Live fails closed without fallback suggestions
- Given a fresh fully ready review, Live starts from its exact first track and returns real ranked candidates from the applied pool, retaining start/end/manual/arc/locked/excluded controls
- Preview only plays through the existing authorized audio protocol; it does not advance Live
- A manually chosen freshly eligible next track advances once and appends the previous current track to history; forged/stale/repeated actions do not advance
- Navigation preserves the session; opening the same unchanged review is idempotent. Explicit clear resets it. Scan/generation/source changes invalidate old sessions and suggestions
- Renderer receives only opaque IDs and track DTOs, never paths or raw engine objects. Session revisions reject stale concurrent clicks
- Timer/history are honest local guidance state, not claims of live Serato playback or detected audio
- Missing files/core disconnect disable suggestions and mutation while preserving explanatory UI
- Legacy Qt imports retain function/type identity and behavior through a compatibility facade
