"""Tests for the 5 Qt screen widgets."""

from __future__ import annotations

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.export_view_model import ExportViewModel
from xfinaudio.desktop.library_view_model import LibraryViewModel
from xfinaudio.desktop.review_view_model import ReviewViewModel
from xfinaudio.desktop.screens import (
    BuildScreen,
    ExportScreen,
    LibraryScreen,
    MetadataScreen,
    ReviewScreen,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.playlist_service import PlaylistRecommendation
from xfinaudio.recommendation.strategies import default_strategy_registry


def _recommendation() -> PlaylistRecommendation:
    track = TrackRecord(path="/music/a.flac", title="A", metadata_status="complete")
    return PlaylistRecommendation(
        ordered_tracks=[track],
        transition_scores=[],
        strategy=default_strategy_registry().get("build"),
        warnings=[],
        applied_controls={},
        optimizer="test",
        total_score=0.0,
    )


# ---------------------------------------------------------------------------
# LibraryScreen
# ---------------------------------------------------------------------------


class TestLibraryScreen:
    def test_instantiates(self, qapp) -> None:
        screen = LibraryScreen()
        assert screen is not None

    def test_has_required_widgets(self, qapp) -> None:
        screen = LibraryScreen()
        assert hasattr(screen, "folder_button")
        assert hasattr(screen, "scan_button")
        assert hasattr(screen, "cancel_button")
        assert hasattr(screen, "status_label")
        assert hasattr(screen, "tracks_table")
        assert hasattr(screen, "search_input")
        assert hasattr(screen, "proceed_button")

    def test_render_empty_state_does_not_raise(self, qapp) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = AppState()
        screen.render(vm, state)  # must not raise

    def test_scan_button_disabled_without_folder(self, qapp) -> None:
        screen = LibraryScreen()
        vm = LibraryViewModel()
        state = AppState()  # selected_folder is None
        screen.render(vm, state)
        assert not screen.scan_button.isEnabled()

    def test_tracks_table_has_enough_columns(self, qapp) -> None:
        screen = LibraryScreen()
        assert screen.tracks_table.columnCount() >= 5


# ---------------------------------------------------------------------------
# BuildScreen
# ---------------------------------------------------------------------------


class TestBuildScreen:
    def test_instantiates(self, qapp) -> None:
        screen = BuildScreen()
        assert screen is not None

    def test_has_required_widgets(self, qapp) -> None:
        screen = BuildScreen()
        assert hasattr(screen, "strategy_combo")
        assert hasattr(screen, "recommend_button")
        assert hasattr(screen, "copilot_button")
        assert hasattr(screen, "copilot_table")
        assert hasattr(screen, "apply_variant_button")
        assert hasattr(screen, "proceed_button")
        assert hasattr(screen, "variant_label")
        assert hasattr(screen, "back_button")

    def test_render_empty_state_does_not_raise(self, qapp) -> None:
        screen = BuildScreen()
        vm = BuildViewModel()
        state = AppState()
        screen.render(vm, state)  # must not raise

    def test_recommend_button_disabled_without_tracks(self, qapp) -> None:
        screen = BuildScreen()
        vm = BuildViewModel()
        state = AppState()  # no scanned_records
        screen.render(vm, state)
        assert not screen.recommend_button.isEnabled()


# ---------------------------------------------------------------------------
# ReviewScreen
# ---------------------------------------------------------------------------


class TestReviewScreen:
    def test_instantiates(self, qapp) -> None:
        screen = ReviewScreen()
        assert screen is not None

    def test_has_required_widgets(self, qapp) -> None:
        screen = ReviewScreen()
        assert hasattr(screen, "readiness_badge")
        assert hasattr(screen, "readiness_table")
        assert hasattr(screen, "recommendation_table")
        assert hasattr(screen, "export_button")
        assert hasattr(screen, "save_to_playlists_button")

    def test_render_empty_state_does_not_raise(self, qapp) -> None:
        screen = ReviewScreen()
        vm = ReviewViewModel()
        state = AppState()
        screen.render(vm, state)  # must not raise

    def test_readiness_badge_no_playlist(self, qapp) -> None:
        screen = ReviewScreen()
        vm = ReviewViewModel()
        state = AppState()  # no recommendation
        screen.render(vm, state)
        assert "No playlist" in screen.readiness_badge.text() or "playlist" in screen.readiness_badge.text().lower()

    def test_export_button_disabled_without_recommendation(self, qapp) -> None:
        screen = ReviewScreen()
        vm = ReviewViewModel()
        state = AppState()  # no recommendation → BLOCKED → can_export=False
        screen.render(vm, state)
        assert not screen.export_button.isEnabled()

    def test_save_to_playlists_button_tracks_recommendation_availability(self, qapp) -> None:
        screen = ReviewScreen()
        vm = ReviewViewModel()

        screen.render(vm, AppState())
        assert not screen.save_to_playlists_button.isEnabled()

        screen.render(vm, AppState(last_recommendation=_recommendation()))
        assert screen.save_to_playlists_button.isEnabled()

    def test_save_to_playlists_button_emits_signal(self, qapp) -> None:
        screen = ReviewScreen()
        calls: list[None] = []
        screen.save_to_playlists_requested.connect(lambda: calls.append(None))

        screen.save_to_playlists_button.setEnabled(True)
        screen.save_to_playlists_button.click()

        assert calls == [None]

    def test_readiness_badge_status_property_drives_color(self, qapp) -> None:
        """The badge exposes a `status` property so the theme can color it like a semaphore."""
        screen = ReviewScreen()
        vm = ReviewViewModel()

        screen.render(vm, AppState())  # no recommendation → blocked
        assert screen.readiness_badge.property("status") == "blocked"

        screen.render(vm, AppState(last_recommendation=_recommendation()))  # no report → needs_review
        assert screen.readiness_badge.property("status") == "needs_review"

    def test_duplicate_quality_line_is_not_in_visible_layout(self, qapp) -> None:
        """The quality line is consolidated into the review summary, not shown as a 4th label."""
        screen = ReviewScreen()
        assert screen.quality_label.parent() is None


# ---------------------------------------------------------------------------
# ExportScreen
# ---------------------------------------------------------------------------


class TestExportScreen:
    def test_instantiates(self, qapp) -> None:
        screen = ExportScreen()
        assert screen is not None

    def test_has_required_widgets(self, qapp) -> None:
        screen = ExportScreen()
        assert hasattr(screen, "variant_label")
        assert hasattr(screen, "export_button")
        assert hasattr(screen, "preview_button")
        assert hasattr(screen, "history_table")
        assert hasattr(screen, "safe_folder_label")
        assert hasattr(screen, "safe_folder_button")
        assert hasattr(screen, "export_readiness_button")
        assert hasattr(screen, "back_button")

    def test_render_empty_state_does_not_raise(self, qapp) -> None:
        screen = ExportScreen()
        vm = ExportViewModel()
        state = AppState()
        screen.render(vm, state)  # must not raise

    def test_playlist_info_label_height_is_capped(self, qapp) -> None:
        """The one-line export summary must not balloon into a giant empty box."""
        screen = ExportScreen()
        height = screen.playlist_info_label.maximumHeight()
        assert 0 < height <= 80


# ---------------------------------------------------------------------------
# MetadataScreen
# ---------------------------------------------------------------------------


class TestMetadataScreen:
    def test_instantiates(self, qapp) -> None:
        screen = MetadataScreen()
        assert screen is not None

    def test_has_required_widgets(self, qapp) -> None:
        screen = MetadataScreen()
        assert hasattr(screen, "status_label")
        assert hasattr(screen, "back_button")

    def test_render_empty_state_does_not_raise(self, qapp) -> None:
        screen = MetadataScreen()
        state = AppState()
        screen.render(state)  # must not raise

    def test_render_empty_state_shows_guidance_in_worklist_area(self, qapp) -> None:
        screen = MetadataScreen()

        screen.render(AppState())

        assert not screen.worklist_empty_label.isHidden()
        assert "No library scanned yet" in screen.worklist_empty_label.text()
        assert screen.worklist_table.isHidden()
