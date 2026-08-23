from __future__ import annotations

import threading
from pathlib import Path

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_completion import LoudnessCompletionService, prioritize_records
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

    def load_loudness_profile_cache(self, paths, *, engine_fingerprint: str, force_reanalyze: bool = False):
        return {path: self.cache[path] for path in paths if path in self.cache}

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
