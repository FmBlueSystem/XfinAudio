"""Actual Create confirmation controls never generate a plan themselves."""

from PySide6.QtCore import Qt
from PySide6.QtTest import QSignalSpy, QTest

from xfinaudio.desktop.screens.build_screen import BuildScreen
from xfinaudio.recommendation.prep_copilot import DJSetIntent


def test_create_preview_exposes_duration_style_constraints_before_confirmation(qapp):
    screen = BuildScreen()
    confirmed = QSignalSpy(screen.copilot_confirm_requested)
    intent = DJSetIntent(name="Opening", target_minutes=45, genre_focus="House", target_track_count=24)
    screen.intent_preview.show_intent(intent, "2 locked · 1 excluded · loudness -14 ± 0.5 LU")
    assert not screen.intent_preview.isHidden()
    assert screen.intent_preview.duration.value() == 45
    assert screen.intent_preview.genre.text() == "House"
    assert "2 locked" in screen.intent_preview.constraints.text()
    assert confirmed.count() == 0
    screen.intent_preview.duration.setValue(60)
    QTest.mouseClick(screen.intent_preview.confirm_button, Qt.MouseButton.LeftButton)
    assert confirmed.count() == 1
    assert confirmed.at(0)[0].target_minutes == 60
    assert screen.copilot_share_titles.isChecked() is False
    screen.close()


def test_create_preview_edit_cancel_and_configure_are_reachable(qapp):
    screen = BuildScreen()
    edit = QSignalSpy(screen.copilot_edit_requested)
    cancel = QSignalSpy(screen.copilot_cancel_requested)
    configure = QSignalSpy(screen.configure_ai_requested)
    screen.intent_preview.show_intent(DJSetIntent(name="Test"), "No constraints")
    screen.intent_preview.edit_button.click()
    screen.copilot_cancel_button.setEnabled(True)
    screen.copilot_cancel_button.click()
    screen.copilot_configure_button.click()
    assert (edit.count(), cancel.count(), configure.count()) == (1, 1, 1)
    screen.close()
