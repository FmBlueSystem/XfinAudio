# Design

Pure validated Library query module plus a small Qt panel; LibraryScreen combines
its existing quick/search filters with exact structured metadata predicates.
No AppState schema changes and no database/audio mutation.

Create interpretation and planning become separate asynchronous stages. A dedicated
preview widget shows validated intent and current constraints. The controller keeps
a context snapshot for preview validity and owns cancellation request IDs. Queued
completion envelopes carry their ID all the way to the UI slot, avoiding late-result
races. Edit/cancel discard preview; confirmation snapshots candidate controls and
loudness before worker execution. Existing plan application remains the explicit
selected-variant action.

The intent adapter defaults to genre vocabulary only. Opt-in title/genre payloads
are explicit per request. Unknown JSON fields/paths cannot create local constraints.
Injected extractors and plan builders enable real QWidget tests without network.
The coordinator integrates Configure AI and runtime settings through public hooks.
