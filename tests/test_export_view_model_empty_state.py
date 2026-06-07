"""Tests for ExportViewModel empty-state guidance (Work Unit 7)."""

from __future__ import annotations

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportViewModel


class TestEmptyStateGuidance:
    def test_no_recommendation_shows_build_first_message(self) -> None:
        vm = ExportViewModel()
        text = vm.empty_state_text(AppState())
        assert text is not None
        assert "build" in text.lower() or "playlist" in text.lower()

    def test_empty_state_contains_destination_format(self) -> None:
        vm = ExportViewModel()
        text = vm.empty_state_text(AppState())
        assert text is not None
        assert "serato" in text.lower() or "crate" in text.lower()

    def test_empty_state_contains_preview_explanation(self) -> None:
        vm = ExportViewModel()
        text = vm.empty_state_text(AppState())
        assert text is not None
        assert "preview" in text.lower()

    def test_empty_state_contains_serato_verification_hint(self) -> None:
        vm = ExportViewModel()
        text = vm.empty_state_text(AppState())
        assert text is not None
        assert "serato" in text.lower() or "open" in text.lower()


class TestPreviewExplanation:
    def test_preview_does_not_write_files(self) -> None:
        vm = ExportViewModel()
        text = vm.preview_explanation_text()
        assert text is not None
        assert "write" in text.lower() or "file" in text.lower()
        assert "preview" in text.lower()


class TestDestinationExplanation:
    def test_destination_mentions_crate_format(self) -> None:
        vm = ExportViewModel()
        text = vm.destination_text()
        assert text is not None
        assert "crate" in text.lower() or "subcrate" in text.lower()
