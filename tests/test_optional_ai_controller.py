"""Real Qt events exercise explicit opt-in and bounded synthetic workers."""

from threading import Event
from time import sleep

from PySide6.QtCore import QCoreApplication, QEvent, QThread
from PySide6.QtWidgets import QLineEdit

from xfinaudio.desktop.optional_ai_assist import OptionalAssistController, OptionalAssistPanel


def wait(qapp, predicate):
    for _ in range(1500):
        qapp.processEvents()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        if predicate():
            return
        sleep(0.002)
    assert predicate()


def setup(qapp, operation, context=lambda: ()):
    panel, request = OptionalAssistPanel("Request only"), QLineEdit("help")
    results, called, configured = [], [], []
    enabled = [False]

    def prepare(text):
        assert QThread.currentThread() == qapp.thread()
        called.append(text)
        return operation, lambda result: results.append((result, QThread.currentThread()))

    controller = OptionalAssistController(
        panel,
        request,
        prepare=prepare,
        context=context,
        enabled=lambda: enabled[0],
        configure=lambda: configured.append(True),
    )
    return controller, panel, request, results, called, configured, enabled


def drain(qapp, controller):
    wait(qapp, lambda: not controller.findChildren(QThread))


def test_no_transmission_without_both_opt_ins_and_explicit_click(qapp, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    c, panel, request, results, calls, configured, enabled = setup(qapp, lambda: "ok")
    assert not panel.consent.isChecked()
    request.setText("changed")
    panel.ask_button.click()
    assert not calls
    panel.consent.setChecked(True)
    panel.ask_button.click()
    assert not calls and "Configure AI" in panel.status.text()
    panel.configure_button.click()
    assert configured == [True]
    enabled[0] = True
    panel.ask_button.click()
    wait(qapp, lambda: bool(results))
    assert calls == ["changed"]
    assert results == [("ok", qapp.thread())]
    drain(qapp, c)


def test_cancel_retry_retains_old_worker_and_rejects_old_delivery(qapp):
    entered, release = Event(), Event()
    attempts = []

    def operation():
        attempts.append(len(attempts))
        if len(attempts) == 1:
            entered.set()
            assert release.wait(2)
            return "old"
        return "new"

    c, panel, _, results, calls, _, enabled = setup(qapp, operation)
    enabled[0] = True
    panel.consent.setChecked(True)
    panel.ask_button.click()
    assert entered.wait(1)
    panel.ask_button.click()
    assert len(calls) == 1
    panel.cancel_button.click()
    panel.ask_button.click()
    wait(qapp, lambda: bool(results))
    assert results[0][0] == "new"
    assert any(t.isRunning() for t in c.findChildren(QThread))
    release.set()
    drain(qapp, c)
    assert len(results) == 1


def test_changed_context_or_request_and_revoked_consent_reject_results(qapp):
    for change in ("context", "request", "consent"):
        release, context = Event(), [1]
        c, panel, request, results, _, _, enabled = setup(
            qapp, lambda release=release: (release.wait(2), "old")[1], lambda context=context: tuple(context)
        )
        enabled[0] = True
        panel.consent.setChecked(True)
        panel.ask_button.click()
        if change == "context":
            context.append(2)
        elif change == "request":
            request.setText("new")
        else:
            panel.consent.setChecked(False)
        release.set()
        drain(qapp, c)
        assert not results and not c.busy


def test_failure_is_actionable_without_echoing_raw_exception(qapp):
    def operation():
        raise RuntimeError("SYNTHETIC_SECRET")

    c, panel, _, _, _, _, enabled = setup(qapp, operation)
    enabled[0] = True
    panel.consent.setChecked(True)
    panel.ask_button.click()
    drain(qapp, c)
    assert "retry" in panel.status.text().lower()
    assert "SYNTHETIC_SECRET" not in panel.status.text()
