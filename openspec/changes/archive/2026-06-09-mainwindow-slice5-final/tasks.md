# Tasks: MainWindow Slice 5 — Final Alias & Coordinator Cleanup

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~570 (348 aliases + 130 playlist + 90 live-assistant) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (alias removal) → PR 2 (coordinators: Items 2+3) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Base | Notes |
|------|------|-----------|------|-------|
| 1 | Item 1: Alias removal + test repointing | PR 1 | main | ~350 lines; pure refactor, no coordinator deps |
| 2 | Items 2+3: PlaylistCoordinator + LiveAssistantCoordinator | PR 2 | main | ~220 lines; independent of each other, depend on PR 1 |

---

**IMPORTANT**: `tracks_table` (main_window.py line 587) is a REAL attribute — do NOT touch it. It is NOT part of the alias layer.

## Phase 1: Item 1 — Alias Removal (ordered, each step depends on prior)

- [x] 1.1 Repoint internal `MainWindow` callers (`_apply_compact_mac_layout`, `_apply_compact_table_columns`, `_apply_visual_design`, `_setup_connections`) — replace `self.<alias>` with `self._<screen>.<widget>`
- [x] 1.2 Update `ExportCoordinator` — repoint `host.export_guidance_label` → `host._export_screen.export_guidance_label`; repoint `host.serato_export_history_table` → `host._export_screen.history_table`; trim both from `ExportHost` Protocol
- [x] 1.3 Update `test_main_window.py` (~210 replacements) — replace all `window.<alias>` with `window._<screen>.<widget>` per design table
- [x] 1.4 Update `integration_flow.py` — repoint `scan_button`, `recommend_button`, `strategy_combo`, `song_search_input`, `recommendation_table`
- [x] 1.5 Delete `test_visual_integration.py:187` self-referential identity assert (`visible_tracks_table`)
- [x] 1.6 Delete 27 `@property` alias definitions from `MainWindow` (lines 455–566)

## Phase 2: Item 2 — PlaylistCoordinator (independent, can parallel with Phase 3)

- [x] 2.1 Create `playlist_coordinator.py` with `PlaylistHost(Protocol)` and `PlaylistCoordinator` class — `connect_signals()`, CRUD + save/export/remove-track/refresh handlers
- [x] 2.2 In `MainWindow.__init__`, instantiate `PlaylistCoordinator(host=self)` and call `connect_signals()`
- [x] 2.3 Add thin 1-line delegation methods in `MainWindow` for playlist public API

## Phase 3: Item 3 — LiveAssistantCoordinator (independent, can parallel with Phase 2)

- [x] 3.1 Create `live_assistant_coordinator.py` with `LiveAssistantHost(Protocol)` and `LiveAssistantCoordinator` class — `connect_signals()` + `load_next()` (moved `_on_live_load_next` body)
- [x] 3.2 In `MainWindow.__init__`, instantiate `LiveAssistantCoordinator(host=self)` and call `connect_signals()`; keep thin `_on_live_load_next` delegate
- [x] 3.3 Move live-assistant signal wiring (exit/preview/load-next) from `MainWindow` into coordinator

## Phase 4: Verification

- [x] 4.1 `uv run pytest -q` — all tests pass (740 passing)
- [x] 4.2 `uv run ruff check .` — zero errors
- [x] 4.3 `uv run ruff format --check .` — passes
