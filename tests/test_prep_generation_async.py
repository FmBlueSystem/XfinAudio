"""Desktop Prep work must leave the GUI responsive and preserve a valid plan."""

import threading
import time

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from tests.test_build_screen import _plan_state, _track
from xfinaudio.desktop.main_window import MainWindow


def _wait(app: QApplication, predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert predicate()


def _window(tmp_path):
    window = MainWindow.with_defaults(tmp_path / "db.sqlite3", tmp_path / "settings.json")
    tracks = [_track("/a.flac"), _track("/b.flac")]
    window.show_tracks(tracks)
    window._on_library_selection_changed([tracks[0].path])
    window.workflow_tabs.setCurrentIndex(1)
    return window, tracks


def test_prep_generation_runs_off_gui_and_blocks_duplicate_requests(qapp, tmp_path):
    window, tracks = _window(tmp_path)
    started = threading.Event()
    release = threading.Event()
    called = []
    gui_thread = threading.get_ident()
    published = []
    publish = window._prep_task._publish
    window._prep_task._publish = lambda plan: (published.append(threading.get_ident()), publish(plan))[-1]
    ticks = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: ticks.append(True))
    timer.start()

    def slow(*args, **kwargs):
        called.append(threading.get_ident())
        started.set()
        release.wait(0.4)
        return _plan_state(tracks).last_prep_copilot_plan

    window._prep_copilot._plan_generation_builder = slow
    try:
        before = time.monotonic()
        window.generate_prep_copilot()
        assert time.monotonic() - before < 0.2
        _wait(qapp, started.is_set)
        window.generate_prep_copilot()
        _wait(qapp, lambda: len(ticks) >= 3)
        assert window._state.is_preparing_copilot
        assert not window._build_screen.copilot_button.isEnabled()
        release.set()
        _wait(qapp, lambda: not window._state.is_preparing_copilot)
        assert called == [called[0]] and called[0] != gui_thread
        assert window.last_prep_copilot_plan is not None
        assert published == [gui_thread]
    finally:
        release.set()
        timer.stop()
        window.close()
        _wait(qapp, lambda: window._prep_task._thread is None)


def test_failed_prep_preserves_previous_plan(qapp, tmp_path):
    window, tracks = _window(tmp_path)
    plan = _plan_state(tracks).last_prep_copilot_plan
    window._replace_app_state(window._state.model_copy(update={"last_prep_copilot_plan": plan}))

    def fail(*args, **kwargs):
        raise ValueError("synthetic failure")

    window._prep_copilot._plan_generation_builder = fail
    try:
        window.generate_prep_copilot()
        _wait(qapp, lambda: not window._state.is_preparing_copilot)
        assert window.last_prep_copilot_plan is plan
        assert "synthetic failure" in window.status_label.text()
    finally:
        window.close()
        _wait(qapp, lambda: window._prep_task._thread is None)


def test_cancel_then_retry_rejects_stale_result_and_progress(qapp, tmp_path):
    from PySide6.QtCore import QThread

    window, tracks = _window(tmp_path)
    prior = _plan_state(tracks).last_prep_copilot_plan
    assert prior is not None
    recommendation = prior.variants[0].recommendation
    newer = prior.model_copy(update={"intent": prior.intent.model_copy(update={"name": "retry"})})
    window._replace_app_state(
        window._state.model_copy(
            update={
                "last_prep_copilot_plan": prior,
                "last_recommendation": recommendation,
                "applied_variant_name": "safe",
            }
        )
    )
    started = threading.Event()
    release = threading.Event()

    def slow(*args, **kwargs):
        started.set()
        kwargs["checkpoint"]("safe")
        release.wait(2)
        # Simulate queued progress and a non-cooperative operation that finishes late.
        return prior

    window._prep_copilot._plan_generation_builder = slow
    try:
        window.generate_prep_copilot()
        _wait(qapp, started.is_set)
        _wait(qapp, lambda: "safe" in window._build_screen.prep_progress_label.text().lower())
        assert window._build_screen.prep_cancel_button.isEnabled()
        old_request = window._prep_task._request_id
        window._build_screen.prep_cancel_button.click()
        assert not window._state.is_preparing_copilot
        assert window.last_prep_copilot_plan is prior
        assert window.last_recommendation is recommendation
        assert window._state.applied_variant_name == "safe"
        assert "cancelled" in window.status_label.text()
        window._prep_copilot._plan_generation_builder = lambda *args, **kwargs: newer
        window.generate_prep_copilot()
        _wait(qapp, lambda: window.last_prep_copilot_plan is newer)
        window._prep_task.progress.emit("adventurous", old_request)
        window._prep_task.failed.emit(ValueError("stale failure"), old_request)
        release.set()
        _wait(qapp, lambda: not any(t.isRunning() for t in window.findChildren(QThread)))
        qapp.processEvents()
        assert window.last_prep_copilot_plan is newer
        assert not window._state.is_preparing_copilot
        assert not window._build_screen.prep_cancel_button.isEnabled()
        assert "adventurous" not in window._build_screen.prep_progress_label.text().lower()
        assert "stale failure" not in window.status_label.text()
    finally:
        release.set()
        window.close()
        _wait(qapp, lambda: not any(t.isRunning() for t in window.findChildren(QThread)))


def test_cancel_stops_candidate_work_before_builder(qapp, tmp_path):
    from PySide6.QtCore import QThread

    window, tracks = _window(tmp_path)
    started = threading.Event()
    release = threading.Event()
    calls = []

    def candidates(*args, **kwargs):
        started.set()
        release.wait(2)
        return tracks

    window._prep_copilot._candidate_routes_factory = lambda: (candidates, lambda *args, **kwargs: (tracks, None))
    window._prep_copilot._plan_generation_builder = lambda *args, **kwargs: calls.append(True)
    try:
        window.generate_prep_copilot()
        _wait(qapp, started.is_set)
        window._prep_task.cancel()
        release.set()
        _wait(qapp, lambda: not any(t.isRunning() for t in window.findChildren(QThread)))
        assert not calls
        assert window.last_prep_copilot_plan is None
    finally:
        release.set()
        window.close()
        _wait(qapp, lambda: not any(t.isRunning() for t in window.findChildren(QThread)))
