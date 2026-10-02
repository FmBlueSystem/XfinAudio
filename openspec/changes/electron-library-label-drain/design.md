# Design

The preferences controller clears pending after its host perform has already run the generic idle drain. Observe completion of the existing label-refresh promise in app.ts and attempt the existing queued-label helper once. The helper consumes the pending notification before launching a read and keeps existing core, gate and controller guards. No new retry state, timer or controller callback is needed.

Use delayed fake API responses to prove overlap, coalescing and failure behavior at the app integration boundary. Existing preferences and navigation tests cover unchanged value/route contracts. Fake DOM does not prove native visibility or physical focus.
