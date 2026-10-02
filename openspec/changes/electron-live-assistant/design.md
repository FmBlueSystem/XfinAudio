# Design

Move desktop/live_assistance.py algorithms to application/live_assistance.py, leaving re-exports at the legacy path. Headless Live service reuses current-review recommendation and fresh source identity/readiness checks; no independent recommendation algorithm or library-pool expansion. Session fields: opaque id, source revision/review id, numeric revision, played prefix/history and monotonic current-track start. Commands are serialized by the existing server mutation owner.

Protocol: live.open({reviewId}), live.status({sessionId}), live.next({sessionId,revision,trackId}), live.clear({sessionId}). Public snapshot: sessionId, revision, sourceReviewId, state(active/complete), current track, history[{track,startedAt}], candidates[{track,score,alerts}], elapsedSeconds. Next-track marking is manual guidance, separate from audio preview.

Main/preload exposes matching narrow typed actions; renderer uses the global operation gate and stale-generation guards. Existing player handles preview. No automatic polling is required; elapsed display advances from the last authoritative monotonic reading and refreshes on session interactions.
