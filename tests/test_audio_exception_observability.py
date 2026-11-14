"""Analysis failures swallowed by broad handlers must still record their cause.

S6 (audit point 4, "Fallas de análisis de audio invisibles"): the broad ``except
Exception`` handlers in ``audio/spectral_profile.py``, ``audio/tonal_profile.py``,
``audio/danceability.py`` and ``audio/loudness_completion.py`` returned ``None`` or a
transient failure without one log line, so a library full of unreadable files looked
exactly like a library nobody had analysed. These tests pin the recorded cause -- track
path, exception type and exception message -- while keeping the public return values.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import numpy as np
import pytest

from xfinaudio.audio import danceability, spectral_profile, tonal_profile
from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_completion import LoudnessCompletionService
from xfinaudio.audio.loudness_tags import LoudnessTagWriteResult
from xfinaudio.library.models import TrackRecord

MISSING_TRACK = Path("/music/never-read.flac")
SYNTHETIC_RED_TRACK = Path(__file__).resolve().parents[1] / "assets" / "synthetic_color_tests" / "red_100hz.wav"
LOUDNESS_LOGGER = "xfinaudio.audio.loudness_completion"

ANALYSIS_FAILURE_CASES = [
    pytest.param(spectral_profile, "analyze_spectral_profile", id="spectral"),
    pytest.param(spectral_profile, "analyze_edge_spectral_profile", id="edge-spectral"),
    pytest.param(tonal_profile, "analyze_tonal_profile", id="tonal"),
    pytest.param(danceability, "analyze_danceability", id="danceability"),
]

DURATION_PROBE_CASES = ANALYSIS_FAILURE_CASES[:1] + ANALYSIS_FAILURE_CASES[2:]


def _analyzer(module: ModuleType, name: str) -> Callable[..., Any]:
    return getattr(module, name)


def _written_track(tmp_path: Path) -> Path:
    track = tmp_path / "track.flac"
    track.write_bytes(b"not audio")
    return track


def _cause_messages(caplog: pytest.LogCaptureFixture, logger_name: str) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.name == logger_name]


def _patch_decoding_failure(monkeypatch: pytest.MonkeyPatch, *, duration: float = 120.0) -> None:
    """Resolve the duration, then fail the decode itself."""
    import librosa

    monkeypatch.setattr(librosa, "get_duration", lambda **_kwargs: duration, raising=False)

    def _fail(*_args: object, **_kwargs: object) -> Any:
        raise RuntimeError("decoder exploded")

    monkeypatch.setattr(librosa, "load", _fail, raising=False)


@pytest.mark.parametrize(("module", "analyze_name"), ANALYSIS_FAILURE_CASES)
def test_audio_analysis_failure_is_logged_with_the_track_path_and_cause(
    module: ModuleType,
    analyze_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    track = _written_track(tmp_path)
    _patch_decoding_failure(monkeypatch)

    with caplog.at_level(logging.WARNING, logger=module.__name__):
        assert _analyzer(module, analyze_name)(track) is None

    messages = _cause_messages(caplog, module.__name__)
    assert any(
        str(track) in message and "RuntimeError" in message and "decoder exploded" in message for message in messages
    ), messages


@pytest.mark.parametrize(("module", "analyze_name"), ANALYSIS_FAILURE_CASES)
def test_missing_librosa_dependency_is_logged(
    module: ModuleType,
    analyze_name: str,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setitem(sys.modules, "librosa", None)

    with caplog.at_level(logging.WARNING, logger=module.__name__):
        assert _analyzer(module, analyze_name)(MISSING_TRACK) is None

    messages = _cause_messages(caplog, module.__name__)
    assert any(str(MISSING_TRACK) in message and "ModuleNotFoundError" in message for message in messages), messages


@pytest.mark.parametrize(("module", "analyze_name"), DURATION_PROBE_CASES)
def test_duration_probe_failure_is_logged_and_analysis_continues(
    module: ModuleType,
    analyze_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    import librosa

    track = _written_track(tmp_path)

    def _fail(**_kwargs: object) -> float:
        raise ValueError("no duration in header")

    monkeypatch.setattr(librosa, "get_duration", _fail, raising=False)
    monkeypatch.setattr(
        librosa, "load", lambda *_args, **_kwargs: (np.empty(0, dtype=np.float32), 22050), raising=False
    )

    with caplog.at_level(logging.WARNING, logger=module.__name__):
        assert _analyzer(module, analyze_name)(track) is None

    messages = _cause_messages(caplog, module.__name__)
    assert any(
        str(track) in message and "ValueError" in message and "no duration in header" in message for message in messages
    ), messages


def _loudness_profile(status: LoudnessStatus = LoudnessStatus.MEASURED) -> LoudnessProfile:
    measured = status is LoudnessStatus.MEASURED
    return LoudnessProfile(
        lufs_integrated=-10.0 if measured else None,
        loudness_range_lra=4.0 if measured else None,
        true_peak_dbtp=-1.0 if measured else None,
        status=status,
        engine_fingerprint="ffmpeg-test",
    )


class _Repository:
    """Minimal loudness cache port: no cached profiles, records the writes."""

    def __init__(self) -> None:
        self.updated: dict[str, LoudnessProfile] = {}

    def load_loudness_profile_cache(
        self, paths: Any, *, engine_fingerprint: str, force_reanalyze: bool = False
    ) -> dict[str, LoudnessProfile]:
        return {}

    def refresh_post_metadata_identity(self, path: str) -> bool:
        return True

    def update_loudness_profile(self, path: str, profile: LoudnessProfile) -> bool:
        self.updated[path] = profile
        return True


class _Analyzer:
    def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile:
        return _loudness_profile()


class _RaisingAnalyzer:
    def analyze(self, path: Path, *, duration_seconds: float) -> LoudnessProfile:
        raise RuntimeError("ffmpeg produced no output")


def _raising_tag_writer(path: Path, profile: LoudnessProfile) -> LoudnessTagWriteResult:
    raise PermissionError("tags are read-only")


def test_loudness_analyzer_failure_is_logged_and_stays_a_transient_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    track = tmp_path / "noisy.flac"
    track.write_bytes(b"audio")
    repository = _Repository()

    with caplog.at_level(logging.WARNING, logger=LOUDNESS_LOGGER):
        completed = LoudnessCompletionService(_RaisingAnalyzer(), engine_fingerprint="ffmpeg-test").complete(
            [TrackRecord(path=str(track), duration=8.0)], repository
        )

    profile = completed[str(track)]
    assert profile.status is LoudnessStatus.TRANSIENT_FAILURE
    assert profile.lufs_integrated is None
    assert repository.updated[str(track)].status is LoudnessStatus.TRANSIENT_FAILURE
    messages = _cause_messages(caplog, LOUDNESS_LOGGER)
    assert any(
        str(track) in message and "RuntimeError" in message and "ffmpeg produced no output" in message
        for message in messages
    ), messages


def test_loudness_tag_write_failure_is_logged_and_stays_a_transient_failure(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    track = tmp_path / "readonly.flac"
    track.write_bytes(b"audio")
    repository = _Repository()

    with caplog.at_level(logging.WARNING, logger=LOUDNESS_LOGGER):
        completed = LoudnessCompletionService(
            _Analyzer(), engine_fingerprint="ffmpeg-test", tag_writer=_raising_tag_writer
        ).complete([TrackRecord(path=str(track), duration=8.0)], repository)

    profile = completed[str(track)]
    assert profile.status is LoudnessStatus.TRANSIENT_FAILURE
    assert profile.lufs_integrated is None
    messages = _cause_messages(caplog, LOUDNESS_LOGGER)
    assert any(
        str(track) in message and "PermissionError" in message and "tags are read-only" in message
        for message in messages
    ), messages


def test_successful_spectral_analysis_still_returns_the_same_profile() -> None:
    """Recording the cause must not disturb the path where nothing fails."""
    profile = spectral_profile.analyze_spectral_profile(SYNTHETIC_RED_TRACK)

    assert profile == spectral_profile.SpectralProfile(
        red_ratio=0.9982118606567383,
        green_ratio=0.001737726153805852,
        blue_ratio=5.050602339906618e-05,
        centroid_hz=102.16331186323613,
        rolloff_hz=108.16446940104167,
        rms=0.21613404154777527,
        dominant_color="RED",
        analysis_version=2,
    )
