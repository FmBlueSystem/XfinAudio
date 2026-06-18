## Why

After the lean-refactor chain (PRs #72–#77), `main_window.py` is 1096 LOC — still
the largest file in the codebase and the only one over the 400-line review budget.
The previous slice (PR 5) extracted 10 helper modules. What remains is the genuine
coordination logic: state sync + render orchestration, library state management
(folder + spectral + restore), settings dialog, and DJ readiness display. These
are independent concerns glued together by `MainWindow`.

## What changes

Extract 4 controllers from `MainWindow` and replace the in-class methods with
one-line delegations:

### New modules (4)

1. **`desktop/app_controller.py`** — `AppController` class (~140 LOC). Owns the
   state-sync and render-orchestration logic that currently lives in
   `_sync_state`, `_render_screens`, `_render_tab`, `_refresh_state_fields`,
   `_on_tab_changed`, `_update_tab_states`. The controller is constructed with
   the screens, view models, and navigation; the MainWindow calls
   `self._app_controller.sync_state()` etc. The 15 property accessors STAY on
   MainWindow (PR 7 will move them).

2. **`desktop/library_controller.py`** — `LibraryController` class (~280 LOC).
   Owns the library state actions: `choose_folder`, `set_selected_folder`,
   `_populate_track_table`, `_apply_song_filter`, `_selected_metadata_status_filter`,
   `_selected_missing_metadata_filter`, `_metadata_status_records`,
   `_metadata_missing_field_records`, `restore_persisted_tracks`,
   `_on_library_selection_changed`, `_refresh_idle_action_state`, `show_tracks`,
   `_start_spectral_completion_worker`, `_cancel_spectral_completion_worker`,
   `_on_spectral_progress_updated`, `_on_spectral_profile_ready`,
   `_on_spectral_completion_finished`. Constructor takes the workflow_service,
   repository, screens, state, and the `app_controller` (for sync_state
   callbacks).

3. **`desktop/settings_controller.py`** (replaces the file deleted in PR 4) —
   `SettingsController` class (~80 LOC). Owns `_open_settings_dialog`,
   `_on_spectral_cohesion_changed`, `_apply_settings`,
   `_format_safe_export_folder_label`. Constructor takes the settings
   repository, the export screen, the app_controller, the tr callable, and a
   reference to MainWindow for the language-change message box.

4. **`desktop/dj_readiness_controller.py`** — `DjReadinessController` class
   (~70 LOC). Owns `_show_dj_readiness` and `_populate_dj_readiness_table`.

### MainWindow shims

Each extracted method becomes a one-line shim:

```python
# before
def choose_folder(self) -> None:
    folder = QFileDialog.getExistingDirectory(self, self.tr("Choose music folder"))
    if folder:
        self.set_selected_folder(Path(folder))

# after
def choose_folder(self) -> None:
    self._library_controller.choose_folder()
```

The signal wiring in `_connect_widget_signals` does NOT change — it still
connects to the `MainWindow.choose_folder` shim, which forwards to the
controller. This is the same pattern PR 5 used for `ExportActions` and
`PrepCopilotController`.

## Non-goals

- Moving the 15 property accessors to `AppState`. That is PR 7.
- Splitting `MainWindow` into `MainWindowShell` + `App`. The class name stays.
- Renaming any public method on `MainWindow`.
- Changing the test suite beyond import path updates.

## Impact

- Net: ~63 LOC moved out of `main_window.py`; new main_window: ~1033 LOC. The original estimate of 570 LOC was based on counting the LOC of the original MainWindow methods, but most extracted methods were smaller than estimated (the LibraryController bundle is a single dependency dataclass plus 17 small methods, totaling 340 LOC including class boilerplate). The architectural win is real: 4 controllers with explicit dependency injection and no Protocol-with-one-impl host. The LOC win is smaller than expected; PR 7 will recover more by moving the 15 property accessors to AppState.
- 4 new controller modules in `src/xfinaudio/desktop/`.
- Review budget: this PR exceeds 400-line cap on changed lines (4 new files + ~600 LOC of additions + main_window.py modification). The behavior is unchanged; this is the same kind of large-but-mechanical refactor as PR 5.
- Risk: medium. The 4 controllers are each independent and have explicit
  dependencies. Strict TDD applies: the 848-test suite is the contract.

## Follow-up

PR 7 (`refactor/slice-mainwindow-residual`) will move the 15 property
accessors from `MainWindow` to `AppState`, updating all 50+ call sites, to
finally bring `main_window.py` under the 400-line budget.
