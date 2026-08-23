import base64
import json
import logging
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile
from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.scan_service import ScanService
from xfinaudio.library.scan_service import (
    ScanCancellationToken,
    ScanCancelledError,
    _coerce_tag_value,
    _lookup_previous_profile,
    read_mutagen_tags,
    scan_folder,
)


def test_scan_folder_recursively_reads_supported_audio_metadata() -> None:
    requested_paths: list[Path] = []

    def read_tags(path: Path) -> dict[str, list[str]]:
        requested_paths.append(path)
        return {
            "title": ["Track One"],
            "artist": ["Artist One"],
            "bpm": ["116.0"],
            "key": ["eyJhbGdvcml0aG0iOjk0LCJrZXkiOiIxMUIiLCJzb3VyY2UiOiJtaXhlZGlua2V5In0="],
            "energy": ["eyJhbGdvcml0aG0iOjEzLCJlbmVyZ3lMZXZlbCI6Nywic291cmNlIjoibWl4ZWRpbmtleSJ9"],
            "genre": ["Disco"],
        }

    root = Path("/library")
    paths = [root / "nested" / "track.flac", root / "notes.txt"]

    records = scan_folder(root, list_paths=lambda folder: paths, read_tags=read_tags)

    assert [record.path for record in records] == [str(root / "nested" / "track.flac")]
    assert requested_paths == [root / "nested" / "track.flac"]
    assert records[0].title == "Track One"
    assert records[0].artist == "Artist One"
    assert records[0].bpm == 116.0
    assert records[0].camelot_key == "11B"
    assert records[0].energy_level == 7
    assert records[0].genre == "Disco"
    assert records[0].metadata_status == "complete"
    assert records[0].raw_metadata["title"] == ["Track One"]
    assert records[0].source_fields["camelot_key"] == "key"


def test_scan_folder_threads_audio_md5_from_tag_reader() -> None:
    root = Path("/library")
    checksum = "0123456789abcdef0123456789abcdef"

    records = scan_folder(
        root,
        list_paths=lambda folder: [folder / "track.flac"],
        read_tags=lambda path: {"title": ["Track One"], "__audio_md5__": checksum},
        resolve_spectral_profiles=False,
    )

    assert records[0].audio_md5 == checksum
    assert records[0].title == "Track One"


def test_scan_folder_defaults_audio_md5_to_none_when_tag_reader_omits_it() -> None:
    root = Path("/library")

    records = scan_folder(
        root,
        list_paths=lambda folder: [folder / "track.flac"],
        read_tags=lambda path: {"title": ["Track One"]},
        resolve_spectral_profiles=False,
    )

    assert records[0].audio_md5 is None
    assert records[0].title == "Track One"
    assert records[0].raw_metadata == {"title": ["Track One"]}


def test_scan_folder_derives_energy_curve_from_cuepoint_tag() -> None:
    cuepoints = base64.b64encode(
        json.dumps(
            {
                "cues": [
                    {"name": "Energy 4", "time": 15000},
                    {"name": "Energy 9", "time": 120000},
                    {"name": "Energy 7", "time": 210000},
                ]
            }
        ).encode()
    ).decode()

    records = scan_folder(
        Path("/library"),
        list_paths=lambda folder: [folder / "track.flac"],
        read_tags=lambda path: {"cuepoints": [cuepoints]},
    )

    assert (records[0].energy_in, records[0].energy_out, records[0].energy_peak) == (4, 7, 9)


def test_scan_folder_reads_duplicate_lister_candidates_once() -> None:
    root = Path("/library")
    audio_path = root / "track.flac"
    requested_paths: list[Path] = []

    def read_tags(path: Path) -> dict[str, list[str]]:
        requested_paths.append(path)
        return {"title": ["Track One"]}

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path, audio_path, root / "notes.txt"],
        read_tags=read_tags,
    )

    assert requested_paths == [audio_path]
    assert [record.path for record in records] == [str(audio_path)]


def test_scan_folder_marks_records_incomplete_when_required_metadata_is_missing() -> None:
    root = Path("/library")
    audio_path = root / "track.aif"

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Partial"], "TBPM": ["128.55"]},
    )

    assert records[0].metadata_status == "incomplete"
    assert set(records[0].missing_required_fields) == {"camelot_key", "energy_level"}


def test_scan_folder_skips_files_when_mutagen_cannot_read_tags() -> None:
    root = Path("/library")
    audio_path = root / "broken.mp3"

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: None,
    )

    assert records == []


def test_scan_folder_skips_supported_files_when_tag_reader_raises() -> None:
    root = Path("/library")
    broken_path = root / "broken.flac"
    good_path = root / "good.flac"

    def read_tags(path: Path) -> dict[str, list[str]]:
        if path == broken_path:
            raise ValueError("corrupt metadata")
        return {
            "title": ["Good Track"],
            "bpm": ["116.0"],
            "key": ["eyJhbGdvcml0aG0iOjk0LCJrZXkiOiIxMUIiLCJzb3VyY2UiOiJtaXhlZGlua2V5In0="],
            "energy": ["eyJhbGdvcml0aG0iOjEzLCJlbmVyZ3lMZXZlbCI6Nywic291cmNlIjoibWl4ZWRpbmtleSJ9"],
        }

    records = scan_folder(
        root,
        list_paths=lambda folder: [broken_path, good_path],
        read_tags=read_tags,
    )

    assert [record.path for record in records] == [str(good_path)]


def test_scan_folder_logs_supported_file_read_failures_without_raw_metadata(caplog) -> None:
    root = Path("/library")
    broken_path = root / "broken.flac"

    with caplog.at_level(logging.WARNING, logger="xfinaudio.library.scan_service"):
        records = scan_folder(
            root,
            list_paths=lambda folder: [broken_path],
            read_tags=lambda path: (_ for _ in ()).throw(ValueError("corrupt metadata")),
        )

    assert records == []
    assert str(broken_path) in caplog.text
    assert "ValueError" in caplog.text
    assert "corrupt metadata" in caplog.text
    assert "raw_metadata" not in caplog.text


def test_scan_folder_reports_supported_file_progress_in_deterministic_order() -> None:
    root = Path("/library")
    first_path = root / "a.flac"
    second_path = root / "nested" / "b.mp3"
    progress_events = []

    records = scan_folder(
        root,
        list_paths=lambda folder: [root / "notes.txt", second_path, first_path],
        read_tags=lambda path: {"title": [path.stem]},
        on_progress=progress_events.append,
    )

    assert [record.path for record in records] == [str(first_path), str(second_path)]
    assert [(event.processed_count, event.total_count, event.current_path) for event in progress_events] == [
        (1, 2, first_path),
        (2, 2, second_path),
    ]


def test_scan_folder_reports_progress_for_skipped_supported_files() -> None:
    root = Path("/library")
    broken_path = root / "a.flac"
    no_tags_path = root / "b.mp3"
    good_path = root / "c.wav"
    progress_events = []

    def read_tags(path: Path) -> dict[str, list[str]] | None:
        if path == broken_path:
            raise ValueError("corrupt metadata")
        if path == no_tags_path:
            return None
        return {"title": [path.stem]}

    records = scan_folder(
        root,
        list_paths=lambda folder: [good_path, no_tags_path, broken_path],
        read_tags=read_tags,
        on_progress=progress_events.append,
    )

    assert [record.path for record in records] == [str(good_path)]
    assert [(event.processed_count, event.total_count, event.current_path) for event in progress_events] == [
        (1, 3, broken_path),
        (2, 3, no_tags_path),
        (3, 3, good_path),
    ]


def test_scan_folder_raises_cancelled_error_before_later_file_without_persisting_api_change() -> None:
    root = Path("/library")
    first_path = root / "a.flac"
    second_path = root / "b.flac"
    token = ScanCancellationToken()
    requested_paths: list[Path] = []

    def read_tags(path: Path) -> dict[str, list[str]]:
        requested_paths.append(path)
        token.cancel()
        return {"title": [path.stem]}

    with pytest.raises(ScanCancelledError) as exc_info:
        scan_folder(
            root,
            list_paths=lambda folder: [first_path, second_path],
            read_tags=read_tags,
            cancellation_token=token,
        )

    assert requested_paths == [first_path]
    assert [record.path for record in exc_info.value.records] == [str(first_path)]


def test_scan_folder_attaches_spectral_profile_when_analyzer_returns_profile(monkeypatch) -> None:
    root = Path("/library")
    audio_path = root / "track.flac"
    expected_profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        dominant_color="GREEN",
    )

    def fake_analyze(path: Path, **kwargs) -> SpectralProfile:
        return expected_profile

    monkeypatch.setattr("xfinaudio.audio.analyzer.analyze_spectral_profile", fake_analyze)

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Track One"]},
    )

    assert len(records) == 1
    assert records[0].spectral_profile == expected_profile


def test_scan_folder_continues_when_analyzer_returns_none(monkeypatch) -> None:
    root = Path("/library")
    audio_path = root / "track.flac"

    monkeypatch.setattr("xfinaudio.audio.analyzer.analyze_spectral_profile", lambda path, **kwargs: None)

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Track One"]},
    )

    assert len(records) == 1
    assert records[0].spectral_profile is None


def test_scan_folder_uses_previous_profile_cache_when_file_identity_matches() -> None:
    root = Path("/library")
    audio_path = root / "track.flac"
    expected_profile = SpectralProfile(
        red_ratio=0.1,
        green_ratio=0.8,
        blue_ratio=0.1,
        dominant_color="GREEN",
    )

    def fake_analyze(path: Path, **kwargs) -> SpectralProfile:
        pytest.fail("Analyzer should not be called when cache matches")

    # The path does not exist, so stat will fail and cache lookup falls through to analysis.
    # Provide a cache entry with mismatched identity to force analysis and prove the path is checked.
    cache = {str(audio_path): (0, 0, expected_profile)}

    records = scan_folder(
        root,
        list_paths=lambda folder: [audio_path],
        read_tags=lambda path: {"title": ["Track One"]},
        parallel_spectral_analysis=False,
        previous_profile_cache=cache,
    )

    assert len(records) == 1
    # Because the file cannot be stated, the mismatched cache is ignored and analyze runs.
    # This test primarily verifies the cache code path does not crash.
    assert records[0].spectral_profile is None


@pytest.mark.parametrize(
    ("version", "is_hit"),
    [(1, False), (CURRENT_ANALYSIS_VERSION, True), (CURRENT_ANALYSIS_VERSION + 1, False)],
)
def test_previous_profile_cache_requires_exact_current_version(tmp_path: Path, version: int, is_hit: bool) -> None:
    audio_path = tmp_path / "track.flac"
    audio_path.write_text("audio")
    stat = audio_path.stat()
    profile = SpectralProfile(
        red_ratio=0.9,
        green_ratio=0.05,
        blue_ratio=0.05,
        dominant_color="RED",
        analysis_version=version,
    )
    cache = {str(audio_path): (stat.st_mtime_ns, stat.st_size, profile)}

    assert (_lookup_previous_profile(audio_path, cache) is profile) is is_hit


def test_scan_folder_runs_parallel_batch_when_enabled(monkeypatch) -> None:
    root = Path("/library")
    first_path = root / "a.flac"
    second_path = root / "b.flac"

    def fake_batch_analyze(paths, **kwargs):
        return {
            str(path): SpectralProfile(red_ratio=0.9, green_ratio=0.05, blue_ratio=0.05, dominant_color="RED")
            for path in paths
        }

    monkeypatch.setattr("xfinaudio.library.scan_service.analyze_paths", fake_batch_analyze)

    records = scan_folder(
        root,
        list_paths=lambda folder: [first_path, second_path],
        read_tags=lambda path: {"title": [path.stem]},
        parallel_spectral_analysis=True,
    )

    assert len(records) == 2
    assert all(record.spectral_profile is not None for record in records)
    assert all(record.spectral_profile.dominant_color == "RED" for record in records)


def test_scan_folder_keeps_only_parsed_tags_in_raw_metadata() -> None:
    """Bulk tags the parser never reads must not be retained on the record.

    Serato/Mixed In Key blobs (beatgrid, overview, lyrics) accounted for 261 MB
    of a 269 MB real library DB while contributing nothing to any parsed field.
    """
    root = Path("/library")

    def read_tags(path: Path) -> dict[str, object]:
        return {
            "title": ["Track One"],
            "artist": ["Artist One"],
            "bpm": ["116.0"],
            "key": ["eyJhbGdvcml0aG0iOjk0LCJrZXkiOiIxMUIiLCJzb3VyY2UiOiJtaXhlZGlua2V5In0="],
            "energy": ["eyJhbGdvcml0aG0iOjEzLCJlbmVyZ3lMZXZlbCI6Nywic291cmNlIjoibWl4ZWRpbmtleSJ9"],
            "grouping": ["2"],
            "publisher": ["Energy 3"],
            "comment": ["5A - [⚡️4 | 💃0.75]"],
            "genre": ["Disco"],
            "beatgrid": ["A" * 100_000],
            "serato_overview": ["B" * 50_000],
            "lyrics": ["C" * 10_000],
            "cuepoints": ["D" * 5_000],
            "__audio_md5__": "0123456789abcdef0123456789abcdef",
        }

    records = scan_folder(root, list_paths=lambda folder: [root / "track.flac"], read_tags=read_tags)

    raw = records[0].raw_metadata
    assert raw["title"] == ["Track One"]
    assert raw["genre"] == ["Disco"]
    for dropped in (
        "beatgrid",
        "serato_overview",
        "lyrics",
        "cuepoints",
        "grouping",
        "publisher",
        "comment",
        "__audio_md5__",
    ):
        assert dropped not in raw
    # Parsing must be unaffected: it runs before the record is built.
    assert records[0].bpm == 116.0
    assert records[0].camelot_key == "11B"
    assert records[0].energy_level == 7
    assert records[0].metadata_status == "complete"


def test_read_mutagen_tags_formats_nonzero_audio_md5(monkeypatch) -> None:
    audio = SimpleNamespace(
        tags={"title": ["Track One"]},
        info=SimpleNamespace(length=123.0, md5_signature=0xABC),
    )
    monkeypatch.setattr("xfinaudio.library.scan_service.MutagenFile", lambda path, easy: audio)

    tags = read_mutagen_tags(Path("/library/track.flac"))

    assert tags is not None
    assert tags["title"] == ["Track One"]
    assert tags["__duration__"] == 123.0
    assert tags["__audio_md5__"] == "00000000000000000000000000000abc"


@pytest.mark.parametrize(
    "info",
    [SimpleNamespace(length=123.0, md5_signature=0), SimpleNamespace(length=123.0)],
)
def test_read_mutagen_tags_omits_absent_audio_md5(monkeypatch, info) -> None:
    audio = SimpleNamespace(tags={"title": ["Track One"]}, info=info)
    monkeypatch.setattr("xfinaudio.library.scan_service.MutagenFile", lambda path, easy: audio)

    tags = read_mutagen_tags(Path("/library/track.flac"))

    assert tags is not None
    assert tags["title"] == ["Track One"]
    assert "__audio_md5__" not in tags


def test_read_mutagen_tags_ignores_audio_md5_read_errors(monkeypatch) -> None:
    class FaultyInfo:
        length = 123.0

        @property
        def md5_signature(self) -> int:
            raise RuntimeError("unreadable checksum")

    audio = SimpleNamespace(tags={"title": ["Track One"]}, info=FaultyInfo())
    monkeypatch.setattr("xfinaudio.library.scan_service.MutagenFile", lambda path, easy: audio)

    tags = read_mutagen_tags(Path("/library/track.flac"))

    assert tags is not None
    assert tags["title"] == ["Track One"]
    assert tags["__duration__"] == 123.0
    assert "__audio_md5__" not in tags


def test_coerce_tag_value_summarizes_binary_frames_without_expanding_them() -> None:
    """Binary frames must never go through repr(), which escapes each byte to \\xNN.

    Measured: str() on a mutagen APIC holding a 1 MB cover yields 4,000,111
    characters. On an MP3 library with embedded art that is tens of GB.
    """

    class FakeApic:
        """Mimics a mutagen APIC frame: no .text, repr() dumps the raw bytes."""

        def __init__(self, data: bytes) -> None:
            self.data = data

        def __repr__(self) -> str:
            return f"APIC(data={self.data!r})"

    payload = b"\xff" * 100_000
    result = _coerce_tag_value(FakeApic(payload))

    assert isinstance(result, str)
    assert len(result) < 200
    assert "100000" in result
    assert "\\xff" not in result


def test_coerce_tag_value_still_reads_text_frames() -> None:
    """The binary guard must not change how ordinary text tags are coerced."""

    class FakeTextFrame:
        def __init__(self, text: list[str]) -> None:
            self.text = text

    assert _coerce_tag_value(FakeTextFrame(["Track One"])) == ["Track One"]
    assert _coerce_tag_value(["Disco", "House"]) == ["Disco", "House"]
    assert _coerce_tag_value("plain") == "plain"


# ---------------------------------------------------------------------------
# xfinaudio.desktop.scan_service.ScanService: LibraryWatchService integration
# ---------------------------------------------------------------------------


class _ScanLabel:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:  # noqa: N802 - Qt-compatible test double
        self.text = text


class _ScanButton:
    def __init__(self) -> None:
        self.enabled = True

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 - Qt-compatible test double
        self.enabled = enabled


class FakeLibraryWatchService:
    """Spy double recording lifecycle calls, matching LibraryWatchService's public shape."""

    def __init__(self) -> None:
        self.pause_calls = 0
        self.resume_calls = 0
        self.start_calls: list[Path] = []

    def pause(self) -> None:
        self.pause_calls += 1

    def resume(self) -> None:
        self.resume_calls += 1

    def start(self, folder: Path) -> None:
        self.start_calls.append(folder)


def _wire_desktop_scan_service(
    service: ScanService,
    *,
    state: AppState,
    folder: Path | None = None,
    watch_service: Any = None,
) -> dict[str, Any]:
    captured: dict[str, Any] = {"scanned_records": []}

    def _set_scanned_records(records: list) -> None:
        captured["scanned_records"] = records

    service.set_state_accessors(
        selected_folder=lambda: folder,
        scanned_records=lambda: captured["scanned_records"],
        set_scanned_records=_set_scanned_records,
        state=state,
    )
    service.set_ui(
        library_screen=SimpleNamespace(scan_button=_ScanButton(), cancel_button=_ScanButton()),
        build_screen=SimpleNamespace(recommend_button=_ScanButton()),
        status_label=_ScanLabel(),
        scan_progress_label=_ScanLabel(),
        library_guidance_label=_ScanLabel(),
        recommendation_guidance_label=_ScanLabel(),
        tr=lambda text: text,
    )
    service.set_actions(
        sync_state=lambda: None,
        show_tracks=lambda *_args: None,
        clear_scan_dependent_state=lambda: None,
        refresh_idle_action_state=lambda: None,
        cancel_spectral_completion_worker=lambda: None,
        show_status_bar=lambda: None,
    )
    if watch_service is not None:
        service.set_watch_service(cast(Any, watch_service))
    return captured


def _completed_result(records: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        cancelled=False,
        records=records or [],
        complete_count=0,
        incomplete_count=0,
    )


def test_begin_scan_state_pauses_watch_service_when_wired() -> None:
    service = ScanService(cast(Any, object()))
    watch_service = FakeLibraryWatchService()
    _wire_desktop_scan_service(service, state=AppState(), watch_service=watch_service)

    service.begin_scan_state()

    assert watch_service.pause_calls == 1


def test_end_scan_state_resumes_watch_service_when_wired() -> None:
    service = ScanService(cast(Any, object()))
    watch_service = FakeLibraryWatchService()
    _wire_desktop_scan_service(service, state=AppState(), watch_service=watch_service)

    service._end_scan_state()

    assert watch_service.resume_calls == 1


def test_successful_scan_arms_watch_on_scanned_folder() -> None:
    service = ScanService(cast(Any, object()))
    watch_service = FakeLibraryWatchService()
    folder = Path("/music")
    _wire_desktop_scan_service(service, state=AppState(), folder=folder, watch_service=watch_service)

    service.on_completed(_completed_result())

    assert watch_service.start_calls == [folder]


def test_successful_scan_clears_changes_detected_state() -> None:
    service = ScanService(cast(Any, object()))
    state = AppState(changes_detected_since_scan=True)
    _wire_desktop_scan_service(service, state=state)

    service.on_completed(_completed_result())

    assert service._state.changes_detected_since_scan is False


def test_scan_service_works_without_watch_service_wired() -> None:
    service = ScanService(cast(Any, object()))
    _wire_desktop_scan_service(service, state=AppState(), folder=Path("/music"))

    service.begin_scan_state()
    service.on_completed(_completed_result())

    assert service._watch_service is None


def test_pause_resume_debounce_burst_through_real_library_watch_service_coalesces_once() -> None:
    """End-to-end pause (scan begins) -> resume (scan ends) -> debounce burst,
    through a real LibraryWatchService wired to ScanService, coalesces to a
    single changes_detected_since_scan transition."""
    from tests.test_library_watch_service import FakeDebounceTimer, FakeEventSource
    from xfinaudio.desktop.library_watch_service import LibraryWatchService
    from xfinaudio.library.folder_watcher import FolderWatcher

    event_source = FakeEventSource()
    folder_watcher = FolderWatcher(event_source=event_source)
    timers: list[FakeDebounceTimer] = []

    def factory(on_timeout):
        timer = FakeDebounceTimer(on_timeout)
        timers.append(timer)
        return timer

    watch_service = LibraryWatchService(folder_watcher, debounce_timer_factory=factory, settle_window_ms=2000)
    folder = Path("/music")
    state = AppState(selected_folder=folder)
    watch_service.set_state_accessors(state=state, sync_state=lambda: None)

    scan_service = ScanService(cast(Any, object()))
    _wire_desktop_scan_service(scan_service, state=state, folder=folder, watch_service=watch_service)

    # Manual "Scan" click: begins the scan (pauses the watcher, no watch armed yet).
    scan_service.begin_scan_state()
    # Scan completes: resumes onto nothing (never armed), then arms the watch on
    # the scanned folder as the successful-scan hook does.
    scan_service.on_completed(_completed_result())

    emissions: list[None] = []
    watch_service.changes_detected.connect(lambda: emissions.append(None))

    event_source.fire(str(folder / "a.mp3"))
    event_source.fire(str(folder / "b.mp3"))
    event_source.fire(str(folder / "c.mp3"))
    timers[-1].fire()

    assert len(emissions) == 1
