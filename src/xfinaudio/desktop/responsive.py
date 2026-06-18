"""Responsive resize behavior for MainWindow."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

_SIDEBAR_WIDTH_NARROW = 120


class ResponsiveLayout:
    def __init__(
        self,
        sidebar_panel: Any,
        sidebar_list: Any,
        label_list: list[str],
        width_for: Callable[[int], int],
    ) -> None:
        self._sidebar_panel = sidebar_panel
        self._sidebar_list = sidebar_list
        self._labels = label_list
        self._width_for = width_for
        self._status_widgets: tuple[Any, ...] = ()
        self._window: Any | None = None

    def set_full_screen_context(self, window: Any, status_widgets: tuple[Any, ...]) -> None:
        self._window = window
        self._status_widgets = status_widgets

    def apply(self, window_width: int) -> None:
        sidebar_width = self._width_for(window_width)
        self._sidebar_panel.setFixedWidth(sidebar_width)
        self._sidebar_list.setFixedWidth(sidebar_width)
        collapsed = sidebar_width == _SIDEBAR_WIDTH_NARROW
        for index in range(self._sidebar_list.count()):
            item = self._sidebar_list.item(index)
            if item is not None:
                item.setText("" if collapsed else self._labels[index])

    def set_full_screen(self, enabled: bool) -> None:
        self._sidebar_panel.setHidden(enabled)
        for widget in self._status_widgets:
            widget.setHidden(enabled)
        if self._window is not None:
            if enabled:
                self._window.showFullScreen()
            else:
                self._window.showNormal()
