"""Tests for ExportViewModel user-facing copy."""

from __future__ import annotations

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel


def test_empty_state_text_warns_about_live_serato_writes() -> None:
    """When no recommendation exists, the export empty-state warns about live Serato writes."""
    vm = ExportViewModel()
    state = AppState(last_recommendation=None)

    text = vm.empty_state_text(state)

    assert "live serato" in text.lower()
    assert "not part of the verified release candidate" in text
    assert "safe export folder" in text.lower()


def test_destination_text_warns_about_manual_copy_to_live_library() -> None:
    """Destination text explains exports go to the safe folder and require manual copy."""
    vm = ExportViewModel()

    text = vm.destination_text()

    assert "safe export folder" in text.lower()
    assert "live _Serato_/Subcrates" in text
    assert "backup" in text.lower() or "verification" in text.lower()


def test_empty_state_text_is_empty_when_recommendation_exists() -> None:
    """When a recommendation exists, the empty-state text is empty."""
    vm = ExportViewModel()
    state = AppState(last_recommendation=None)
    state.last_recommendation = object()  # type: ignore[assignment]

    assert vm.empty_state_text(state) == ""
