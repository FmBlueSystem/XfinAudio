# Design: Slice main_window shell

## Approach

Four controller classes, each with explicit constructor injection. Each
extracted MainWindow method becomes a one-line shim. The signal wiring
`_connect_widget_signals` keeps the same shape — it still connects to
`MainWindow.<method>`, and the shim forwards to the controller.

This is the same pattern used by PR 4 for `ExportActions` and
`PrepCopilotController`, and by PR 5 for the 10 helper modules. The
behavior is unchanged; the test suite is the contract.

## Files affected

### New files (4)

| Path | LOC target | Source |
|------|------------|--------|
| `src/xfinaudio/desktop/app_controller.py` | ~140 | `_sync_state`, `_render_screens`, `_render_tab`, `_refresh_state_fields`, `_on_tab_changed`, `_update_tab_states` |
| `src/xfinaudio/desktop/library_controller.py` | ~280 | 17 library methods (folder, table, filter, restore, spectral) |
| `src/xfinaudio/desktop/settings_controller.py` | ~80 | 4 settings methods (open dialog, apply, cohesion) |
| `src/xfinaudio/desktop/dj_readiness_controller.py` | ~70 | 2 readiness methods (show, populate table) |

### Modified files (1)

| Path | Change |
|------|--------|
| `src/xfinaudio/desktop/main_window.py` | -570 LOC (extracted method bodies), +60 LOC of shims and construction → net -510 LOC |

## Public API of the new controllers

```python
# app_controller.py
class AppController:
    def __init__(
        self,
        *,
        state: AppState,
        nav: Navigation,
        workflow_tabs: WorkflowStack,
        workflow_sidebar: QListWidget,
        screen_names: list[str],
        library_screen: LibraryScreen,
        build_screen: BuildScreen,
        review_screen: ReviewScreen,
        export_screen: ExportScreen,
        metadata_screen: MetadataScreen,
        live_assistant_screen: LiveAssistantScreen,
        library_vm: LibraryViewModel,
        build_vm: BuildViewModel,
        review_vm: ReviewViewModel,
        export_vm: ExportViewModel,
        metadata_vm: MetadataViewModel,
        on_live_assistant_state_changed: Callable[[dict, list], None],
    ) -> None: ...
    def sync_state(self) -> None: ...
    def render_screens(self) -> None: ...
    def render_tab(self, index: int, lightweight: bool = False) -> None: ...
    def refresh_state_fields(self) -> None: ...
    def on_tab_changed(self, index: int) -> None: ...
    def update_tab_states(self) -> None: ...

# library_controller.py
class LibraryController:
    def __init__(
        self,
        *,
        state: AppState,
        workflow_service: PlaylistWorkflowService,
        library_screen: LibraryScreen,
        metadata_screen: MetadataScreen,
        folder_label: QLabel,
        library_guidance_label: QLabel,
        recommendation_guidance_label: QLabel,
        status_label: QLabel,
        audio_player: AudioPlayer,
        library_selected_paths: list[str],
        pre_scan_records_by_path: dict[str, TrackRecord],
        sync_state: Callable[[], None],
        table_populator: Callable[[list[TrackRecord]], None],
        render_main_song_filter: Callable[..., None],
        tr: Callable[[str], str],
        log: logging.Logger,
        parent: QWidget | None = None,
    ) -> None: ...
    def choose_folder(self) -> None: ...
    def set_selected_folder(self, folder: Path) -> None: ...
    def populate_track_table(self, records: list[TrackRecord]) -> None: ...
    def apply_song_filter(self, query: str | None = None, *, clear_selection: bool = False) -> None: ...
    def selected_metadata_status_filter(self) -> str | None: ...
    def selected_missing_metadata_filter(self) -> str | None: ...
    def metadata_status_records(self, status: str) -> list[TrackRecord]: ...
    def metadata_missing_field_records(self, missing_field: str) -> list[TrackRecord]: ...
    def restore_persisted_tracks(self, records: list[TrackRecord]) -> None: ...
    def on_library_selection_changed(self, paths: list[str]) -> None: ...
    def refresh_idle_action_state(self) -> None: ...
    def show_tracks(self, records, complete_count=None, incomplete_count=None) -> None: ...
    def start_spectral_completion_worker(self, records: list[TrackRecord]) -> None: ...
    def cancel_spectral_completion_worker(self) -> None: ...
    # spectral slots
    def on_spectral_progress_updated(self, processed: int, total: int) -> None: ...
    def on_spectral_profile_ready(self, path: str, profile: object) -> None: ...
    def on_spectral_completion_finished(self) -> None: ...
    def clear_scan_dependent_state(self) -> None: ...

# settings_controller.py
class SettingsController:
    def __init__(
        self,
        *,
        settings_getter: Callable[[], AppSettings],
        settings_setter: Callable[[AppSettings], None],
        settings_repository: SettingsPersistence | None,
        export_screen: ExportScreen,
        format_safe_export_folder_label: Callable[[], str],
        sync_state: Callable[[], None],
        tr: Callable[[str], str],
        message_parent: QWidget,
    ) -> None: ...
    def open_settings_dialog(self) -> None: ...
    def on_spectral_cohesion_changed(self, value: int) -> None: ...
    def apply_settings(self, new_settings: AppSettings) -> None: ...
    def format_safe_export_folder_label(self) -> str: ...

# dj_readiness_controller.py
class DjReadinessController:
    def __init__(
        self,
        *,
        state: AppState,
        review_screen: ReviewScreen,
        sync_state: Callable[[], None],
        last_report_setter: Callable[[DjReadinessReport | None], None],
        tr: Callable[[str], str],
    ) -> None: ...
    def show(self, recommendation, quality_report, *, serato_plan=None, serato_volume_root=None) -> None: ...
    def populate_table(self, report: DjReadinessReport) -> None: ...
```

## MainWindow changes

### Construction

```python
# in _initialize_window_state, after the screens and view models are created:
self._app_controller = AppController(
    state=self._state,
    nav=self._nav,
    workflow_tabs=self.workflow_tabs,
    workflow_sidebar=self.workflow_sidebar,
    screen_names=_SCREEN_NAMES,
    library_screen=self._library_screen,
    build_screen=self._build_screen,
    review_screen=self._review_screen,
    export_screen=self._export_screen,
    metadata_screen=self._metadata_screen,
    live_assistant_screen=self._live_assistant_screen,
    library_vm=self._library_vm,
    build_vm=self._build_vm,
    review_vm=self._review_vm,
    export_vm=self._export_vm,
    metadata_vm=self._metadata_vm,
    on_live_assistant_state_changed=self._live_assistant_screen.set_library_state,
)
self._library_controller = LibraryController(
    state=self._state,
    workflow_service=self.workflow_service,
    library_screen=self._library_screen,
    metadata_screen=self._metadata_screen,
    folder_label=self.folder_label,
    library_guidance_label=self.library_guidance_label,
    recommendation_guidance_label=self.recommendation_guidance_label,
    status_label=self.status_label,
    audio_player=self._audio_player,
    library_selected_paths=self._library_selected_paths,
    pre_scan_records_by_path=self._pre_scan_records_by_path,
    sync_state=self._sync_state,
    table_populator=self._populate_track_table,
    render_main_song_filter=self._apply_song_filter,
    tr=self.tr,
    log=LOGGER,
    parent=self,
)
self._settings_controller = SettingsController(
    settings_getter=lambda: self.settings,
    settings_setter=lambda value: setattr(self, "settings", value),
    settings_repository=self.settings_repository,
    export_screen=self._export_screen,
    format_safe_export_folder_label=self._format_safe_export_folder_label,
    sync_state=self._sync_state,
    tr=self.tr,
    message_parent=self,
)
self._dj_readiness_controller = DjReadinessController(
    state=self._state,
    review_screen=self._review_screen,
    sync_state=self._sync_state,
    last_report_setter=lambda value: setattr(self, "last_dj_readiness_report", value),
    tr=self.tr,
)
```

### Shim methods

Each extracted MainWindow method becomes a one-line shim:

```python
def choose_folder(self) -> None:
    self._library_controller.choose_folder()

def set_selected_folder(self, folder: Path) -> None:
    self._library_controller.set_selected_folder(folder)

def restore_persisted_tracks(self, records: list[TrackRecord]) -> None:
    self._library_controller.restore_persisted_tracks(records)

def show_tracks(self, records, complete_count=None, incomplete_count=None) -> None:
    self._library_controller.show_tracks(records, complete_count, incomplete_count)

# ... etc for all 17 library methods, 6 app controller methods,
# 4 settings methods, 2 readiness methods.
```

## Step-by-step

1. Pre-flight: `git status` clean; 848 tests pass.
2. Create `app_controller.py`. Update `main_window.py` to construct it and
   replace the 6 sync/render methods with shims. Run `pytest -q`. Green.
3. Create `library_controller.py`. Update `main_window.py`. Run `pytest -q`.
   Green.
4. Create `settings_controller.py` (a fresh file, not the one deleted in
   PR 4). Update `main_window.py`. Run `pytest -q`. Green.
5. Create `dj_readiness_controller.py`. Update `main_window.py`. Run
   `pytest -q`. Green.
6. Run full verify: pytest, ruff, pyright, hygiene check.
7. `wc -l src/xfinaudio/desktop/main_window.py` is under 600.
8. Single work-unit commit: `refactor(desktop): extract 4 controllers from main_window`.
9. Push. Open PR.

## Risks

- **Setter explosion**: each controller takes many explicit dependencies. The
  LibraryController has 14 constructor parameters. This is a lot, but they
  are all genuinely needed (state, services, screens, labels, callbacks).
  The alternative is a Protocol-with-one-impl host, which is the YAGNI this
  refactor is removing. If a controller needs more than 15 constructor
  parameters, STOP and report.
- **State sharing**: the LibraryController mutates `self._library_selected_paths`
  and `self._pre_scan_records_by_path` on MainWindow (via the references
  passed in). This is a minor leak, but the references are private and
  documented in the controller's docstring. PR 7 can move these to AppState
  if desired.
- **Circular imports**: the controllers import from `xfinaudio.quality.*`,
  `xfinaudio.library.*`, etc. None of these import from `desktop.*`, so no
  cycles.

## Rollback

Single `git revert <commit-sha>` restores the previous state.
