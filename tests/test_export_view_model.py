"""Tests for ExportViewModel user-facing copy."""

from __future__ import annotations

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel


def test_empty_state_text_describes_direct_serato_export() -> None:
    """The empty-state describes the crate destination and separate report folder."""
    vm = ExportViewModel()
    state = AppState(last_recommendation=None)

    text = vm.empty_state_text(state)

    assert "directly" in text.lower()
    assert "_Serato_/Subcrates" in text
    assert "report folder" in text.lower()
    assert "manual copy" not in text.lower()


def test_destination_text_describes_direct_crate_and_optional_reports() -> None:
    """Destination guidance follows the authorized direct-Serato flow."""
    vm = ExportViewModel()

    text = vm.destination_text()

    assert "directly" in text.lower()
    assert "_Serato_/Subcrates" in text
    assert "report folder" in text.lower()
    assert "backup" in text.lower() or "verification" in text.lower()


def test_empty_state_text_is_empty_when_recommendation_exists() -> None:
    """When a recommendation exists, the empty-state text is empty."""
    vm = ExportViewModel()
    state = AppState(last_recommendation=None)
    state = state.model_copy(update={"last_recommendation": object()})

    assert vm.empty_state_text(state) == ""


def test_optional_report_folder_does_not_claim_to_control_serato_destination():
    from pathlib import Path

    from xfinaudio.config.settings import AppSettings, ExportSettings

    vm = ExportViewModel()
    assert "optional" in vm.safe_folder_label(AppState()).lower()
    folder = Path("/reports/dj/night")
    state = AppState(settings=AppSettings(export=ExportSettings(safe_export_folder=folder)))
    assert str(folder) in vm.safe_folder_label(state)
    assert "report" in vm.safe_folder_label(state).lower()
