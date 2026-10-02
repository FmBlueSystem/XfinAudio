"""Focused tests for sequential background-analysis orchestration."""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, EdgeSpectralProfile, SpectralProfile
from xfinaudio.config.settings import AppSettings, LoudnessSettings
from xfinaudio.desktop.library_columns import column_index
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.rendering import _format_spectral_color
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.loudness_policy import LoudnessBand
from xfinaudio.recommendation.playlist_service import recommend_playlist


class _FakeSettingsRepository:
    def __init__(self) -> None:
        self.saved_settings: list[AppSettings] = []

    def load(self) -> AppSettings:
        return AppSettings()

    def save(self, settings: AppSettings) -> None:
        self.saved_settings.append(settings)


class _FakeScanService:
    def scan(self, *args: object, **kwargs: object) -> list[TrackRecord]:
        return []


class _FakeRepository:
    def save_scan_results(self, records: list[TrackRecord], *, pruned_root=None) -> None:
        pass


def _ensure_app() -> QApplication:
    existing = QApplication.instance()
    return existing if isinstance(existing, QApplication) else QApplication([])


def _worker_mock() -> Mock:
    worker = Mock()
    worker.progress = Mock()
    worker.progress_updated = Mock()
    worker.finished = Mock()
    worker.failed = Mock()
    return worker


def _spectral_profile() -> SpectralProfile:
    return SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )


def _danceability_profile() -> DanceabilityProfile:
    return DanceabilityProfile(
        score=0.72,
        pulse_clarity=0.8,
        tempo_confidence=0.9,
        percussive_ratio=0.6,
    )


def _loudness_profile() -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=-9.5,
        loudness_range_lra=3.0,
        true_peak_dbtp=-0.5,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint="test-engine",
    )


def test_spectral_completion_starts_danceability_worker_after_finish(monkeypatch) -> None:
    _ensure_app()
    spectral_worker = _worker_mock()
    danceability_worker = _worker_mock()
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.SpectralCompletionWorker",
        Mock(return_value=spectral_worker),
    )
    danceability_factory = Mock(return_value=danceability_worker)
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.DanceabilityCompletionWorker",
        danceability_factory,
    )
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    records = [TrackRecord(path="/music/track.flac")]

    window._library_controller.start_spectral_completion_worker(records)

    assert spectral_worker.start.call_count == 1
    assert danceability_factory.call_count == 0

    window._library_controller.on_spectral_completion_finished()

    danceability_worker.start.assert_called_once()
    assert danceability_worker.start.call_args.args[0] == records


def test_danceability_starts_directly_when_no_spectral_work_is_pending(monkeypatch) -> None:
    _ensure_app()
    spectral_factory = Mock()
    danceability_worker = _worker_mock()
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.SpectralCompletionWorker",
        spectral_factory,
    )
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.DanceabilityCompletionWorker",
        Mock(return_value=danceability_worker),
    )
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    records = [TrackRecord(path="/music/track.flac", spectral_profile=_spectral_profile())]

    window._library_controller.start_spectral_completion_worker(records)

    spectral_factory.assert_not_called()
    danceability_worker.start.assert_called_once()
    assert danceability_worker.start.call_args.args[0] == records


def test_danceability_profile_ready_updates_state_and_requests_sync(monkeypatch) -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    record = TrackRecord(path="/music/track.flac")
    controller._state = controller._state.model_copy(
        update={"scanned_records": [record], "records_by_path": {record.path: record}}
    )
    request_sync = Mock()
    monkeypatch.setattr(controller, "_request_sync", request_sync)
    profile = _danceability_profile()

    controller.on_danceability_profile_ready(record.path, profile)
    _ensure_app().processEvents()

    assert controller._state.scanned_records[0].danceability_profile == profile
    assert controller._state.records_by_path[record.path].danceability_profile == profile
    request_sync.assert_called_once_with()


def test_danceability_completion_starts_edge_worker_after_finish(monkeypatch) -> None:
    _ensure_app()
    danceability_worker = _worker_mock()
    edge_worker = _worker_mock()
    monkeypatch.setattr(
        "xfinaudio.desktop.library_controller.DanceabilityCompletionWorker",
        Mock(return_value=danceability_worker),
    )
    edge_factory = Mock(return_value=edge_worker)
    monkeypatch.setattr("xfinaudio.desktop.library_controller.EdgeSpectralCompletionWorker", edge_factory)
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    records = [TrackRecord(path="/music/track.flac", spectral_profile=_spectral_profile())]

    window._library_controller.start_danceability_completion_worker(records)

    assert edge_factory.call_count == 0
    window._library_controller.on_danceability_completion_finished()
    edge_worker.start.assert_called_once()
    assert edge_worker.start.call_args.args[0] == records


def test_edge_profile_ready_updates_state_and_requests_sync(monkeypatch) -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    record = TrackRecord(path="/music/track.flac")
    controller._state = controller._state.model_copy(
        update={"scanned_records": [record], "records_by_path": {record.path: record}}
    )
    request_sync = Mock()
    monkeypatch.setattr(controller, "_request_sync", request_sync)
    edge = _spectral_profile()
    profile = EdgeSpectralProfile(intro=edge, outro=edge)

    controller.on_edge_spectral_profile_ready(record.path, profile)
    _ensure_app().processEvents()

    assert controller._state.scanned_records[0].edge_spectral_profile == profile
    assert controller._state.records_by_path[record.path].edge_spectral_profile == profile
    request_sync.assert_called_once_with()


def test_shutdown_tears_down_all_completion_workers() -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    spectral_worker = _worker_mock()
    danceability_worker = _worker_mock()
    edge_worker = _worker_mock()
    window._library_controller._spectral_completion_worker = spectral_worker
    window._library_controller._danceability_completion_worker = danceability_worker
    window._library_controller._edge_spectral_completion_worker = edge_worker
    window._library_controller._state = window._state.model_copy(
        update={"is_completing_loudness": True, "loudness_progress_count": 1, "loudness_total_count": 2}
    )

    window._library_controller.shutdown()

    spectral_worker.shutdown.assert_called_once_with()
    danceability_worker.shutdown.assert_called_once_with()
    edge_worker.shutdown.assert_called_once_with()
    assert window._library_controller._spectral_completion_worker is None
    assert window._library_controller._danceability_completion_worker is None
    assert window._library_controller._edge_spectral_completion_worker is None
    assert window._library_controller._state.is_completing_loudness is False


def test_library_anchor_selection_suggests_its_genre_on_build_screen() -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    records = [
        TrackRecord(path="/music/house.flac", genre="House", metadata_status="complete"),
        TrackRecord(path="/music/rock.flac", genre="Rock", metadata_status="complete"),
    ]
    window._library_controller.populate_track_table(records)

    window._library_controller.on_library_selection_changed([records[0].path])

    assert window._build_screen.genre_combo.currentText() == "House"


def test_library_selection_and_profile_completion_refresh_loudness_detail() -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    record = TrackRecord(path="/music/house.flac", genre="House")
    controller = window._library_controller
    controller._state = controller._state.model_copy(
        update={"scanned_records": [record], "records_by_path": {record.path: record}}
    )

    controller.on_library_selection_changed([record.path])
    assert window._library_screen.loudness_detail_label.text() == "Loudness: not measured"

    controller.on_loudness_profile_ready(record.path, _loudness_profile())
    _ensure_app().processEvents()
    assert window._library_screen.loudness_detail_label.text().startswith("LUFS: -9.5")

    controller.on_library_selection_changed([])
    assert window._library_screen.loudness_detail_pane.isHidden() is True


def test_replacement_backfill_uses_the_current_loudness_band() -> None:
    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller

    def measured(path: str, lufs: float) -> TrackRecord:
        return TrackRecord(
            path=path,
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            metadata_status="complete",
            loudness_profile=_loudness_profile().model_copy(update={"lufs_integrated": lufs}),
        )

    removed = measured("/removed.flac", -10)
    old_target = measured("/old-target.flac", -10)
    replacement = measured("/replacement.flac", -14)
    original_band = LoudnessBand(-10, 2)
    recommendation = recommend_playlist([removed], "consistent_loudness", loudness_band=original_band)
    controller._state = controller._state.model_copy(
        update={"scanned_records": [removed, old_target, replacement], "last_recommendation": recommendation}
    )
    settings = LoudnessSettings(target_lufs=-14, tolerance_lu=0.5)
    window.settings = window.settings.model_copy(update={"loudness": settings})

    result = controller._replacement_recommendation(removed.path)

    assert result is not None
    assert [item.path for item in result.ordered_tracks] == [replacement.path]
    assert recommendation.replacement_policy is not None
    assert recommendation.replacement_policy.loudness_band == original_band
    assert result.replacement_policy is not None
    assert result.replacement_policy.loudness_band == LoudnessBand(-14, 0.5)


def _window_with_settings_repository() -> tuple[MainWindow, _FakeSettingsRepository]:
    _ensure_app()
    settings_repository = _FakeSettingsRepository()
    window = MainWindow(
        scan_service=_FakeScanService(), repository=_FakeRepository(), settings_repository=settings_repository
    )
    return window, settings_repository


def test_exclude_requested_persists_selected_paths_in_build_settings() -> None:
    window, settings_repository = _window_with_settings_repository()
    window._library_selected_paths.append("/music/track.flac")

    window._library_controller.on_exclude_requested()

    assert settings_repository.saved_settings, "exclude must persist settings on change"
    assert settings_repository.saved_settings[-1].build.excluded_paths == frozenset({"/music/track.flac"})
    assert settings_repository.saved_settings[-1].build.locked_paths == frozenset()


def test_lock_requested_persists_selected_paths_in_build_settings() -> None:
    window, settings_repository = _window_with_settings_repository()
    window._library_selected_paths.append("/music/track.flac")

    window._library_controller.on_lock_requested()

    assert settings_repository.saved_settings, "lock must persist settings on change"
    assert settings_repository.saved_settings[-1].build.locked_paths == frozenset({"/music/track.flac"})
    assert settings_repository.saved_settings[-1].build.excluded_paths == frozenset()


def test_clear_constraints_persists_emptied_build_sets() -> None:
    window, settings_repository = _window_with_settings_repository()
    window._library_selected_paths.append("/music/track.flac")
    window._library_controller.on_exclude_requested()
    window._library_selected_paths.append("/music/other.flac")
    window._library_controller.on_lock_requested()

    window._library_controller.on_clear_constraints()

    assert settings_repository.saved_settings, "clear must persist the emptied sets"
    assert settings_repository.saved_settings[-1].build.excluded_paths == frozenset()
    assert settings_repository.saved_settings[-1].build.locked_paths == frozenset()


def test_rescan_does_not_clear_persisted_build_constraints() -> None:
    window, settings_repository = _window_with_settings_repository()
    window._library_selected_paths.append("/music/track.flac")
    window._library_controller.on_exclude_requested()

    window._library_controller.clear_scan_dependent_state()

    assert settings_repository.saved_settings[-1].build.excluded_paths == frozenset({"/music/track.flac"})


def test_cached_result_burst_publishes_once_per_tick_with_latest_values() -> None:
    app = _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    records = [TrackRecord(path=f"/{i}.flac") for i in range(1000)]
    window._replace_app_state(
        window._state.with_scanned_records(records).model_copy(
            update={"is_completing_loudness": True, "loudness_total_count": 1000}
        )
    )
    original = window._state
    published = Mock(wraps=controller._access.state_setter)
    controller._access = replace(controller._access, state_setter=published)
    controller._request_sync = Mock()
    for i, record in enumerate(records):
        controller.on_spectral_profile_ready(record.path, _spectral_profile())
        controller.on_spectral_progress_updated(i + 1, 1000)
        controller.on_loudness_profile_ready(record.path, _loudness_profile())
    controller.on_spectral_profile_ready(records[0].path, None)
    assert published.call_count == 0
    assert window._state is original

    app.processEvents()

    assert published.call_count == 1
    controller._request_sync.assert_called_once()
    assert window._state.spectral_progress_count == window._state.loudness_progress_count == 1000
    assert window._state.scanned_records[0].spectral_profile is None
    assert all(r.spectral_profile == _spectral_profile() for r in window._state.scanned_records[1:])
    assert all(r.loudness_profile == _loudness_profile() for r in window._state.scanned_records)
    assert all(r.loudness_profile is None for r in original.scanned_records)


@pytest.mark.parametrize(
    "terminal",
    [
        "on_spectral_completion_finished",
        "on_danceability_completion_finished",
        "on_edge_spectral_completion_finished",
        "on_loudness_completion_finished",
        "cancel_spectral_completion_worker",
        "cancel_danceability_completion_worker",
        "cancel_edge_spectral_completion_worker",
        "cancel_loudness_completion",
        "shutdown",
    ],
)
def test_terminal_callback_flushes_received_results_before_handoff(terminal, monkeypatch) -> None:
    app = _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    record = TrackRecord(path="/cached.flac")
    window._replace_app_state(window._state.with_scanned_records([record]))

    def check_handoff(*_args):
        assert window._state.scanned_records[0].spectral_profile == _spectral_profile()

    for method in (
        "start_danceability_completion_worker",
        "start_edge_spectral_completion_worker",
        "start_loudness_completion",
    ):
        monkeypatch.setattr(controller, method, Mock(side_effect=check_handoff))
    controller.on_spectral_profile_ready(record.path, _spectral_profile())
    assert window._state.scanned_records[0].spectral_profile is None
    getattr(controller, terminal)()
    assert window._state.scanned_records[0].spectral_profile == _spectral_profile()
    after = window._state
    app.processEvents()
    assert window._state is after


def test_replaced_library_discards_pending_batch_and_keeps_new_metadata() -> None:
    app = _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    record = TrackRecord(path="/same.flac", title="Old")
    controller.populate_track_table([record])
    controller.on_spectral_profile_ready(record.path, _spectral_profile())
    controller.populate_track_table([record.model_copy(update={"title": "Rescanned"})])
    after = window._state
    app.processEvents()
    assert window._state is after
    assert window._state.scanned_records[0].title == "Rescanned"
    assert window._state.scanned_records[0].spectral_profile is None
    assert window._library_screen.tracks_table.item(0, column_index("Color")).text() == ""


def test_batch_paints_correct_paths_after_sort_filter_and_suspends_native_sort(monkeypatch) -> None:
    app = _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    records = [TrackRecord(path=f"/{i}.flac", title=f"{10 - i}") for i in range(10)]
    controller.populate_track_table(records)
    table = window._library_screen.tracks_table
    table.setSortingEnabled(True)
    table.sortItems(column_index("Color"), Qt.SortOrder.DescendingOrder)
    table.setRowHidden(3, True)
    sorting_changes = Mock(wraps=table.setSortingEnabled)
    monkeypatch.setattr(table, "setSortingEnabled", sorting_changes)
    for record in records[::2]:
        controller.on_spectral_profile_ready(record.path, _spectral_profile())
    app.processEvents()
    assert [call.args for call in sorting_changes.call_args_list] == [(False,), (True,)]
    assert table.isSortingEnabled()
    for row in range(table.rowCount()):
        path = table.item(row, column_index("Path")).text()
        assert table.item(row, column_index("Color")).text() == _format_spectral_color(
            window._state.records_by_path[path]
        )


def test_duplicate_loudness_deliveries_count_before_profile_coalescing_and_clamp() -> None:
    app = _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    record = TrackRecord(path="/repeat.flac")
    window._replace_app_state(
        window._state.with_scanned_records([record]).model_copy(
            update={"is_completing_loudness": True, "loudness_total_count": 2}
        )
    )
    for _ in range(3):
        controller.on_loudness_profile_ready(record.path, _loudness_profile())
    controller.on_danceability_profile_ready(record.path, _danceability_profile())
    app.processEvents()
    assert window._state.loudness_progress_count == 2
    assert window._state.scanned_records[0].danceability_profile == _danceability_profile()
    assert window._state.scanned_records[0].loudness_profile == _loudness_profile()


def test_progress_only_tick_reuses_collections_and_keeps_intervening_updates() -> None:
    app = _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    records = [TrackRecord(path="/a.flac")]
    window._replace_app_state(window._state.with_scanned_records(records))
    before = window._state
    controller.on_spectral_progress_updated(1, 2)
    window._replace_app_state(window._state.model_copy(update={"changes_detected_since_scan": True}))
    app.processEvents()
    assert window._state.scanned_records is before.scanned_records
    assert window._state.records_by_path is before.records_by_path
    assert window._state.changes_detected_since_scan
    assert window._state.spectral_progress_count == 1


def test_parent_destruction_discards_unpaintable_batch_after_render_timer_teardown(monkeypatch) -> None:
    import sys

    from shiboken6 import delete

    _ensure_app()
    window = MainWindow(scan_service=_FakeScanService(), repository=_FakeRepository())
    controller = window._library_controller
    controller.on_spectral_profile_ready("/pending.flac", _spectral_profile())
    exceptions = []
    monkeypatch.setattr(sys, "excepthook", lambda _kind, error, _trace: exceptions.append(error))
    delete(window._app_controller._sync_timer)
    delete(window)
    assert not exceptions
    assert controller._shutting_down
    assert not controller._pending_profiles
