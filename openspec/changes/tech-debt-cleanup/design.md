# Design: Technical Debt Cleanup

## Technical Approach

Four isolated, test-backed edits. Items 1–2 are one-line surgical changes. Item 3
backfills four prior-cycle behaviors using existing test patterns (no new fixtures).
Item 4 promotes the function-style `export_coordinator.py` module into a stateful
`ExportCoordinator` class that owns export logic; `MainWindow` keeps thin delegation
wrappers so all existing public methods and test assertions survive unchanged.

## Architecture Decisions

| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Export extraction shape | `ExportCoordinator` class taking a `host` protocol (the `MainWindow`) for state/widget access | Pass every dependency per-call; full DI refactor | Class needs `last_recommendation`, `status_label`, `settings`, `applied_prep_copilot_variant_name`, history state. A host handle preserves behavior with minimal churn (first slice only). |
| MainWindow contract | Keep public methods (`preview_export`, `export_recommendation`, `export_recommendation_to_serato`, `export_metadata_status_to_serato`, `preview_serato_export`) as 1-line delegations | Rename/remove and update tests | Proposal requires preserving test assertions on status labels; delegation keeps the contract. |
| Module coexistence | Add class alongside existing free functions in `export_coordinator.py`; class calls them internally | Move free functions into methods | Free functions (`plan_serato_export`, `record_export`, etc.) stay pure/testable; class is the Qt-aware orchestrator. |
| Dead method removal | Delete `_populate_prep_copilot_table` only; leave free `populate_prep_copilot_table` | — | Out of scope per proposal; free function still used elsewhere. |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `src/xfinaudio/desktop/main_window.py` | Modify | Delete dead method (Item 1); replace export-method bodies with delegations to `self._export_coordinator` (Item 4). |
| `src/xfinaudio/desktop/export_coordinator.py` | Modify | Add `ExportCoordinator` class absorbing export orchestration. |
| `src/xfinaudio/config/settings.py` | Modify | `OptimizerSettings.exact_limit` default `20`→`15` (Item 2). |
| `tests/test_transition_scoring.py` | Modify | Add cache-hit + cache-clear tests (Item 3). |
| `tests/test_sequence_optimizer.py` | Modify | Add n=15 exact / n=16 heuristic boundary test (Item 3). |
| `tests/test_main_window.py` | Modify | Add thread-guard cancel + debounce tests (Item 3). |

## Item 1 — Remove Dead Method

- **Method**: `def _populate_prep_copilot_table(self, plan: PrepCopilotPlan) -> None:`
- **Location**: `main_window.py` lines **1668–1677** (signature L1668, body through L1677).
- **Action**: Delete the whole method block. No callers remain (`BuildScreen.render` replaced it). The free `populate_prep_copilot_table` import (used by `BuildScreen`) stays.

## Item 2 — Align exact_limit Default

- **Location**: `settings.py` line **28**: `exact_limit: int = Field(default=20, ge=0)`.
- **Action**: Change `default=20` → `default=15`. Matches `optimizer.recommend_sequence(exact_limit=15)` (optimizer.py L29).

## Item 3 — Missing Tests

| # | File | Test name | Setup | Assertion |
|---|------|-----------|-------|-----------|
| 3a | `test_transition_scoring.py` | `test_score_transition_cache_returns_same_object_for_identical_pair` | `cache: dict = {}`; call `score_transition(track("l"), track("r"), cache=cache)` twice with same args. | Second result `is` first result (identity, memoized); `len(cache) == 1`. |
| 3b | `test_transition_scoring.py` | `test_score_transition_new_session_cache_starts_empty` | Build `cache_a={}`, score a pair; build fresh `cache_b={}`. | `cache_b == {}` before use; scoring with `cache_b` recomputes (result `is not` the `cache_a` entry). Verifies session-scoped cache isolation. |
| 3c | `test_sequence_optimizer.py` | `test_recommend_sequence_routes_n15_exact_and_n16_heuristic` | Reuse module-level `track(...)`. Build 15 tracks and 16 tracks. Call with default `exact_limit` (now 15). | n=15 → `result.optimizer == "exact"`; n=16 → `result.optimizer == "greedy-2opt"`. Confirms boundary `len(ordered) <= exact_limit` (optimizer.py L45). |
| 3d | `test_main_window.py` | `test_main_window_second_scan_cancels_previous_run` | `ensure_app()`; `MainWindow(FakeScanService(), FakeRepository())`; `set_selected_folder(tmp_path)`; spy on `window._scan_controller.cancel` via `monkeypatch`/wrapper; call `scan_selected_folder()` twice without letting first finish. | `ScanController.start_scan` invokes `cancel()` when a thread `isRunning()` (scan_controller.py L31–33) — assert spy called once on the 2nd start, OR assert `current_scan_cancellation_token` is the 2nd token. |
| 3e | `test_main_window.py` | `test_main_window_search_debounce_fires_filter_once_after_rapid_keystrokes` | Follow L478–479 pattern; `show_tracks([...])`; monkeypatch/count `window._apply_song_filter`; emit `song_search_input.setText(...)` rapidly 3×, then `window._search_debounce.timeout.emit()` once. | `_apply_song_filter` called exactly once (debounce coalesces). `_search_debounce` is single-shot, 150ms (main_window.py L332–334). |

Note 3d/3e: tests drive the `QTimer`/thread guard deterministically by emitting
`timeout` manually (existing convention, L479) and inspecting `ScanController`
state — no real sleeps, avoiding CI flakiness (proposal risk row).

## Item 4 — Export Extraction Map

**Export logic currently in `MainWindow` (move to `ExportCoordinator`):**

| Method | Lines | Disposition |
|--------|-------|-------------|
| `_selected_export_software` | 1103–1105 | Move (reads `_export_screen` via host). |
| `preview_export` | 1107–1149 | Body → coordinator; MainWindow delegates. |
| `export_recommendation` | 1151–1209 | Body → coordinator; MainWindow delegates. |
| `preview_serato_export` | 1211–1251 | Body → coordinator; MainWindow delegates. |
| `export_recommendation_to_serato` | 1253–1316 | Body → coordinator; MainWindow delegates. |
| `_plan_current_serato_export` | 1318–1334 | Move (internal). |
| `export_metadata_status_to_serato` | 1336–1385 | Body → coordinator; MainWindow delegates (called by L701, L1917). |
| `_export_missing_metadata_worklist_to_serato` | 1387–1424 | Move (internal). |
| `_record_serato_export` | 1426–1444 | Move (internal). |
| `_render_serato_export_history` | 1446–1453 | Move (writes `serato_export_history_table`). |

**Stays in `MainWindow`:** the `serato_export_history` property/state, all widget
construction (L756–826), `serato_export_history_table` accessor, and the public
delegation wrappers above. `MainWindow.__init__` constructs
`self._export_coordinator = ExportCoordinator(host=self)`.

## Interfaces / Contracts

```python
class ExportCoordinator:
    """Qt-aware export orchestration extracted from MainWindow (first slice)."""

    def __init__(self, host: "MainWindow") -> None: ...

    def selected_software(self) -> str: ...

    def preview_export(
        self, *, serato_folder: Path | None = None,
        crate_name: str | None = None, generated_at: datetime | None = None,
    ) -> None: ...

    def export_recommendation(
        self, *, serato_folder: Path | None = None,
        crate_name: str | None = None, generated_at: datetime | None = None,
    ) -> None: ...

    def preview_serato_export(self, *, serato_folder=None, crate_name=None, generated_at=None) -> None: ...

    def export_recommendation_to_serato(self, *, serato_folder=None, crate_name=None, generated_at=None) -> None: ...

    def export_metadata_status_to_serato(
        self, *, status: str | None = None,
        missing_field: str | None = None, serato_folder: Path | None = None,
    ) -> None: ...
```

`host` exposes (already on `MainWindow`): `last_recommendation`,
`last_dj_readiness_report`, `last_quality_report`, `settings`,
`applied_prep_copilot_variant_name`, `status_label`, `export_guidance_label`,
`serato_export_history` (get/set), `serato_export_history_table`, `_export_screen`,
`_show_dj_readiness`, `_sync_state`, `_selected_metadata_status_filter`,
`_selected_missing_metadata_filter`, `_metadata_status_records`,
`_metadata_missing_field_records`, `tr`.

MainWindow delegation example:

```python
def export_recommendation(self, *, serato_folder=None, crate_name=None, generated_at=None) -> None:
    self._export_coordinator.export_recommendation(
        serato_folder=serato_folder, crate_name=crate_name, generated_at=generated_at,
    )
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|--------------|----------|
| Unit | Cache memoization, optimizer boundary | Items 3a–3c, pure functions. |
| Integration (Qt) | Thread-guard cancel, debounce, export delegation | Items 3d–3e + existing export suite re-run unchanged. |
| Regression | All `test_main_window.py` export assertions | Must pass via delegation; run full suite before/after Item 4. |

## Migration / Rollout

No migration. Only a factory default changes (Item 2); persisted user configs keep
their stored value. Each item is an independent commit; `git revert` restores prior
behavior.

## Open Questions

- [ ] Confirm `host` typing approach: `TYPE_CHECKING` import of `MainWindow` to avoid circular import (recommended). Resolve during apply.
