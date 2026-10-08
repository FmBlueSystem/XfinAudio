"""Unreadable persisted payloads and parser probes must not fail silently.

Historically `track_repository._deserialize_*_profile` swallowed every failure with a bare
`except Exception: return None`, and `scan_service.read_mutagen_tags` swallowed a failed
audio-MD5 probe with `except Exception: pass`. A database row holding unreadable profile
JSON, or a mutagen info object exposing a non-numeric `md5_signature`, therefore degraded to
"no analysis" with no log line and no way for a maintainer to tell a corrupt row from a track
that was never analysed. These tests pin the operator-visible signal instead.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path

import pytest

from xfinaudio.library import scan_service, track_repository
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.track_repository import TrackRepository

REPOSITORY_LOGGER = "xfinaudio.library.track_repository"
SCAN_SERVICE_LOGGER = "xfinaudio.library.scan_service"
TRACK_PATH = "/music/broken.flac"


@pytest.mark.parametrize(
    ("deserializer_name", "label"),
    [
        ("_deserialize_profile", "spectral profile"),
        ("_deserialize_danceability_profile", "danceability profile"),
        ("_deserialize_edge_spectral_profile", "edge spectral profile"),
        ("_deserialize_tonal_profile", "tonal profile"),
        ("_deserialize_loudness_profile", "loudness profile"),
    ],
)
def test_unreadable_profile_payload_is_logged_with_the_track_path(
    deserializer_name: str, label: str, caplog: pytest.LogCaptureFixture
) -> None:
    deserializer = getattr(track_repository, deserializer_name)

    with caplog.at_level(logging.WARNING, logger=REPOSITORY_LOGGER):
        assert deserializer("{not json", path=TRACK_PATH) is None

    messages = [record.getMessage() for record in caplog.records]
    assert any(label in message and TRACK_PATH in message for message in messages), messages


def test_unreadable_loudness_payload_is_logged_through_the_freshness_wrapper(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger=REPOSITORY_LOGGER):
        profile = track_repository._deserialize_current_loudness_profile(  # noqa: SLF001
            "[]", path=TRACK_PATH, source_mtime_ns=None, source_size_bytes=None
        )

    assert profile is None
    assert any("loudness profile" in record.getMessage() for record in caplog.records)


def test_corrupt_spectral_profile_row_is_reported_when_reading_the_library(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    repository = TrackRepository(tmp_path / "xfinaudio.sqlite3")
    repository.save_scan_results([TrackRecord(path=TRACK_PATH)])
    partially_written_payload = json.dumps({"red_ratio": 0.9})
    with sqlite3.connect(repository.db_path) as connection:
        connection.execute(
            "UPDATE tracks SET spectral_profile_json = ? WHERE path = ?",
            (partially_written_payload, TRACK_PATH),
        )

    with caplog.at_level(logging.WARNING, logger=REPOSITORY_LOGGER):
        record = repository.list_tracks()[0]

    assert record.spectral_profile is None
    assert TRACK_PATH in caplog.text
    assert "spectral profile" in caplog.text


class _UnreadableSignatureInfo:
    """Mutagen info shim whose declared MD5 signature cannot be formatted as hex."""

    length = 1.0
    bitrate = 320_000
    md5_signature = "not-an-integer"


class _StubAudio:
    """Minimal mutagen file stand-in: no tags, one unreadable MD5 signature."""

    tags: dict[str, object] = {}
    info = _UnreadableSignatureInfo()


def test_unreadable_audio_md5_signature_is_logged(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(scan_service, "MutagenFile", lambda *_args, **_kwargs: _StubAudio())

    with caplog.at_level(logging.WARNING, logger=SCAN_SERVICE_LOGGER):
        tags = scan_service.read_mutagen_tags(Path("/music/broken.mp3"))

    assert tags is not None
    assert "__audio_md5__" not in tags
    assert "/music/broken.mp3" in caplog.text
