"""Tests for LibraryViewModel display logic."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.library_view_model import LibraryViewModel


def test_scan_settings_review_text_includes_supported_extensions() -> None:
    """The scan settings review lists supported audio extensions."""
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music"))

    text = vm.scan_settings_review_text(state)

    for ext in state.settings.scan.supported_extensions:
        assert ext in text
    assert "BPM" in text
    assert "TKEY" in text


def test_scan_settings_review_text_includes_field_mappings() -> None:
    """The scan settings review mentions required metadata field mappings."""
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music"))

    text = vm.scan_settings_review_text(state)

    assert "TBPM" in text
    assert "TKEY" in text
    assert "COMM:Songs-DB_Custom1" in text or "comments" in text.lower()


def test_rescan_button_visible_when_changes_detected_and_not_scanning() -> None:
    """The rescan affordance shows once a settled filesystem change is detected."""
    vm = LibraryViewModel()
    state = AppState(selected_folder=Path("/music"), changes_detected_since_scan=True)

    assert vm.rescan_button_visible(state) is True


def test_rescan_button_hidden_when_scanning_or_no_changes() -> None:
    """The rescan affordance stays hidden while scanning, and when nothing changed."""
    vm = LibraryViewModel()

    assert vm.rescan_button_visible(AppState(selected_folder=Path("/music"))) is False
    assert (
        vm.rescan_button_visible(
            AppState(selected_folder=Path("/music"), changes_detected_since_scan=True, is_scanning=True)
        )
        is False
    )


def test_status_text_shows_active_spectral_completion_progress() -> None:
    """Spectral completion progress takes priority over the normal library summary."""
    vm = LibraryViewModel()
    state = AppState(
        selected_folder=Path("/music"),
        is_completing_spectral=True,
        spectral_progress_count=3,
        spectral_total_count=10,
    )

    text = vm.status_text(state)

    assert text == "Analyzing spectral colors 3/10"
