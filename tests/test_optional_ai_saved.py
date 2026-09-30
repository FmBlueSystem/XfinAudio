"""Saved-set AI uses anonymous snapshots and renders local, truthful facts."""

from threading import Event
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from tests.test_optional_ai_controller import drain
from tests.test_optional_ai_library_editor import host
from xfinaudio.ai.structured_assists import SavedInterpretation, anonymize_saved_request, build_saved_descriptors
from xfinaudio.desktop.optional_ai_saved import install_saved_control


def service(result):
    return SimpleNamespace(
        anonymize_saved_request=anonymize_saved_request,
        build_saved_descriptors=build_saved_descriptors,
        interpret_saved_request=MagicMock(return_value=result),
    )


def test_saved_comparison_sends_anonymous_summaries_and_renders_local_evidence(qapp, tmp_path, monkeypatch):
    window = host(qapp, tmp_path, monkeypatch)
    first = window._playlist_repository.create("Sunset", ["a", "b"])
    second = window._playlist_repository.create("Peak", ["b", "missing"])
    services = service(SavedInterpretation(action="compare", selected_ids=("s0", "s1")))
    controller = install_saved_control(window, services=services)
    controller.request.setText("compare Sunset and Peak")
    controller.panel.consent.setChecked(True)
    controller.panel.ask_button.click()
    drain(qapp, controller)
    request, descriptors = services.interpret_saved_request.call_args.args
    assert "Sunset" not in request and "Peak" not in request
    assert {d.id for d in descriptors} == {"s0", "s1"}
    assert "track_paths" not in repr(descriptors)
    text = window._playlists_screen.assistant_output.toPlainText()
    assert "Sunset" in text and "Peak" in text and "1 shared unique track" in text
    assert "1/2 known" in text
    assert window._playlist_repository.get_by_id(first.id) == first
    assert window._playlist_repository.get_by_id(second.id) == second


@pytest.mark.parametrize("change", ["delete", "replace", "unknown_id"])
def test_stale_repository_or_unrecognized_id_cannot_publish_results(qapp, tmp_path, monkeypatch, change):
    window = host(qapp, tmp_path, monkeypatch)
    saved = window._playlist_repository.create("Set", ["a", "b"])
    release = Event()
    services = service(SavedInterpretation(action="find", selected_ids=("s999" if change == "unknown_id" else "s0",)))
    result = services.interpret_saved_request.return_value
    services.interpret_saved_request.side_effect = lambda *_: (release.wait(2), result)[1]
    controller = install_saved_control(window, services=services)
    controller.request.setText("find a warm set")
    controller.panel.consent.setChecked(True)
    controller.panel.ask_button.click()
    if change == "delete":
        window._playlist_repository.delete(saved.id)
    if change == "replace":
        window._playlist_repository.update_tracks(saved.id, ["c"])
    release.set()
    drain(qapp, controller)
    assert not window._playlists_screen.assistant_output.toPlainText()
    assert "validated" in controller.panel.status.text()
