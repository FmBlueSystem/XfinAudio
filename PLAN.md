# Plan: Removed playlist tracks must not be exported
_Diagnosed by Claude — fix delegated to Codex_

## Bug (confirmed root cause, with evidence)

When the user removes a track from a generated recommendation in the Review screen ("Remove from Playlist"), the track is still included in every export (Serato crate, other DJ software, readiness sidecars).

Data flow:
1. Review screen's remove button emits `track_remove_requested(path)` (`src/xfinaudio/desktop/screens/review_screen.py:89,330-340`), handled by `on_track_remove_requested` (`src/xfinaudio/desktop/library_controller.py:260-283`), which calls `apply_playlist_track_removed` — this ONLY adds the path to `AppState.playlist_removed_paths` (`src/xfinaudio/desktop/app_state_transitions.py:106-108`).
2. The Review UI filters removed paths **for display only**: `review_view_model.py:146-157` (`recommendation_rows`), `:64-68` (`readiness_status`), `:138-143` (`can_export`) all skip `state.playlist_removed_paths`.
3. The export flow reads `host.last_recommendation` directly — the ORIGINAL, unfiltered `PlaylistRecommendation`:
   - `src/xfinaudio/desktop/serato_recommendation_export.py:154` (`export_recommendation_to_serato`), `:233-236` and `:253-256` (preview/report paths)
   - `src/xfinaudio/desktop/software_export_coordinator.py:34` and `:80`
   Nothing anywhere subtracts `playlist_removed_paths` before exporting. The removal is purely cosmetic.

## Fix approach

Add a single pure helper and use it at every export entry point:

1. **New pure function** in `src/xfinaudio/recommendation/playlist_service.py` (or a small new module if playlist_service is the wrong home — implementer's call, but it must be pure and unit-testable without Qt):
   ```python
   def recommendation_without_paths(
       recommendation: PlaylistRecommendation, removed_paths: frozenset[str]
   ) -> PlaylistRecommendation:
   ```
   - Returns the recommendation unchanged (same object is fine) when `removed_paths` is empty or intersects nothing.
   - Otherwise returns a copy with `ordered_tracks` filtered, and `transition_scores` **recomputed for the new adjacencies** (removing a middle track creates a new seam between its former neighbors — reuse the existing `_score_ordered_tracks`/`score_transition` machinery so the scores stay honest; do NOT just drop the removed track's score entries, that would misalign scores with adjacencies).
   - `total_score` updated consistently with the recomputed transition scores.
   - `PlaylistRecommendation` is a frozen pydantic model — use `model_copy(update=...)`.

2. **Apply it at every export read-site of `host.last_recommendation`**, filtering by the AppState's `playlist_removed_paths`:
   - `serato_recommendation_export.py` — all three read sites (`:154`, `:233-236`, `:253-256`), so the confirmed export, the preview, and the readiness report all agree with what the Review screen shows.
   - `software_export_coordinator.py` — both read sites (`:34`, `:80`).
   - Find how those hosts access AppState (`host` protocol / `self._state` on the controllers — check `export_coordinator.py:84`'s host protocol and how `library_controller` reaches state) and thread `playlist_removed_paths` through minimally. If the host protocol needs a new member (e.g. `playlist_removed_paths` property), add it where the protocol is defined and implement it on the real window/state holder.

3. **Edge case — everything removed**: `review_view_model.can_export` (`:138-143`) already blocks export when zero tracks remain, so the export entry points should not be reachable with an empty result; still, the helper must handle the empty result without crashing, and an assertion-friendly guard (return early with a status message rather than exporting an empty crate) at the export sites is acceptable defense.

## Tests (RED-first — this repo enforces strict TDD)

- Unit tests for `recommendation_without_paths` in `tests/test_playlist_service.py` (or a matching new test module):
  - Removing a middle track: `ordered_tracks` shrinks, `transition_scores` has exactly `len(ordered_tracks)-1` entries, and the new seam between former neighbors is scored (not carried over stale).
  - Removing nothing / empty `removed_paths`: recommendation returned unchanged.
  - Removing the first/last track.
  - Removing all tracks: empty `ordered_tracks`, empty `transition_scores`, no crash.
- Export-level regression test (mirror the existing patterns in `tests/test_export_coordinator.py` / `tests/test_playlist_coordinator.py` for how exports are tested with fake hosts): generate a recommendation, mark one track removed in state, run the Serato export path, assert the written/planned crate does NOT contain the removed track's path. This is the test that reproduces the user-reported bug — it must fail before the fix and pass after.

## Verification (all must pass)

```
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

## Out of scope

- Changing how removal works in the Review UI (undo/redo via `playlist_removed_paths` stays exactly as is).
- Re-running the optimizer after a removal (the remaining order is preserved as-is; only adjacency scores are recomputed).
- Persisted "My Playlists" export path (`playlist_coordinator.py:146` builds a fresh recommendation from a saved playlist's own track list — separate flow, not driven by `last_recommendation`, not part of this bug).
