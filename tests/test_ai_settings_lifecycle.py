"""Exercise real Qt threads through the dialog with synthetic operations only."""

from threading import Event

import pytest
from PySide6.QtCore import QCoreApplication, QElapsedTimer, QEvent
from PySide6.QtTest import QTest

from xfinaudio.ai.connection_test import ConnectionStatus
from xfinaudio.config.settings import AiSettings, AppSettings
from xfinaudio.desktop.ai_connection_probe import _ACTIVE
from xfinaudio.desktop.settings_dialog import SettingsDialog


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "SYNTHETIC-ONLY")
    monkeypatch.setenv("NAN_API_BASE", "https://provider.invalid/chat")
    monkeypatch.setenv("HOME", str(tmp_path))


def wait_until(qapp, predicate):
    timer = QElapsedTimer()
    timer.start()
    while not predicate() and timer.elapsed() < 2000:
        qapp.processEvents()
        QTest.qWait(1)
    assert predicate()


@pytest.mark.parametrize("dismiss", ["reject", "close", "delete"])
def test_pending_thread_survives_dismissal_and_never_updates_closed_dialog(qapp, dismiss):
    entered, release = Event(), Event()
    dialog = SettingsDialog(AppSettings(ai=AiSettings(enabled=True)))
    panel = dialog._ai_panel

    def operation(settings):
        entered.set()
        release.wait(2)
        return ConnectionStatus("connected", "Stale result must not render")

    panel._probe._operation = operation
    results = []
    panel._probe.completed.connect(results.append)
    dialog.show()
    panel.test_button.click()
    assert entered.wait(1)
    thread = panel._probe._task
    assert thread in _ACTIVE
    if dismiss == "delete":
        dialog.reject()
        dialog.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    else:
        getattr(dialog, dismiss)()
        assert not dialog.isVisible()
    release.set()
    wait_until(qapp, lambda: thread not in _ACTIVE)
    assert results == []
    if dismiss != "delete":
        assert "Stale result" not in panel.status_label.text()


@pytest.mark.parametrize("failure", ["unavailable", "authentication_failed", "invalid_response"])
def test_retry_after_failure_uses_new_probe_without_restart(qapp, failure):
    dialog = SettingsDialog(AppSettings(ai=AiSettings(enabled=True)))
    panel = dialog._ai_panel
    responses = [ConnectionStatus(failure, "Retry available"), ConnectionStatus("connected", "Synthetic success")]
    panel._probe._operation = lambda _: responses.pop(0)
    panel.test_button.click()
    wait_until(qapp, lambda: not panel._probe.busy)
    assert panel.status_label.text() == "Retry available"
    assert panel.test_button.isEnabled()
    panel.test_button.click()
    wait_until(qapp, lambda: not panel._probe.busy)
    assert panel.status_label.text() == "Synthetic success"
    dialog.reject()
