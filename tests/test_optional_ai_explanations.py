"""Explanation requests expose bounded current evidence, never library identity."""

from threading import Event
from types import SimpleNamespace
from unittest.mock import MagicMock

from tests.test_ai_narrator_controller import _readiness
from tests.test_live_assistance import _set
from tests.test_optional_ai_controller import drain
from tests.test_optional_ai_library_editor import host
from xfinaudio.desktop.optional_ai_explanations import install_explanation_controls
from xfinaudio.desktop.screens.live_assistant_screen import LiveAssistantScreen
from xfinaudio.desktop.screens.metadata_screen import MetadataScreen
from xfinaudio.library.models import TrackRecord


def setup(qapp, tmp_path, monkeypatch):
    window = host(qapp, tmp_path, monkeypatch)
    window._metadata_screen = MetadataScreen()
    window._live_assistant_screen = LiveAssistantScreen()
    services = SimpleNamespace(explain_grounded_evidence=MagicMock(return_value="<b>Verify supplied facts</b>"))
    controls = install_explanation_controls(window, services=services)
    return window, services, controls


def ask(controller):
    controller.panel.consent.setChecked(True)
    controller.panel.ask_button.click()


def test_metadata_sends_counts_only_and_never_fills_missing_values(qapp, tmp_path, monkeypatch):
    window, services, controls = setup(qapp, tmp_path, monkeypatch)
    window.scanned_records = [TrackRecord(path="/private/secret.mp3", title="Private", bpm=None)]
    window._state = window._state.model_copy(update={"locked_paths": frozenset({"/private/secret.mp3"})})
    controller = controls["metadata"]
    ask(controller)
    drain(qapp, controller)
    kind, facts = services.explain_grounded_evidence.call_args.args
    assert kind == "metadata"
    assert facts == [
        {"id": "m0", "track_count": 1, "missing_bpm": 1, "missing_key": 1, "missing_energy": 1, "locked_with_gaps": 1}
    ]
    assert "private" not in repr(facts).lower()
    assert window.scanned_records[0].bpm is None
    assert "<b>" in controller.panel.commentary.toPlainText()
    assert controller.panel.commentary.isReadOnly()
    window.scanned_records = []
    controller.invalidate_if_context_changed()
    assert not controller.panel.commentary.toPlainText()


def test_live_shares_actual_metrics_and_does_not_change_order(qapp, tmp_path, monkeypatch):
    window, services, controls = setup(qapp, tmp_path, monkeypatch)
    screen = window._live_assistant_screen
    recommendation = _set()
    assert screen.set_session(recommendation, _readiness())
    before = list(screen._ranked_candidates)
    controller = controls["live"]
    ask(controller)
    drain(qapp, controller)
    kind, facts = services.explain_grounded_evidence.call_args.args
    assert kind == "live" and facts[0]["id"] == "c0"
    assert facts[0]["score"] == before[0].score.total_score
    assert all("path" not in key and "title" not in key for fact in facts for key in fact)
    assert screen._ranked_candidates == before
    assert screen._played_paths == ("/a",)
    screen._on_load_next(before[0].track.path)
    assert not controller.panel.commentary.toPlainText()


def test_next_track_while_explanation_runs_discards_delivery(qapp, tmp_path, monkeypatch):
    window, services, controls = setup(qapp, tmp_path, monkeypatch)
    release = Event()
    services.explain_grounded_evidence.side_effect = lambda *_: (release.wait(2), "old transition")[1]
    screen = window._live_assistant_screen
    assert screen.set_session(_set(), _readiness())
    controller = controls["live"]
    ask(controller)
    screen.load_next(screen._ranked_candidates[0].track.path)
    release.set()
    drain(qapp, controller)
    assert not controller.panel.commentary.toPlainText()


def test_absent_gaps_or_unready_live_never_send(qapp, tmp_path, monkeypatch):
    _, services, controls = setup(qapp, tmp_path, monkeypatch)
    for controller in controls.values():
        ask(controller)
        assert not controller.busy
    services.explain_grounded_evidence.assert_not_called()
