"""Thread lifecycle uses bounded fake operations; no network or credentials."""

from threading import Event

from PySide6.QtCore import QElapsedTimer
from PySide6.QtTest import QTest

from xfinaudio.ai.connection_test import ConnectionStatus
from xfinaudio.config.settings import AiSettings
from xfinaudio.desktop.ai_connection_probe import ConnectionProbe


def wait_until(qapp, predicate):
    timer = QElapsedTimer()
    timer.start()
    while not predicate() and timer.elapsed() < 2000:
        qapp.processEvents()
        QTest.qWait(1)
    assert predicate()


def test_probe_runs_off_ui_thread_and_rejects_duplicate_clicks(qapp):
    entered, release = Event(), Event()

    def operation(settings):
        entered.set()
        assert release.wait(2)
        return ConnectionStatus("connected", "Safe result")

    probe = ConnectionProbe(operation=operation)
    results, states = [], []
    probe.completed.connect(results.append)
    probe.busy_changed.connect(states.append)
    assert probe.start(AiSettings(enabled=True))
    assert entered.wait(1)
    assert probe.busy
    assert not probe.start(AiSettings(enabled=True))
    assert results == []
    release.set()
    wait_until(qapp, lambda: not probe.busy)
    assert [result.state for result in results] == ["connected"]
    assert states == [True, False]


def test_cancel_ignores_old_result_and_allows_retry_after_completion(qapp):
    release = Event()

    def operation(settings):
        release.wait(2)
        return ConnectionStatus("connected", "Safe result")

    probe = ConnectionProbe(operation=operation)
    results = []
    probe.completed.connect(results.append)
    probe.start(AiSettings(enabled=True))
    probe.cancel()
    release.set()
    wait_until(qapp, lambda: not probe.busy)
    assert results == []
    assert probe.start(AiSettings(enabled=True))
    wait_until(qapp, lambda: not probe.busy)
    assert len(results) == 1


def test_unexpected_failure_never_renders_raw_exception(qapp):
    def operation(settings):
        raise RuntimeError("SYNTHETIC-SECRET")

    probe = ConnectionProbe(operation=operation)
    results = []
    probe.completed.connect(results.append)
    probe.start(AiSettings(enabled=True))
    wait_until(qapp, lambda: not probe.busy)
    assert results[0].state == "unavailable"
    assert "SYNTHETIC-SECRET" not in results[0].message


def test_destroyed_owner_does_not_destroy_running_thread(qapp):
    from PySide6.QtCore import QCoreApplication, QEvent

    release = Event()
    probe = ConnectionProbe(operation=lambda _: (release.wait(2), ConnectionStatus("connected", "ok"))[1])
    probe.start(AiSettings(enabled=True))
    probe.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    release.set()
    QTest.qWait(30)
    qapp.processEvents()
