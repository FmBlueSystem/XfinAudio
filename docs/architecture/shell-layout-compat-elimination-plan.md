# Shell Layout Compatibility Elimination Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `gentle-ai-sdd-tdd` and strict RED -> GREEN -> VERIFY for every behavior-changing slice. Each slice must stay reviewable, create/update OpenSpec artifacts, merge with CI green, then archive in a docs-only PR before starting the next risky slice.

**Goal:** Remove all remaining methods from `src/xfinaudio/desktop/shell_layout_compat.py::LEGACY_LAYOUT_METHODS` until the graft map is empty or safely removable.

**Architecture:** Move each functional group from dynamic class grafting into explicit `MainWindow` methods, controller methods, coordinator methods, or screen wiring according to the real owner. `MainWindow` may temporarily expose thin delegators when direct callers still require the legacy method names, but product logic must live in controllers/coordinators/services, not in the compatibility surface.

**Tech Stack:** Python 3.11, PySide6, pytest, pyright, ruff, gentle-ai OpenSpec SDD/TDD.

---

## Current State

Last verified: 2026-06-20 on `main` at `3c1d9df`.

`LEGACY_LAYOUT_METHODS` remaining count: **34**.

Remaining methods:

```text
_open_settings_dialog
_on_spectral_cohesion_changed
scan_selected_folder
_begin_scan_state
_on_library_selection_changed
cancel_scan
show_tracks
generate_prep_copilot
_apply_prep_copilot_item
apply_selected_prep_copilot_variant
recommend_playlist
_begin_recommendation_state
_end_recommendation_state
_start_recommendation_worker
_finish_recommendation
_fail_recommendation
_populate_dj_readiness_table
_on_recommend_requested
_on_copilot_variant_applied
set_selected_folder
_persist_last_scan_folder
_populate_track_table
_apply_song_filter
_selected_metadata_status_filter
_selected_missing_metadata_filter
_metadata_status_records
_metadata_missing_field_records
restore_persisted_tracks
_start_spectral_completion_worker
_cancel_spectral_completion_worker
_on_spectral_progress_updated
_on_spectral_profile_ready
_on_spectral_completion_finished
_clear_scan_dependent_state
```

## Non-Negotiables

- No audio mutation.
- No DSP expansion.
- No live Serato DB V2 writes.
- No dependency changes unless separately approved.
- No monolithic PR that removes all 34 at once.
- Every slice must include RED evidence before production edits.
- Every implementation PR must pass CI before archive.
- Every archive PR must be docs/OpenSpec-only and pass CI.

## Slice Chain

### Slice 1: Settings shell methods explicit

**Count removed:** 2

**Methods:**
- `_open_settings_dialog`
- `_on_spectral_cohesion_changed`

**Owner:** `SettingsController`.

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Modify: `src/xfinaudio/desktop/shell_layout_compat.py`
- Modify: `tests/test_main_window_shell_compat.py`
- Modify: `docs/architecture/layered-architecture.md`
- Create: `openspec/changes/settings-shell-methods-explicit/`

**RED test:** Add `test_settings_shell_methods_are_explicit_main_window_methods` asserting both names are absent from `shell_layout_compat.LEGACY_LAYOUT_METHODS`, present in `MainWindow.__dict__`, and callable.

**GREEN implementation:** Add explicit `MainWindow` delegators:

```python
def _open_settings_dialog(self) -> None:
    self._settings_controller.open_settings_dialog()


def _on_spectral_cohesion_changed(self, value: int) -> None:
    self._settings_controller.on_spectral_cohesion_changed(value)
```

**Focused verification:**

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
```

---

### Slice 2: Scan entry shell methods explicit

**Count removed:** 4

**Methods:**
- `scan_selected_folder`
- `_begin_scan_state`
- `cancel_scan`
- `_clear_scan_dependent_state`

**Owner:** `ScanService`, `LibraryController`, existing scan-state helpers.

**Files:**
- Modify: `src/xfinaudio/desktop/main_window.py`
- Modify: `src/xfinaudio/desktop/shell_layout_compat.py`
- Modify: `tests/test_main_window_shell_compat.py`
- Create: `openspec/changes/scan-shell-methods-explicit/`

**RED test:** Assert the four selected names are explicit `MainWindow` methods and absent from the graft map.

**GREEN implementation:** Add thin `MainWindow` delegators to existing owners or layout helper functions only where no narrower owner exists yet. Do not move scan behavior into `MainWindow`.

---

### Slice 3: Library table shell methods explicit

**Count removed:** 7

**Methods:**
- `_on_library_selection_changed`
- `show_tracks`
- `set_selected_folder`
- `_persist_last_scan_folder`
- `_populate_track_table`
- `_apply_song_filter`
- `restore_persisted_tracks`

**Owner:** `LibraryController`, library screen/table rendering, settings persistence.

**RED test:** Assert selected names are absent from the graft map and explicit on `MainWindow`.

**GREEN implementation:** Prefer delegation to `LibraryController` where an equivalent method already exists. Keep table rendering in table/screen helpers, not compatibility glue.

---

### Slice 4: Metadata filter shell methods explicit

**Count removed:** 4

**Methods:**
- `_selected_metadata_status_filter`
- `_selected_missing_metadata_filter`
- `_metadata_status_records`
- `_metadata_missing_field_records`

**Owner:** Metadata screen/view-model boundary.

**RED test:** Assert selected names are explicit and absent from the graft map.

**GREEN implementation:** Delegate to metadata screen/view-model helpers. Keep filtering deterministic and tested.

---

### Slice 5: Prep Copilot shell methods explicit

**Count removed:** 3

**Methods:**
- `generate_prep_copilot`
- `_apply_prep_copilot_item`
- `apply_selected_prep_copilot_variant`

**Owner:** `PrepCopilotController`.

**RED test:** Assert selected names are explicit and absent from the graft map.

**GREEN implementation:** Delegate to `self._prep_copilot`.

---

### Slice 6: Recommendation shell methods explicit

**Count removed:** 8

**Methods:**
- `recommend_playlist`
- `_begin_recommendation_state`
- `_end_recommendation_state`
- `_start_recommendation_worker`
- `_finish_recommendation`
- `_fail_recommendation`
- `_populate_dj_readiness_table`
- `_on_recommend_requested`

**Owner:** `RecommendationService`, `DjReadinessController`, review/build screens.

**RED test:** Assert selected names are explicit and absent from the graft map.

**GREEN implementation:** Delegate to recommendation and readiness controllers/services. Keep recommendation product logic out of `MainWindow`.

---

### Slice 7: Copilot/recommendation bridge explicit

**Count removed:** 1

**Method:**
- `_on_copilot_variant_applied`

**Owner:** `PrepCopilotController` / recommendation bridge.

**Reason for separate slice:** This is a bridge between Copilot and recommendation state; keep isolated if Slice 6 grows too large.

---

### Slice 8: Spectral completion shell methods explicit

**Count removed:** 5

**Methods:**
- `_start_spectral_completion_worker`
- `_cancel_spectral_completion_worker`
- `_on_spectral_progress_updated`
- `_on_spectral_profile_ready`
- `_on_spectral_completion_finished`

**Owner:** `LibraryController` and `SpectralCompletionWorker` boundary.

**RED test:** Assert selected names are explicit and absent from the graft map.

**GREEN implementation:** Delegate to the spectral completion owner. Do not add DSP or audio mutation.

---

## Final Removal Slice

After all groups above are removed:

1. Assert `LEGACY_LAYOUT_METHODS == {}` or delete the map entirely.
2. Remove `install_legacy_layout_methods` if no call sites remain.
3. Remove `shell_layout_compat.py` and facade exports only if nothing imports them.
4. Update shell compatibility tests to assert the dynamic layout grafting surface is gone.
5. Archive final OpenSpec change.

## Verification Required Per Implementation PR

Run focused tests first, then full gates:

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

## Progress Tracker

- [ ] Slice 1: Settings shell methods explicit — removes 2, remaining 32.
- [ ] Slice 2: Scan entry shell methods explicit — removes 4, remaining 28.
- [ ] Slice 3: Library table shell methods explicit — removes 7, remaining 21.
- [ ] Slice 4: Metadata filter shell methods explicit — removes 4, remaining 17.
- [ ] Slice 5: Prep Copilot shell methods explicit — removes 3, remaining 14.
- [ ] Slice 6: Recommendation shell methods explicit — removes 8, remaining 6.
- [ ] Slice 7: Copilot/recommendation bridge explicit — removes 1, remaining 5.
- [ ] Slice 8: Spectral completion shell methods explicit — removes 5, remaining 0.
- [ ] Final removal slice: remove empty compatibility surface if safe.
