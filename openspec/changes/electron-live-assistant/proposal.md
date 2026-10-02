# Qt-free local Live guidance

Restore the existing deterministic Live Assistant over the exact current reviewed engine set. Extract its pure scoring/readiness functions from the Qt-importing desktop package unchanged, preserving the legacy import facade. Add bounded opaque session commands and a Spanish renderer for current track, ranked choices, preview, manual next-track history and elapsed time. This does not control Serato decks, detect playback, perform DSP or call providers.

Only a fully ready current review is eligible; needs_review stays unavailable as in the existing Live implementation. Never widen the applied pool or generation controls. Source/session changes invalidate old actions. No audio/Serato/database writes occur.

Proposed review chain, each patchset capped at400 added+removed lines: pure extraction and compatibility tests; session/source snapshot backend and tests; typed host/preload bounds; renderer controller; accessible view; app integration and subprocess/native QA. Split units further before publication as necessary. Nothing is pushed or released.
