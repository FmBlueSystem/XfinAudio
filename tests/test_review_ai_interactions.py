"""Real Review widget/controller interactions with offline worker seams."""

from typing import Any

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tests.test_ai_narrator_controller import NARRATIVE, _Harness, _ready_state, _track
from xfinaudio.ai import narrate_set
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.screens.review_screen import ReviewScreen


def _widgets(harness: _Harness) -> ReviewScreen:
    screen = ReviewScreen()
    harness.controller._review_screen = screen
    harness.controller._review_vm = ReviewViewModel()
    screen.ai_narrate_requested.connect(harness.controller.narrate)
    screen.ai_narrate_cancel_requested.connect(harness.controller.cancel)
    screen.render(ReviewViewModel(), harness.host._state)
    screen.show()
    return screen


def test_disabled_narrator_recovery_uses_real_widgets_without_transport(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "0")
    harness = _Harness(monkeypatch, narrator=narrate_set)
    screen = _widgets(harness)
    configured: list[bool] = []
    screen.configure_ai_requested.connect(lambda: configured.append(True))
    QTest.mouseClick(screen.ai_narrate_button, Qt.MouseButton.LeftButton)
    assert not screen.ai_narrate_button.isEnabled()
    assert screen.ai_narrate_cancel_button.isVisibleTo(screen)
    harness.run()
    assert "Configure AI" in screen.ai_narrate_status.text()
    assert screen.ai_narrate_button.isEnabled()
    QTest.mouseClick(screen.configure_ai_button, Qt.MouseButton.LeftButton)
    assert configured == [True]

    def fake_narrator(*_args: Any, **_kwargs: Any) -> str:
        return NARRATIVE

    harness.controller._narrator = fake_narrator
    QTest.mouseClick(screen.ai_narrate_button, Qt.MouseButton.LeftButton)
    harness.run(1)
    assert screen.ai_narrative_label.text() == NARRATIVE
    assert "AI-generated commentary" in screen.ai_narrate_status.text()
    screen.ai_narrate_requested.disconnect(harness.controller.narrate)
    screen.ai_narrate_cancel_requested.disconnect(harness.controller.cancel)
    harness.controller.deleteLater()
    screen.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_real_cancel_and_set_switch_do_not_show_stale_narration(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    harness = _Harness(monkeypatch)
    screen = _widgets(harness)
    QTest.mouseClick(screen.ai_narrate_button, Qt.MouseButton.LeftButton)
    QTest.mouseClick(screen.ai_narrate_cancel_button, Qt.MouseButton.LeftButton)
    assert screen.ai_narrate_button.isEnabled()
    harness.run()
    assert screen.ai_narrative_label.text() == ""
    QTest.mouseClick(screen.ai_narrate_button, Qt.MouseButton.LeftButton)
    harness.host._state = _ready_state([_track("/new-a"), _track("/new-b")])
    harness.controller.invalidate_if_context_changed()
    screen.render(ReviewViewModel(), harness.host._state)
    harness.run(1)
    assert screen.ai_narrative_label.text() == ""
    assert screen.ai_narrate_button.isEnabled()
    screen.ai_narrate_requested.disconnect(harness.controller.narrate)
    screen.ai_narrate_cancel_requested.disconnect(harness.controller.cancel)
    harness.controller.deleteLater()
    screen.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
