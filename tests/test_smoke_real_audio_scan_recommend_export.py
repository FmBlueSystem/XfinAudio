"""End-to-end smoke test using a real audio fixture with Mixed In Key-style tags.

This test automates the manual "real Mixed In Key audio QA" gate by exercising
the actual scan, persistence, recommendation, and Serato export paths against a
copy of the committed silence WAV fixture. It never writes to the user's real
Serato library or mutates the committed fixture.
"""

from __future__ import annotations

import base64
import json
import shutil
from pathlib import Path

import pytest
from mutagen.id3 import TBPM, TCON, TIT2, TKEY, TPE1, TXXX
from mutagen.wave import WAVE

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.desktop.app_state import AppState
from xfinaudio.exporting.serato_crate import parse_serato_crate_bytes, write_serato_crate
from xfinaudio.exporting.serato_playlist_exporter import plan_serato_playlist_export
from xfinaudio.library.scan_service import MetadataScanService
from xfinaudio.library.track_repository import TrackRepository

FIXTURE_PATH = Path(__file__).with_name("fixtures") / "silence_1s.wav"


def _encode_mik_tag(payload: dict[str, object]) -> str:
    """Return a base64-encoded JSON blob matching Mixed In Key's tag format."""
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _write_mik_tags(path: Path) -> None:
    """Write MIK-style metadata into a WAV file using ID3 tags."""
    audio = WAVE(path)
    if audio.tags is None:
        audio.add_tags()
    tags = audio.tags
    assert tags is not None

    tags["TIT2"] = TIT2(encoding=3, text="Smoke Track - 8A - Energy 7")
    tags["TPE1"] = TPE1(encoding=3, text="Smoke Artist")
    tags["TCON"] = TCON(encoding=3, text="House")
    tags["TBPM"] = TBPM(encoding=3, text="120.000000")
    tags["TKEY"] = TKEY(encoding=3, text="Am")
    tags["TXXX:key"] = TXXX(
        encoding=3,
        desc="key",
        text=_encode_mik_tag({"algorithm": 94, "key": "8A", "source": "mixedinkey"}),
    )
    tags["TXXX:energy"] = TXXX(
        encoding=3,
        desc="energy",
        text=_encode_mik_tag({"algorithm": 13, "energyLevel": 7, "source": "mixedinkey"}),
    )
    tags["TXXX:energylevel"] = TXXX(encoding=3, desc="energylevel", text="7")
    audio.save()


def _prepare_tracks(tmp_path: Path, names: list[str]) -> Path:
    """Copy the committed fixture into *tmp_path* with MIK-style tags."""
    audio_dir = tmp_path / "_Lossless"
    audio_dir.mkdir(parents=True)
    for name in names:
        dst = audio_dir / name
        shutil.copy(FIXTURE_PATH, dst)
        _write_mik_tags(dst)
    return audio_dir


@pytest.fixture
def smoke_audio_dir(tmp_path: Path) -> Path:
    """Temporary directory containing tagged real-audio fixtures."""
    return _prepare_tracks(tmp_path, ["A.wav", "B.wav"])


def test_real_audio_scan_persist_recommend_export(smoke_audio_dir: Path, tmp_path: Path) -> None:
    """Run the full desktop workflow end-to-end against real audio fixtures."""
    db_path = tmp_path / "smoke.db"
    repository = TrackRepository(db_path)
    scan_service = MetadataScanService()
    workflow = PlaylistWorkflowService(scan_service=scan_service, repository=repository)

    scan_result = workflow.scan_folder(smoke_audio_dir)
    assert scan_result.complete_count == 2
    assert scan_result.incomplete_count == 0

    persisted = repository.list_tracks()
    assert len(persisted) == 2
    for record in persisted:
        assert record.metadata_status == "complete"
        assert record.bpm == 120.0
        assert record.camelot_key == "8A"
        assert record.energy_level == 7

    rec_result = workflow.recommend(persisted, "build")
    recommended_paths = [track.path for track in rec_result.recommendation.ordered_tracks]
    assert len(recommended_paths) == 2

    serato_folder = tmp_path / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    plan = plan_serato_playlist_export("Smoke Set", rec_result.recommendation, serato_folder)
    write_result = write_serato_crate(plan, confirm=True)

    assert write_result.validated is True
    parsed = parse_serato_crate_bytes(write_result.written_path.read_bytes())
    assert parsed.paths == plan.relative_paths
    assert len(parsed.paths) == 2
    for path in parsed.paths:
        assert path.startswith("_Lossless/")
        assert path.endswith(".wav")


def test_real_audio_scan_populates_app_state(smoke_audio_dir: Path, tmp_path: Path) -> None:
    """Verify scanned records can be loaded into the immutable AppState model."""
    repository = TrackRepository(tmp_path / "state.db")
    workflow = PlaylistWorkflowService(scan_service=MetadataScanService(), repository=repository)

    workflow.scan_folder(smoke_audio_dir)
    state = AppState(scanned_records=repository.list_display_tracks())

    assert len(state.scanned_records) == 2
    assert all(record.metadata_status == "complete" for record in state.scanned_records)
