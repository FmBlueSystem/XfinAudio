"""State sync and render orchestration for the desktop shell."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QListWidget

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.metadata_view_model import MetadataViewModel
from xfinaudio.desktop.navigation import Navigation
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.screens import (
    BuildScreen,
    ExportScreen,
    LibraryScreen,
    LiveAssistantScreen,
    MetadataScreen,
    ReviewScreen,
)
from xfinaudio.desktop.workflow_stack import WorkflowStack
from xfinaudio.library.models import TrackRecord

# Upper bound on full-render frequency while progress events stream in. Long
# enough that a 7-thread analyzer cannot outrun the UI, short enough that
# progress still reads as live.
_SYNC_COALESCE_MS = 200


@dataclass(frozen=True)
class AppControllerScreens:
    library: LibraryScreen
    build: BuildScreen
    review: ReviewScreen
    export: ExportScreen
    metadata: MetadataScreen
    live_assistant: LiveAssistantScreen


@dataclass(frozen=True)
class AppControllerViewModels:
    library: LibraryViewModel
    build: BuildViewModel
    review: ReviewViewModel
    export: ExportViewModel
    metadata: MetadataViewModel


@dataclass(frozen=True)
class AppControllerStateAccess:
    settings: Callable[[], object]
    is_scanning: Callable[[], bool]
    is_recommending: Callable[[], bool]
    selected_library_paths: Callable[[], list[str]]
    records_by_path: Callable[[], dict[str, TrackRecord]]
    scanned_records: Callable[[], list[TrackRecord]]
    render_screens: Callable[[], None]


class AppController:
    def __init__(
        self,
        *,
        state: AppState,
        nav: Navigation,
        workflow_tabs: WorkflowStack,
        workflow_sidebar: QListWidget,
        screen_names: Sequence[str],
        screens: AppControllerScreens,
        view_models: AppControllerViewModels,
        access: AppControllerStateAccess,
    ) -> None:
        self._state = state
        self._nav = nav
        self._workflow_tabs = workflow_tabs
        self._workflow_sidebar = workflow_sidebar
        self._screen_names = screen_names
        self._screens = screens
        self._view_models = view_models
        self._access = access
        self._current_tab_index = workflow_tabs.currentIndex()
        self._sync_timer = QTimer()
        self._sync_timer.setSingleShot(True)
        self._sync_timer.setInterval(_SYNC_COALESCE_MS)
        # Late-bound on purpose so tests can patch sync_state.
        self._sync_timer.timeout.connect(lambda: self.sync_state())

    def request_sync(self) -> None:
        """Ask for a render, coalescing bursts into at most one per interval.

        For high-frequency callers (per-file scan progress, per-track spectral
        results). Throttles rather than debounces: the timer is left running if
        already armed, so a continuous burst still refreshes every interval
        instead of starving until it stops.

        Terminal transitions must call ``sync_state`` directly, so the final
        state is never left waiting on a timer.
        """
        if not self._sync_timer.isActive():
            self._sync_timer.start()

    def sync_state(self) -> None:
        self.refresh_state_fields()
        self._screens.live_assistant.set_library_state(self._access.records_by_path(), self._access.scanned_records())
        self._access.render_screens()

    def render_screens(self) -> None:
        current = self._current_tab_index
        for index in (0, 1, 2, 3, 5):
            self.render_tab(index, lightweight=index != current)
        self.update_tab_states()

    def render_tab(self, index: int, lightweight: bool = False) -> None:
        renderers = {
            0: lambda: self._screens.library.render(self._view_models.library, self._state, lightweight=True),
            1: lambda: self._screens.build.render(self._view_models.build, self._state, lightweight=lightweight),
            2: lambda: self._screens.review.render(self._view_models.review, self._state, lightweight=lightweight),
            3: lambda: self._screens.export.render(self._view_models.export, self._state),
            5: lambda: self._screens.metadata.render(self._state, self._view_models.metadata, lightweight=lightweight),
        }
        render = renderers.get(index)
        if render is not None:
            render()

    def refresh_state_fields(self) -> None:
        tab_index = self._workflow_tabs.currentIndex()
        self._state.settings = self._access.settings()
        self._state.is_scanning = self._access.is_scanning()
        self._state.is_recommending = self._access.is_recommending()
        self._state.current_screen = (
            self._screen_names[tab_index] if 0 <= tab_index < len(self._screen_names) else "library"
        )
        self._state.selected_library_paths = list(self._access.selected_library_paths())

    def on_tab_changed(self, index: int) -> None:
        self._current_tab_index = index
        self.refresh_state_fields()
        self.render_tab(index)

    def update_tab_states(self) -> None:
        for index, screen_name in enumerate(self._screen_names):
            enabled = self._nav.can_go_to(screen_name, self._state)
            self._workflow_tabs.setTabEnabled(index, enabled)
            screen = self._workflow_tabs.widget(index)
            if screen is not None:
                screen.setEnabled(enabled)
            item = self._workflow_sidebar.item(index)
            if item is not None:
                flags = item.flags() | Qt.ItemFlag.ItemIsEnabled
                if not enabled:
                    flags &= ~Qt.ItemFlag.ItemIsEnabled
                item.setFlags(flags)
