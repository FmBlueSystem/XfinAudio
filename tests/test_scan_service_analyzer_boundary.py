"""Tests for scan-service spectral analyzer injection."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from xfinaudio.audio.spectral_profile import SpectralProfile
from xfinaudio.library.scan_service import MetadataScanService, scan_folder


class FakeSpectralAnalyzer:
    def __init__(self) -> None:
        self.paths: list[Path] = []
        self._lock = Lock()

    def analyze(self, path: Path) -> SpectralProfile:
        with self._lock:
            self.paths.append(path)
        return SpectralProfile(red_ratio=0.0, green_ratio=1.0, blue_ratio=0.0, dominant_color="GREEN")


def test_scan_folder_uses_injected_spectral_analyzer() -> None:
    path = Path("/music/a.flac")
    analyzer = FakeSpectralAnalyzer()

    records = scan_folder(
        Path("/music"),
        list_paths=lambda _: [path],
        read_tags=lambda _: {"title": ["A"], "artist": ["Artist"], "bpm": ["120"], "initialkey": ["8A"]},
        spectral_analyzer=analyzer,
    )

    assert analyzer.paths == [path]
    assert records[0].spectral_profile is not None
    assert records[0].spectral_profile.dominant_color == "GREEN"


def _tags(title: str) -> dict[str, list[str]]:
    return {"title": [title], "artist": ["Artist"], "bpm": ["120"], "initialkey": ["8A"]}


def test_scan_folder_parallel_analysis_uses_injected_spectral_analyzer() -> None:
    paths = [Path("/music/a.flac"), Path("/music/b.flac")]
    analyzer = FakeSpectralAnalyzer()

    records = scan_folder(
        Path("/music"),
        list_paths=lambda _: paths,
        read_tags=lambda path: _tags(path.stem.upper()),
        parallel_spectral_analysis=True,
        spectral_max_workers=2,
        spectral_analyzer=analyzer,
    )

    assert sorted(analyzer.paths, key=str) == paths
    assert [record.spectral_profile.dominant_color for record in records if record.spectral_profile] == [
        "GREEN",
        "GREEN",
    ]


def test_metadata_scan_service_passes_injected_spectral_analyzer() -> None:
    paths = [Path("/music/a.flac"), Path("/music/b.flac")]
    analyzer = FakeSpectralAnalyzer()

    records = MetadataScanService().scan(
        Path("/music"),
        list_paths=lambda _: paths,
        read_tags=lambda path: _tags(path.stem.upper()),
        parallel_spectral_analysis=True,
        spectral_max_workers=2,
        spectral_analyzer=analyzer,
    )

    assert sorted(analyzer.paths, key=str) == paths
    assert all(record.spectral_profile is not None for record in records)
