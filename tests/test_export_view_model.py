"""Tests for ExportViewModel — export screen data transformation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.export_view_model import ExportHistoryRow, ExportViewModel
from xfinaudio.quality.dj_readiness import DjReadinessReport

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_recommendation(track_count: int = 3) -> MagicMock:
    strategy = MagicMock()
    strategy.name = "harmonic_journey"
    rec = MagicMock()
    rec.ordered_tracks = [MagicMock() for _ in range(track_count)]
    rec.strategy = strategy
    return rec


def _make_readiness(status: str) -> DjReadinessReport:
    return DjReadinessReport(
        status=status,
        summary="test summary",
        blocker_count=1 if status == "blocked" else 0,
        review_count=1 if status == "needs_review" else 0,
        checks=[],
    )


def _make_history_entry(
    strategy: str = "harmonic_journey",
    tracks: str = "5",
    path: str = "/tmp/crate.crate",
    time: str = "14:30:00",
) -> dict[str, str]:
    return {
        "time": time,
        "strategy": strategy,
        "tracks": tracks,
        "path": path,
        "readiness_json_path": "",
        "readiness_csv_path": "",
    }


# ---------------------------------------------------------------------------
# export_enabled
# ---------------------------------------------------------------------------


class TestExportEnabled:
    def test_no_recommendation_returns_false(self) -> None:
        vm = ExportViewModel()
        assert vm.export_enabled(AppState()) is False

    def test_recommendation_with_ready_status_returns_true(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation()
        state.last_dj_readiness_report = _make_readiness("ready")
        assert vm.export_enabled(state) is True

    def test_recommendation_with_blocked_status_returns_false(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation()
        state.last_dj_readiness_report = _make_readiness("blocked")
        assert vm.export_enabled(state) is False

    def test_recommendation_without_readiness_returns_true(self) -> None:
        """No readiness info → don't block export."""
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation()
        assert vm.export_enabled(state) is True

    def test_recommendation_with_needs_review_returns_true(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation()
        state.last_dj_readiness_report = _make_readiness("needs_review")
        assert vm.export_enabled(state) is True


# ---------------------------------------------------------------------------
# preview_text
# ---------------------------------------------------------------------------


class TestPreviewText:
    def test_no_recommendation_returns_none(self) -> None:
        vm = ExportViewModel()
        assert vm.preview_text(AppState()) is None

    def test_recommendation_without_variant_contains_track_count(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation(track_count=7)
        result = vm.preview_text(state)
        assert result is not None
        assert "7" in result

    def test_recommendation_without_variant_omits_variant_text(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation(track_count=4)
        state.applied_variant_name = None
        result = vm.preview_text(state)
        assert result is not None
        assert "variant" not in result.lower()

    def test_recommendation_with_variant_contains_variant_label(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation(track_count=4)
        state.applied_variant_name = "safe"
        result = vm.preview_text(state)
        assert result is not None
        assert "variant" in result.lower() or "Variant" in result


# ---------------------------------------------------------------------------
# export_history_rows
# ---------------------------------------------------------------------------


class TestExportHistoryRows:
    def test_empty_history_returns_empty_list(self) -> None:
        vm = ExportViewModel()
        assert vm.export_history_rows(AppState()) == []

    def test_history_maps_to_rows_most_recent_first(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.serato_export_history = [
            _make_history_entry(time="15:00:00", tracks="3"),
            _make_history_entry(time="14:00:00", tracks="5"),
        ]
        rows = vm.export_history_rows(state)
        assert len(rows) == 2
        # First in history list is most recent (record_export prepends)
        assert "3" in rows[0].track_count
        assert "5" in rows[1].track_count

    def test_history_row_fields_populated(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.serato_export_history = [
            _make_history_entry(
                strategy="harmonic_journey",
                tracks="8",
                path="/tmp/my_crate.crate",
                time="12:00:00",
            )
        ]
        rows = vm.export_history_rows(state)
        assert len(rows) == 1
        row = rows[0]
        assert isinstance(row, ExportHistoryRow)
        assert "/tmp/my_crate.crate" in row.destination
        assert "8" in row.track_count


# ---------------------------------------------------------------------------
# applied_variant_label
# ---------------------------------------------------------------------------


class TestAppliedVariantLabel:
    def test_none_variant_returns_direct_recommend(self) -> None:
        vm = ExportViewModel()
        assert vm.applied_variant_label(AppState()) == "Direct Recommend"

    def test_safe_variant_returns_variant_safe(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.applied_variant_name = "safe"
        assert vm.applied_variant_label(state) == "Variant: Safe"

    def test_balanced_variant_returns_variant_balanced(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.applied_variant_name = "balanced"
        assert vm.applied_variant_label(state) == "Variant: Balanced"

    def test_adventurous_variant_returns_variant_adventurous(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.applied_variant_name = "adventurous"
        assert vm.applied_variant_label(state) == "Variant: Adventurous"


# ---------------------------------------------------------------------------
# safe_folder_label
# ---------------------------------------------------------------------------


class TestSafeFolderLabel:
    def test_no_folder_returns_not_set_message(self) -> None:
        vm = ExportViewModel()
        assert vm.safe_folder_label(AppState()) == "No safe folder set"

    def test_folder_returns_only_folder_name(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.settings = AppSettings(
            export=ExportSettings(safe_export_folder=Path("/Users/freddy/Music/Serato"))
        )
        assert vm.safe_folder_label(state) == "Serato"

    def test_folder_name_not_full_path(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.settings = AppSettings(
            export=ExportSettings(safe_export_folder=Path("/a/b/c/d"))
        )
        result = vm.safe_folder_label(state)
        assert "/" not in result
        assert result == "d"


# ---------------------------------------------------------------------------
# track_count_text
# ---------------------------------------------------------------------------


class TestTrackCountText:
    def test_no_recommendation_returns_dash(self) -> None:
        vm = ExportViewModel()
        assert vm.track_count_text(AppState()) == "—"

    def test_recommendation_returns_track_count_with_label(self) -> None:
        vm = ExportViewModel()
        state = AppState()
        state.last_recommendation = _make_recommendation(track_count=11)
        result = vm.track_count_text(state)
        assert "11" in result
        assert "track" in result.lower()
