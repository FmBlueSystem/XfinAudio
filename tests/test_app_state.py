"""Tests for AppState — central mutable state container for XfinAudio."""

from __future__ import annotations

from xfinaudio.desktop.app_state import VALID_SCREENS, AppState
from xfinaudio.library.models import TrackRecord


def make_track(path: str) -> TrackRecord:
    return TrackRecord(path=path, title=path)


class TestAppStateDefaults:
    def test_construction_does_not_raise(self) -> None:
        state = AppState()
        assert state is not None

    def test_selected_folder_default(self) -> None:
        assert AppState().selected_folder is None

    def test_scanned_records_default(self) -> None:
        assert AppState().scanned_records == []

    def test_records_by_path_default(self) -> None:
        assert AppState().records_by_path == {}

    def test_last_recommendation_default(self) -> None:
        assert AppState().last_recommendation is None

    def test_last_playlist_explanation_default(self) -> None:
        assert AppState().last_playlist_explanation is None

    def test_last_quality_report_default(self) -> None:
        assert AppState().last_quality_report is None

    def test_last_dj_readiness_report_default(self) -> None:
        assert AppState().last_dj_readiness_report is None

    def test_last_prep_copilot_plan_default(self) -> None:
        assert AppState().last_prep_copilot_plan is None

    def test_applied_variant_name_default(self) -> None:
        assert AppState().applied_variant_name is None

    def test_serato_export_history_default_empty(self) -> None:
        assert AppState().serato_export_history == []

    def test_serato_export_history_is_not_shared(self) -> None:
        a = AppState()
        b = AppState()
        a.serato_export_history.append({"foo": "bar"})
        assert b.serato_export_history == []

    def test_current_screen_default(self) -> None:
        assert AppState().current_screen == "library"

    def test_is_scanning_default(self) -> None:
        assert AppState().is_scanning is False

    def test_is_recommending_default(self) -> None:
        assert AppState().is_recommending is False

    def test_settings_is_not_none(self) -> None:
        # AppSettings can be constructed without arguments.
        assert AppState().settings is not None


class TestWithScreen:
    def test_returns_new_screen(self) -> None:
        state = AppState()
        updated = state.with_screen("build")
        assert updated.current_screen == "build"

    def test_original_not_mutated(self) -> None:
        state = AppState()
        state.with_screen("build")
        assert state.current_screen == "library"

    def test_returns_copy(self) -> None:
        state = AppState()
        updated = state.with_screen("review")
        assert updated is not state

    def test_all_valid_screens(self) -> None:
        state = AppState()
        for screen in VALID_SCREENS:
            updated = state.with_screen(screen)  # type: ignore[arg-type]
            assert updated.current_screen == screen

    def test_invalid_screen_does_not_raise(self) -> None:
        # ScreenName is a Literal — Python does not enforce at runtime.
        state = AppState()
        updated = state.with_screen("foo")  # type: ignore[arg-type]
        assert updated.current_screen == "foo"


class TestWithScannedRecords:
    def test_records_by_path_built_correctly(self) -> None:
        t1 = make_track("/music/a.flac")
        t2 = make_track("/music/b.flac")
        state = AppState().with_scanned_records([t1, t2])
        assert state.records_by_path == {"/music/a.flac": t1, "/music/b.flac": t2}

    def test_scanned_records_stored(self) -> None:
        t1 = make_track("/music/a.flac")
        state = AppState().with_scanned_records([t1])
        assert state.scanned_records == [t1]

    def test_original_not_mutated(self) -> None:
        original = AppState()
        original.with_scanned_records([make_track("/music/a.flac")])
        assert original.scanned_records == []

    def test_external_list_mutation_does_not_affect_state(self) -> None:
        t1 = make_track("/music/a.flac")
        lst = [t1]
        state = AppState().with_scanned_records(lst)
        lst.append(make_track("/music/b.flac"))
        assert len(state.scanned_records) == 1

    def test_returns_copy(self) -> None:
        state = AppState()
        updated = state.with_scanned_records([])
        assert updated is not state

    def test_empty_list_produces_empty_index(self) -> None:
        state = AppState().with_scanned_records([])
        assert state.records_by_path == {}


class TestDebugSummary:
    def test_returns_dict(self) -> None:
        summary = AppState().debug_summary()
        assert isinstance(summary, dict)

    def test_required_keys_present(self) -> None:
        summary = AppState().debug_summary()
        expected_keys = {
            "screen",
            "folder",
            "tracks",
            "has_recommendation",
            "has_readiness",
            "applied_variant",
            "export_history",
        }
        assert expected_keys.issubset(summary.keys())

    def test_screen_value(self) -> None:
        assert AppState().debug_summary()["screen"] == "library"

    def test_tracks_count(self) -> None:
        t = make_track("/music/a.flac")
        state = AppState().with_scanned_records([t])
        assert state.debug_summary()["tracks"] == 1

    def test_has_recommendation_false_by_default(self) -> None:
        assert AppState().debug_summary()["has_recommendation"] is False

    def test_has_readiness_false_by_default(self) -> None:
        assert AppState().debug_summary()["has_readiness"] is False

    def test_applied_variant_none_by_default(self) -> None:
        assert AppState().debug_summary()["applied_variant"] is None

    def test_export_history_count_zero(self) -> None:
        assert AppState().debug_summary()["export_history"] == 0
