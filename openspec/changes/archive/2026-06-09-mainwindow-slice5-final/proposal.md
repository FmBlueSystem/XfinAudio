# Proposal: MainWindow Slice 5 — Final Alias & Coordinator Cleanup

## Intent

Remove the legacy property alias layer (~120 widget-forwarding shims) and complete `MainWindow` decomposition by extracting playlist and live-assistant orchestration into dedicated coordinators with Host Protocols. This eliminates technical debt, shrinks `MainWindow`, and gives the remaining screens the same Protocol-bound structure established by earlier coordinator slices.

## Scope

### In Scope
1. **Remove property alias layer** — Delete `@property` shims in `MainWindow` (lines ~447–566) that forward to screen widgets (`folder_button`, `scan_button`, `strategy_combo`, `recommendation_table`, `prep_copilot_table`, etc.).
2. **Update tests** — Replace alias-based assertions in `tests/test_main_window.py` with canonical screen paths (`window._library_screen.tracks_table`, `window._review_screen.recommendation_table`, etc.).
3. **Extract `PlaylistCoordinator`** — Wire `MyPlaylistsScreen` CRUD signals and `PlaylistEditor` save/export/track-removed signals to `PlaylistRepository`; keep `MainWindow` delegations minimal.
4. **Define `PlaylistHost(Protocol)`** — Minimal surface exposed to the coordinator (e.g., `playlist_repository`, `workflow_tabs`, `_sync_state`, records lookups).
5. **Extract `LiveAssistantCoordinator`** — Wire `LiveAssistantScreen` exit/preview/load-next signals, move `_on_live_load_next` candidate recalculation, and handle tab navigation.
6. **Define `LiveAssistantHost(Protocol)`** — Minimal surface (e.g., `live_assistant_screen`, `audio_player`, `workflow_tabs`, `_sync_state`, records lookups).

### Out of Scope
- New product behavior or UX changes.
- New features beyond wiring existing screen signals.
- Audio player internals, table populators, prep-copilot logic.

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `desktop-main-window`: remove widget property aliases; introduce `PlaylistCoordinator` and `LiveAssistantCoordinator` with `PlaylistHost` and `LiveAssistantHost` Protocols; update tests to access widgets through screens.

## Approach

Apply behavior-preserving extraction following the `ExportCoordinator` → `ExportHost` precedent:
- Replace alias accesses in `MainWindow` internals and tests with direct `_screen` references.
- Instantiate `PlaylistCoordinator(host=self)` and `LiveAssistantCoordinator(host=self)` in `MainWindow`; coordinators connect signals and call repository/audio player.
- Define Protocols in the coordinator modules and break any remaining circular `TYPE_CHECKING` imports of `MainWindow`.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/main_window.py` | Modified | Delete ~120 lines of property aliases; add coordinator instantiation and thin delegations. |
| `tests/test_main_window.py` | Modified | Replace alias-based assertions with `window._<screen>` widget paths. |
| `src/xfinaudio/desktop/playlist_coordinator.py` | New | Playlist list/editor signal wiring and `PlaylistRepository` orchestration. |
| `src/xfinaudio/desktop/live_assistant_coordinator.py` | New | Live Assistant signal wiring, load-next handling, and suggestion recalculation. |
| `src/xfinaudio/desktop/screens/my_playlists_screen.py` | None (wiring only) | No behavioral change; signals already defined. |
| `src/xfinaudio/desktop/screens/playlist_editor.py` | None (wiring only) | No behavioral change; signals already defined. |
| `src/xfinaudio/desktop/screens/live_assistant_screen.py` | None (wiring only) | No behavioral change; signals already defined. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Tests missed during alias migration | Med | Run full test suite; grep for all `window.<alias>` usages. |
| Protocol surface incomplete | Low | Audit all `host.` accesses before finalizing Protocol. |
| Coordinator signal wiring breaks existing flows | Low | Keep `MainWindow` public methods as thin delegates; preserve existing signal connections. |

## Rollback Plan

Revert the individual commits. Each item is isolated to specific files with no schema or data migrations, so `git revert` restores prior behavior immediately.

## Dependencies

None

## Success Criteria

- [ ] `MainWindow` line count is reduced by at least 100 lines after alias removal and coordinator extractions.
- [ ] All `window.<alias>` references in tests are replaced with screen widget paths.
- [ ] `PlaylistCoordinator` and `LiveAssistantCoordinator` type-check against their respective Host Protocols instead of `MainWindow`.
- [ ] `uv run pytest -q` passes with zero failures.
- [ ] `uv run ruff check .` reports zero errors.
- [ ] `uv run ruff format --check .` passes.
