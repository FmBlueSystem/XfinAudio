"""Actual fixture metadata writes stay on confirmed descriptors with original-byte backups."""

import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.loudness_tags import LoudnessTagWriteStatus
from xfinaudio.headless.loudness_write import BoundLoudnessWriter, bind_source

FIXTURE = Path(__file__).resolve().parents[1] / "desktop-electron/tests/fixtures/music"


def copied(tmp_path):
    path = tmp_path / "music" / "sample.flac"
    path.parent.mkdir()
    shutil.copyfile(next(FIXTURE.glob("*.flac")), path)
    return path


def measured():
    return LoudnessProfile(
        lufs_integrated=-11.0,
        loudness_range_lra=4.0,
        true_peak_dbtp=-2.0,
        status=LoudnessStatus.MEASURED,
        engine_fingerprint="fixture-measurement",
    )


def test_changed_write_uses_actual_tag_writer_and_keeps_exact_original(tmp_path):
    path = copied(tmp_path)
    before = path.read_bytes()
    data = tmp_path / "data"
    data.mkdir()
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    result = writer(path, measured())
    assert result.status is LoudnessTagWriteStatus.CHANGED
    assert writer.changed_count == 1
    assert len(writer.backups) == 1
    assert writer.backups[0].read_bytes() == before
    tags = FLAC(path)
    assert tags["COMMENT"] == ["-11.0 LUFS · 4.0 LRA · -2.0 dBTP"]
    assert tags.info.md5_signature == FLAC(writer.backups[0]).info.md5_signature
    current = path.read_bytes()
    again = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    assert again(path, measured()).status is LoudnessTagWriteStatus.UNCHANGED
    assert path.read_bytes() == current
    assert not again.backups


@pytest.mark.parametrize("change", ["contents", "symlink", "parent"])
def test_changed_or_redirected_source_is_rejected_before_audio_mutation(tmp_path, change):
    path = copied(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    outside = tmp_path / "outside.flac"
    shutil.copyfile(path, outside)
    before = outside.read_bytes()
    if change == "contents":
        tags = FLAC(path)
        tags["COMMENT"] = ["new operator metadata"]
        tags.save()
    elif change == "symlink":
        path.unlink()
        path.symlink_to(outside)
    else:
        path.parent.rename(tmp_path / "retired")
        path.parent.symlink_to(tmp_path / "retired", target_is_directory=True)
    state = path.read_bytes()
    with pytest.raises(OSError):
        writer(path, measured())
    assert path.read_bytes() == state
    assert outside.read_bytes() == before
    assert not writer.backups


def test_backup_symlink_or_copy_failure_cannot_start_tag_write(tmp_path):
    path = copied(tmp_path)
    before = path.read_bytes()
    data = tmp_path / "data"
    data.mkdir()
    outside = tmp_path / "external"
    outside.mkdir()
    (data / "loudness-backups").symlink_to(outside, target_is_directory=True)
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    with pytest.raises(OSError):
        writer(path, measured())
    assert path.read_bytes() == before
    assert list(outside.iterdir()) == []


def test_incomplete_measurement_never_writes_or_creates_a_backup(tmp_path):
    path = copied(tmp_path)
    before = path.read_bytes()
    data = tmp_path / "data"
    data.mkdir()
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    result = writer(path, measured().model_copy(update={"status": LoudnessStatus.TOO_SHORT}))
    assert result.status is LoudnessTagWriteStatus.UNSUPPORTED
    assert path.read_bytes() == before
    assert not writer.backups


def test_changed_path_after_backup_cannot_redirect_confirmed_descriptor_write(tmp_path, monkeypatch):
    path = copied(tmp_path)
    data = tmp_path / "data"
    data.mkdir()
    before = path.read_bytes()
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    backup = writer._backup
    retired = path.with_name("retired.flac")

    def replace_after_backup(*args):
        backup(*args)
        path.rename(retired)
        path.write_bytes(b"new operator file")

    monkeypatch.setattr(writer, "_backup", replace_after_backup)
    with pytest.raises(OSError):
        writer(path, measured())
    assert path.read_bytes() == b"new operator file"
    assert retired.read_bytes() == before
    assert writer.backups[0].read_bytes() == before


def test_partial_save_failure_retains_original_backup_for_recovery(tmp_path, monkeypatch):
    import xfinaudio.headless.loudness_write as module

    path = copied(tmp_path)
    before = path.read_bytes()
    data = tmp_path / "data"
    data.mkdir()
    original = module.MutagenFile

    def broken_audio(**kwargs):
        audio = original(**kwargs)

        def save(*, fileobj):
            fileobj.seek(0)
            fileobj.write(b"broken")
            fileobj.flush()
            raise OSError("simulated incomplete disk commit")

        audio.save = save
        return audio

    monkeypatch.setattr(module, "MutagenFile", broken_audio)
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    with pytest.raises(OSError):
        writer(path, measured())
    assert writer.failed_count == 1 and writer.changed_count == 0
    assert len(writer.backups) == 1 and writer.backups[0].read_bytes() == before


def test_backup_manifest_maps_original_path_and_exact_bytes_for_recovery(tmp_path):
    import hashlib
    import json

    path = copied(tmp_path)
    before = path.read_bytes()
    data = tmp_path / "data"
    data.mkdir()
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    writer(path, measured())
    manifest = json.loads(writer.backups[0].with_name(writer.backups[0].name + ".json").read_text())
    assert manifest == {
        "schema": 1,
        "originalPath": str(path),
        "originalBytes": len(before),
        "sha256": hashlib.sha256(before).hexdigest(),
        "backupFile": writer.backups[0].name,
    }


@pytest.mark.parametrize(
    "filename", ["synthetic_tone_1khz.wav", "synthetic_tone_1khz_aac.m4a", "synthetic_tone_1khz_alac.m4a"]
)
def test_descriptor_writer_supports_existing_real_wav_and_mp4_fixtures(tmp_path, filename):
    source = Path(__file__).resolve().parents[1] / "tests/fixtures/loudness" / filename
    source_before = source.read_bytes()
    path = tmp_path / filename
    shutil.copyfile(source, path)
    data = tmp_path / "data"
    data.mkdir()
    writer = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    assert writer(path, measured()).status is LoudnessTagWriteStatus.CHANGED
    assert len(writer.backups) == 1 and writer.backups[0].read_bytes() == source_before
    assert source.read_bytes() == source_before
    again = BoundLoudnessWriter(data, {str(path): bind_source(path)})
    assert again(path, measured()).status is LoudnessTagWriteStatus.UNCHANGED
    assert not again.backups
