from __future__ import annotations

import threading
from pathlib import Path
from shutil import copyfile

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_completion import LoudnessCompletionService, prioritize_records
from xfinaudio.audio.loudness_tags import LoudnessTagWriteResult, LoudnessTagWriteStatus, write_loudness_tags
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository


def _profile(status: LoudnessStatus = LoudnessStatus.MEASURED) -> LoudnessProfile:
    return LoudnessProfile(
        lufs_integrated=-10.0 if status is LoudnessStatus.MEASURED else None,
        loudness_range_lra=4.0 if status is LoudnessStatus.MEASURED else None,
        true_peak_dbtp=-1.0 if status is LoudnessStatus.MEASURED else None,
        status=status,
        engine_fingerprint="ffmpeg-test",
    )


class _Repository:
    def __init__(self, cache: dict[str, LoudnessProfile] | None = None) -> None:
        self.cache = cache or {}
        self.updated: dict[str, LoudnessProfile] = {}
        self.force_reanalyze_calls: list[bool] = []

    def load_loudness_profile_cache(self, paths, *, engine_fingerprint: str, force_reanalyze: bool = False):
        self.force_reanalyze_calls.append(force_reanalyze)
        return {} if force_reanalyze else {path: self.cache[path] for path in paths if path in self.cache}

    def refresh_post_metadata_identity(self, path: str) -> bool:
        return True

    def update_loudness_profile(self, path: str, profile: LoudnessProfile) -> bool:
        self.updated[path] = profile
        return True


class _Analyzer:
    def __init__(self) -> None:
        self.calls: list[tuple[Path, float]] = []

    def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile:
        self.calls.append((path, duration_seconds))
        return _profile()


def test_priority_planner_is_stable_deduplicated_and_ignores_unknown_paths() -> None:
    records = [TrackRecord(path=f"/{name}.flac") for name in "abcd"]

    planned = prioritize_records(
        records,
        selected_paths=["/c.flac", "/c.flac"],
        candidate_paths=["/b.flac"],
        visible_paths=["/d.flac", "/missing.flac"],
    )

    assert [record.path for record in planned] == ["/c.flac", "/b.flac", "/d.flac", "/a.flac"]


def test_completion_replays_cache_without_decoding_and_reports_progress(tmp_path: Path) -> None:
    paths = [tmp_path / name for name in ("selected.flac", "cached.flac")]
    for path in paths:
        path.write_text("audio")
    cached = _profile()
    repository = _Repository({str(paths[1]): cached})
    analyzer = _Analyzer()
    results: list[tuple[str, LoudnessProfile]] = []
    progress: list[tuple[int, int]] = []

    completed = LoudnessCompletionService(analyzer, engine_fingerprint="ffmpeg-test").complete(
        [TrackRecord(path=str(path), duration=8.0) for path in paths],
        repository,
        selected_paths=[str(paths[1])],
        on_result=lambda path, profile: results.append((path, profile)),
        on_progress=lambda done, total: progress.append((done, total)),
    )

    assert analyzer.calls == [(paths[0], 8.0)]
    assert repository.updated[str(paths[0])].source_size_bytes == paths[0].stat().st_size
    assert [path for path, _profile in results] == [str(paths[1]), str(paths[0])]
    assert progress == [(1, 2), (2, 2)]
    assert completed[str(paths[1])] == cached


def test_completion_force_reanalyze_bypasses_a_cached_transient_failure(tmp_path: Path) -> None:
    path = tmp_path / "timeout.flac"
    path.write_text("audio")
    repository = _Repository({str(path): _profile(LoudnessStatus.TRANSIENT_FAILURE)})
    analyzer = _Analyzer()

    LoudnessCompletionService(analyzer, engine_fingerprint="ffmpeg-test").complete(
        [TrackRecord(path=str(path), duration=8.0)], repository, force_reanalyze=True
    )

    assert repository.force_reanalyze_calls == [True]
    assert analyzer.calls == [(path, 8.0)]


def test_completion_caps_external_drive_work_and_persists_each_typed_result(tmp_path: Path) -> None:
    paths = [tmp_path / f"{name}.flac" for name in "abcd"]
    for path in paths:
        path.write_text(path.name)
    started, release, done = threading.Event(), threading.Event(), threading.Event()
    lock = threading.Lock()

    class BlockingAnalyzer(_Analyzer):
        def __init__(self) -> None:
            super().__init__()
            self.active = self.maximum = 0

        def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile:
            with lock:
                self.calls.append((path, duration_seconds))
                self.active += 1
                self.maximum = max(self.maximum, self.active)
                if self.active == 2:
                    started.set()
            release.wait(2)
            with lock:
                self.active -= 1
            return _profile(LoudnessStatus.TRANSIENT_FAILURE if path == paths[2] else LoudnessStatus.MEASURED)

    analyzer, repository = BlockingAnalyzer(), _Repository()
    service = LoudnessCompletionService(analyzer, engine_fingerprint="ffmpeg-test")
    thread = threading.Thread(
        target=lambda: (
            service.complete(
                [TrackRecord(path=str(path), duration=6.0, audio_md5="md5") for path in paths],
                repository,
                selected_paths=[str(paths[1])],
                candidate_paths=[str(paths[0])],
                visible_paths=[str(paths[3])],
            ),
            done.set(),
        )
    )
    thread.start()
    assert started.wait(1)
    assert {path for path, _duration in analyzer.calls} == {paths[0], paths[1]}
    release.set()
    assert done.wait(3)
    thread.join()

    assert analyzer.maximum == 2
    assert set(repository.updated) == {str(path) for path in paths}
    assert repository.updated[str(paths[2])].status is LoudnessStatus.TRANSIENT_FAILURE
    assert all(profile.source_mtime_ns == Path(path).stat().st_mtime_ns for path, profile in repository.updated.items())


def test_repository_updates_one_loudness_profile_without_rescanning(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")
    repository = TrackRepository(tmp_path / "library.sqlite3")
    repository.save_scan_results([TrackRecord(path=str(path))])

    assert repository.update_loudness_profile(str(path), _profile()) is True
    assert repository.list_tracks()[0].loudness_profile == _profile()


class _OrderedRepository(_Repository):
    def __init__(self, events: list[str], cache: dict[str, LoudnessProfile] | None = None) -> None:
        super().__init__(cache)
        self.events = events
        self.siblings = {"spectral": object(), "danceability": object(), "edge": object()}

    def refresh_post_metadata_identity(self, path: str) -> bool:
        self.events.append("refresh")
        return True

    def update_loudness_profile(self, path: str, profile: LoudnessProfile) -> bool:
        self.events.append("persist")
        assert self.siblings.keys() == {"spectral", "danceability", "edge"}
        return super().update_loudness_profile(path, profile)


def test_fresh_profile_writes_restamps_refreshes_siblings_then_persists(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")
    events: list[str] = []

    class EventAnalyzer(_Analyzer):
        def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile:
            events.append("analyze")
            return super().analyze(path, duration_seconds=duration_seconds)

    def write_tags(target: Path, profile: LoudnessProfile) -> LoudnessTagWriteResult:
        events.append("write")
        target.write_text(target.read_text() + " tags")
        return LoudnessTagWriteResult(LoudnessTagWriteStatus.CHANGED)

    repository = _OrderedRepository(events)
    LoudnessCompletionService(EventAnalyzer(), engine_fingerprint="ffmpeg-test", tag_writer=write_tags).complete(
        [TrackRecord(path=str(path), duration=8.0)], repository
    )

    assert events == ["analyze", "write", "refresh", "persist"]
    assert repository.updated[str(path)].source_size_bytes == path.stat().st_size
    assert repository.siblings.keys() == {"spectral", "danceability", "edge"}


def test_unchanged_write_avoids_refresh_and_cache_replay_never_calls_writer(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")
    events: list[str] = []
    writer_calls: list[Path] = []

    def unchanged(target: Path, profile: LoudnessProfile) -> LoudnessTagWriteResult:
        writer_calls.append(target)
        return LoudnessTagWriteResult(LoudnessTagWriteStatus.UNCHANGED)

    service = LoudnessCompletionService(_Analyzer(), engine_fingerprint="ffmpeg-test", tag_writer=unchanged)
    repository = _OrderedRepository(events)
    records = [TrackRecord(path=str(path), duration=8.0)]
    service.complete(records, repository)

    assert events == ["persist"]
    assert writer_calls == [path]
    cache_repository = _OrderedRepository([], {str(path): repository.updated[str(path)]})
    service.complete(records, cache_repository)
    assert writer_calls == [path]
    assert cache_repository.updated == {}


def test_tag_write_failure_restamps_and_refreshes_before_persisting_typed_failure(tmp_path: Path) -> None:
    path = tmp_path / "track.flac"
    path.write_text("audio")
    events: list[str] = []

    def partial_write(target: Path, profile: LoudnessProfile) -> LoudnessTagWriteResult:
        events.append("write")
        target.write_text(target.read_text() + " partial")
        raise RuntimeError("save interrupted")

    repository = _OrderedRepository(events)
    LoudnessCompletionService(_Analyzer(), engine_fingerprint="ffmpeg-test", tag_writer=partial_write).complete(
        [TrackRecord(path=str(path), duration=8.0)], repository
    )

    assert events == ["write", "refresh", "persist"]
    assert repository.updated[str(path)].status is LoudnessStatus.TRANSIENT_FAILURE
    assert repository.updated[str(path)].source_size_bytes == path.stat().st_size


def test_m4a_writer_exception_becomes_typed_transient_failure(tmp_path: Path) -> None:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "loudness" / "synthetic_tone_1khz_aac.m4a"
    path = tmp_path / "track.m4a"
    copyfile(fixture, path)

    def failing_writer(target: Path, profile: LoudnessProfile) -> LoudnessTagWriteResult:
        return write_loudness_tags(target, profile, save_audio=lambda _: (_ for _ in ()).throw(OSError("disk full")))

    repository = _Repository()
    service = LoudnessCompletionService(_Analyzer(), engine_fingerprint="ffmpeg-test", tag_writer=failing_writer)
    result = service.complete([TrackRecord(path=str(path), duration=8.0)], repository)

    assert result[str(path)].status is LoudnessStatus.TRANSIENT_FAILURE


def test_cancel_wins_before_late_measurement_commit_and_service_can_be_reused(tmp_path: Path) -> None:
    path = tmp_path / "late.flac"
    path.write_text("audio")
    started, release, cancelled = threading.Event(), threading.Event(), threading.Event()

    class LateAnalyzer(_Analyzer):
        def __init__(self) -> None:
            super().__init__()
            self.block = True

        def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile:
            self.calls.append((path, duration_seconds))
            started.set()
            if self.block:
                release.wait(1)
            return _profile()

        def cancel(self) -> None:
            cancelled.set()

    events: list[str] = []
    analyzer, repository = LateAnalyzer(), _OrderedRepository(events)

    def unchanged_writer(_path: Path, _profile: LoudnessProfile) -> LoudnessTagWriteResult:
        events.append("write")
        return LoudnessTagWriteResult(LoudnessTagWriteStatus.UNCHANGED)

    service = LoudnessCompletionService(analyzer, engine_fingerprint="ffmpeg-test", tag_writer=unchanged_writer)
    completed: dict[str, LoudnessProfile] = {}
    callbacks: list[str] = []
    worker = threading.Thread(
        target=lambda: completed.update(
            service.complete(
                [TrackRecord(path=str(path), duration=8.0)],
                repository,
                on_result=lambda path, _profile: callbacks.append(path),
            )
        )
    )
    worker.start()
    assert started.wait(1)
    service.cancel()
    assert cancelled.is_set()
    release.set()
    worker.join(timeout=1)

    assert worker.is_alive() is False
    assert completed == {}
    assert events == []
    assert repository.updated == {}
    assert callbacks == []

    analyzer.block = False
    next_results = service.complete([TrackRecord(path=str(path), duration=8.0)], repository)
    assert next_results[str(path)].status is LoudnessStatus.MEASURED
    assert next_results[str(path)].source_size_bytes == path.stat().st_size
    assert events == ["write", "persist"]


def test_cancel_waits_for_active_tag_commit_then_skips_remaining_records(tmp_path: Path) -> None:
    first, second, third = [tmp_path / f"{name}.flac" for name in ("first", "second", "third")]
    for path in (first, second, third):
        path.write_text("audio")
    commit_started, release_commit, cancel_called, cancel_done = (threading.Event() for _ in range(4))

    class SequencedAnalyzer(_Analyzer):
        def __init__(self) -> None:
            super().__init__()
            self._call_lock = threading.Lock()

        def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile:
            with self._call_lock:
                first_call = not self.calls
                self.calls.append((path, duration_seconds))
            if not first_call:
                cancel_called.wait(1)
            return _profile()

        def cancel(self) -> None:
            cancel_called.set()

    events: list[str] = []

    def blocking_writer(_path: Path, _profile: LoudnessProfile) -> LoudnessTagWriteResult:
        events.append("write")
        commit_started.set()
        release_commit.wait(1)
        return LoudnessTagWriteResult(LoudnessTagWriteStatus.CHANGED)

    analyzer, repository = SequencedAnalyzer(), _OrderedRepository(events)
    service = LoudnessCompletionService(analyzer, engine_fingerprint="ffmpeg-test", tag_writer=blocking_writer)
    records = [TrackRecord(path=str(path), duration=8.0) for path in (first, second, third)]
    worker = threading.Thread(target=lambda: service.complete(records, repository))
    worker.start()
    assert commit_started.wait(1)
    canceller = threading.Thread(target=lambda: (service.cancel(), cancel_done.set()))
    canceller.start()
    assert cancel_called.wait(1)
    assert cancel_done.wait(0.1) is False
    release_commit.set()
    worker.join(timeout=1)
    canceller.join(timeout=1)

    assert worker.is_alive() is canceller.is_alive() is False
    assert events == ["write", "refresh", "persist"]
    assert list(repository.updated) == [str(analyzer.calls[0][0])]
