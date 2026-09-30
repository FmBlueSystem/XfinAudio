"""Direct queued-callback boundaries for partially initialized or deleted Qt UI."""

import pytest
from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QWidget
from shiboken6 import delete

from xfinaudio.desktop.screens.build_screen import BuildScreen


def test_layout_event_ignores_partially_initialized_screen(qapp):
    screen = BuildScreen.__new__(BuildScreen)
    QWidget.__init__(screen)
    assert not screen.eventFilter(QObject(), QEvent(QEvent.Type.LayoutRequest))
    screen._reveal_ai_response()


@pytest.mark.parametrize("attribute", ["controls_scroll", "copilot_ask_status", "intent_preview"])
def test_deferred_reveal_ignores_missing_child(qapp, attribute):
    screen = BuildScreen()
    child = getattr(screen, attribute)
    delattr(screen, attribute)
    try:
        screen._reveal_ai_response()
        assert not screen.eventFilter(QObject(), QEvent(QEvent.Type.LayoutRequest))
    finally:
        setattr(screen, attribute, child)
        screen.close()


@pytest.mark.parametrize("attribute", ["controls_scroll", "copilot_ask_status", "intent_preview"])
def test_deferred_reveal_ignores_deleted_child(qapp, attribute):
    screen = BuildScreen()
    delete(getattr(screen, attribute))
    screen._reveal_ai_response()
    assert not screen.eventFilter(QObject(), QEvent(QEvent.Type.LayoutRequest))
    screen.close()


def test_queued_reveal_after_screen_deletion_is_harmless(qapp):
    screen = BuildScreen()
    QTimer.singleShot(0, screen._reveal_ai_response)
    delete(screen)
    screen._reveal_ai_response()
    qapp.processEvents()
