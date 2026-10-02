# Observable contract

Play, Pause and Play again must resume the same source/position without stop/load.
A resumed Qt PlayingState must be reflected in the application state.
Intentional content renders must not expose transient empty selection when the
selected playing path remains in the final table.

- Same-path scan completion may replace items but preserves the active pause marker.
- Reordered scan results publish the actual visible selection; if the playing path
  is no longer selected, playback stops rather than retaining stale selected paths.
- Navigation/state sync and repeated play/pause/resume/stop preserve current items.
- Closing stops the player; callbacks scoped to a destroyed player are not delivered.
