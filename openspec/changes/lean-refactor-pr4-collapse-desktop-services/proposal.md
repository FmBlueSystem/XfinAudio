## Why

The `src/xfinaudio/desktop/` package has 34 files. Many are single-caller wrappers
around a 1-implementation `Protocol` that exists solely to type-hint `MainWindow` —
YAGNI at its purest. Two files are completely dead in production. A handful more are
genuine state machines whose QThread/QObject lifecycle and signal handlers live in
two parallel files that grow in lockstep.

This PR collapses the obvious cases, deletes the dead code, and moves screen-local
wiring into the screens that own it. Behavior is preserved; the test suite is the
contract.

## What changes

### Pure deletes (dead in production)

- `src/xfinaudio/desktop/recommendation_worker.py` (54 LOC) — `RecommendationWorker`
  QRunnable has zero production importers; only `tests/test_recommendation_worker.py`
  references it. The live path goes through `BackgroundWorker` in `_workers.py`.
- `src/xfinaudio/desktop/live_assistant_state.py` (167 LOC) — pure-Python state
  machine, zero production importers; only `tests/test_live_assistant_state.py`
  references it. The live `LiveAssistantCoordinator` does not use it.
- `tests/test_recommendation_worker.py` — test of dead code, no longer needed.
- `tests/test_live_assistant_state.py` — test of dead code, no longer needed.

### Merges (collapsing controller+coordinator pairs)

- `src/xfinaudio/desktop/scan_controller.py` (119 LOC) + `scan_coordinator.py` (181
  LOC) → single `src/xfinaudio/desktop/scan_service.py`. The `ScanHost` Protocol
  has exactly one implementation (`MainWindow`); it is replaced by direct calls.
- `src/xfinaudio/desktop/recommendation_controller.py` (95 LOC) +
  `recommendation_coordinator.py` (180 LOC) → single
  `src/xfinaudio/desktop/recommendation_service.py`. The `RecommendationHost`
  Protocol has exactly one implementation; replaced by direct calls.

### Moves (single-caller, screen-local wiring)

- `src/xfinaudio/desktop/live_assistant_coordinator.py` (56 LOC) → merged into
  `src/xfinaudio/desktop/screens/live_assistant_screen.py`. The screen owns the
  signal wiring; no extra layer is justified.
- `src/xfinaudio/desktop/navigation_controller.py` (80 LOC) → renamed
  `src/xfinaudio/desktop/navigation.py` (drop the `Controller` suffix; this is a
  pure-AppState state machine, not a Qt controller).
- `src/xfinaudio/desktop/settings_controller.py` (68 LOC) → merged into
  `src/xfinaudio/desktop/settings_dialog.py`. The settings dialog owns the
  open/apply/reset lifecycle.
- `src/xfinaudio/desktop/menu_builder.py` (93 LOC) → renamed
  `src/xfinaudio/desktop/menu.py`. Drop the `Builder` suffix; it is a plain helper.

### Not touched (kept as separate modules)

- `src/xfinaudio/desktop/export_coordinator.py` (556 LOC) — single-caller but
  genuine state machine with planning, sidecar writing, and multi-software
  exports. Has its own test file (`tests/test_export_coordinator.py`) and
  warrants its own module. Renaming to `export_service.py` is a separate
  decision.
- `src/xfinaudio/desktop/export_view_model.py` (139 LOC) — pure-utility display
  mapper, used by both `main_window.py` and `screens/export_screen.py`.
- `src/xfinaudio/desktop/playlist_coordinator.py` (205 LOC) — single-caller
  thin wrapper; merging into `playlists_screen.py` is viable but the screen
  has its own session-host concerns. Tabled for a follow-up.
- `src/xfinaudio/desktop/recommendation_presenter.py` (105 LOC) — pure
  `build_recommendation_pool` utility, called from `main_window.py` directly.

## Non-goals

- Splitting `main_window.py` (1761 LOC) — that is PR 5.
- Refactoring `export_coordinator.py` or moving it.
- Renaming `export_coordinator.py` to `export_service.py`.
- Merging `playlist_coordinator.py` into its screen.

## Impact

- Net: ~700 LOC removed across 6 deleted files + 4 merged/moved files.
- Files in `src/xfinaudio/desktop/` root: 34 → 26.
- 1-implementation Protocols removed: 4 (`ScanHost`, `RecommendationHost`,
  `LiveAssistantHost`, `SettingsHost`, `MenuHost`).
- Review budget: ~700 LOC, above the 400-line cap. **This PR is the largest of
  the chain** and was the main reason for slicing the refactor across two PRs.
  PR 5 only touches `main_window.py`; this PR only touches the 12 desktop modules
  + 2 test files.
- Risk: medium. The test suite (861 tests) is the safety net. Every consumer of
  every moved/merged module is updated in the same commit.
