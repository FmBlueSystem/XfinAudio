"""Profiles status: pending counts per analysis and a measured remaining time (S2)."""

from __future__ import annotations

import threading
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast

import pytest

from xfinaudio.headless import profiles as profiles_module
from xfinaudio.headless.profiles import ProfileCompletion
from xfinaudio.library.scan_service import ScanCancellationToken

if TYPE_CHECKING:
    from xfinaudio.headless.backend import HeadlessBackend

# Any positive version stamps the fake profiles; the stage tuple supplies the expected one.
VERSION = 1


class _Clock:
    """A deterministic monotonic clock the analyzers advance per decoded track."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seconds = 0.0

    def now(self) -> float:
        with self._lock:
            return self._seconds

    def advance(self, seconds: float) -> None:
        with self._lock:
            self._seconds += seconds


class _Sink:
    """Stands in for the derived contexts the completion retires."""

    def __init__(self) -> None:
        self.invalidations = 0

    def invalidate(self) -> None:
        self.invalidations += 1


class _Repository:
    """Persists a fake profile by writing the same field the library reader would store."""

    def __init__(self, records: list[SimpleNamespace]) -> None:
        self.records = records
        self.saved: list[tuple[str, str]] = []

    def _save(self, field: str, path: str, profile: object) -> bool:
        for record in self.records:
            if record.path == path:
                setattr(record, field, profile)
                self.saved.append((field, path))
                return True
        return False

    def update_spectral_profile(self, path: str, profile: object, *, expected_file_identity: object) -> bool:
        assert expected_file_identity is not None
        return self._save("spectral_profile", path, profile)

    def update_danceability_profile(self, path: str, profile: object, *, expected_file_identity: object) -> bool:
        assert expected_file_identity is not None
        return self._save("danceability_profile", path, profile)

    def update_edge_spectral_profile(self, path: str, profile: object, *, expected_file_identity: object) -> bool:
        assert expected_file_identity is not None
        return self._save("edge_spectral_profile", path, profile)


class _Backend:
    """The narrow surface ``ProfileCompletion`` reads from the headless backend."""

    def __init__(self, records: list[SimpleNamespace], root: Path) -> None:
        self.records = records
        self.roots = [root]
        self.repository = _Repository(records)
        self.editor = _Sink()
        self.live = _Sink()
        self.loudness = _Sink()
        self.preferences = SimpleNamespace(get_profiles=lambda: {}, update_profiles=lambda params: params)

    def _records(self) -> list[SimpleNamespace]:
        return list(self.records)

    def _library(self) -> dict[str, Any]:
        return {"tracks": [], "count": len(self.records)}

    def invalidate_review(self) -> None:
        pass

    def invalidate_optional_ai(self) -> None:
        pass


def _record(path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        path=str(path),
        spectral_profile=None,
        danceability_profile=None,
        edge_spectral_profile=None,
    )


def _analyzer(clock: _Clock, *, cancel: ScanCancellationToken | None = None) -> type:
    """A zero-argument adapter whose analysis costs a deterministic two seconds."""

    class Analyzer:
        def analyze(self, path: Path) -> SimpleNamespace:
            clock.advance(2.0)
            if cancel is not None:
                cancel.cancel()
            return SimpleNamespace(analysis_version=VERSION, source=str(path))

    return Analyzer


def _stages(clock: _Clock, cancel: ScanCancellationToken | None = None) -> tuple:
    return (
        ("spectral", "spectral_profile", VERSION, _analyzer(clock)),
        ("danceability", "danceability_profile", VERSION, _analyzer(clock, cancel=cancel)),
        ("edge", "edge_spectral_profile", VERSION, _analyzer(clock)),
    )


def _library(tmp_path: Path, count: int) -> tuple[Path, list[SimpleNamespace]]:
    root = tmp_path.resolve()
    records = []
    for index in range(count):
        path = root / f"{index}.flac"
        path.write_bytes(b"fLaC")
        records.append(_record(path))
    return root, records


def _completion(backend: _Backend) -> ProfileCompletion:
    """The orchestration only reads the narrow backend surface this test stands in for."""
    return ProfileCompletion(cast("HeadlessBackend", backend))


def test_status_reports_pending_counts_per_analysis_and_keeps_the_summary_fields(tmp_path: Path) -> None:
    root, records = _library(tmp_path, 4)
    stored = SimpleNamespace(analysis_version=VERSION)
    for record in records:
        record.spectral_profile = stored
    records[0].danceability_profile = stored
    status = _completion(_Backend(records, root)).status()

    assert status["spectralReadyCount"] == 4
    assert status["spectralPendingCount"] == 0
    assert status["danceabilityReadyCount"] == 1
    assert status["danceabilityPendingCount"] == 3
    assert status["edgeReadyCount"] == 0
    assert status["edgePendingCount"] == 4
    # The summary fields that already shipped keep their meaning.
    assert status["state"] == "idle"
    assert status["totalTracks"] == 4
    assert status["readyCount"] == 0
    assert status["pendingCount"] == 4
    assert status["failedCount"] == 0
    # Nothing has been measured yet, so no remaining time is invented.
    assert status["estimatedRemainingSeconds"] is None


def test_status_estimates_the_remaining_time_from_measured_per_track_time(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root, records = _library(tmp_path, 2)
    clock = _Clock()
    token = ScanCancellationToken()
    monkeypatch.setattr(profiles_module, "STAGES", _stages(clock, token))
    monkeypatch.setattr(profiles_module, "_clock", clock.now)
    monkeypatch.setattr(profiles_module, "dependencies_available", lambda: True)
    completion = _completion(_Backend(records, root))
    assert completion.status()["estimatedRemainingSeconds"] is None

    progress: list[dict[str, Any]] = []
    result = completion.execute("profiles.complete", {}, token, progress.append)

    status = result["status"]
    assert result["cancelled"] is True
    # The spectral pass measured two decoded tracks at two seconds each.
    assert status["spectralPendingCount"] == 0
    assert status["danceabilityPendingCount"] == 2
    assert status["edgePendingCount"] == 2
    assert status["estimatedRemainingSeconds"] == 8
    assert progress[0]["estimatedRemainingSeconds"] is None
    started = [event for event in progress if event["stage"] == "danceability" and event["processedCount"] == 0]
    assert started
    assert started[0]["estimatedRemainingSeconds"] == 8
