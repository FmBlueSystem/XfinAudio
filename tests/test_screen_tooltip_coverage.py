"""Every screen explains its buttons, not just half of them."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QApplication, QPushButton

from xfinaudio.desktop.screens.build_screen import BuildScreen
from xfinaudio.desktop.screens.export_screen import ExportScreen
from xfinaudio.desktop.screens.live_assistant_screen import LiveAssistantScreen
from xfinaudio.desktop.screens.metadata_screen import MetadataScreen
from xfinaudio.desktop.screens.my_playlists_screen import MyPlaylistsScreen
from xfinaudio.desktop.screens.playlist_editor import PlaylistEditor
from xfinaudio.desktop.screens.review_screen import ReviewScreen

_SCREENS = [
    BuildScreen,
    ExportScreen,
    LiveAssistantScreen,
    MetadataScreen,
    MyPlaylistsScreen,
    PlaylistEditor,
    ReviewScreen,
]


@pytest.mark.parametrize("screen_class", _SCREENS, ids=lambda cls: cls.__name__)
def test_every_button_has_a_tooltip(qapp: QApplication, screen_class: type) -> None:
    """Build, Export, Library and Review already did this; four screens did not.

    17 of 32 buttons carried a tooltip. The worst were three buttons labelled
    only "▶" on the Live Assistant: ambiguous on screen and unreadable to a
    screen reader.
    """
    screen = screen_class()

    buttons = screen.findChildren(QPushButton)
    assert buttons, f"{screen_class.__name__} exposes no buttons to check"
    missing = [
        button.text() or button.accessibleName() or "<unlabelled>" for button in buttons if not button.toolTip().strip()
    ]
    assert missing == [], f"{screen_class.__name__} buttons without a tooltip: {missing}"
