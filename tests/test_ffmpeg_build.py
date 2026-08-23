from __future__ import annotations

import hashlib
import importlib.util
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT_PATH = PROJECT_ROOT / "scripts" / "build_ffmpeg_universal.py"

_build_spec = importlib.util.spec_from_file_location("build_ffmpeg_universal", BUILD_SCRIPT_PATH)
assert _build_spec is not None
assert _build_spec.loader is not None
ffmpeg_build = importlib.util.module_from_spec(_build_spec)
sys.modules[_build_spec.name] = ffmpeg_build
_build_spec.loader.exec_module(ffmpeg_build)


def _source_archive(path: Path) -> None:
    source_root = path.parent / "source" / "ffmpeg-7.1.1"
    source_root.mkdir(parents=True)
    (source_root / "configure").write_text("#!/bin/sh\n", encoding="utf-8")
    with tarfile.open(path, "w:xz") as archive:
        archive.add(source_root, arcname="ffmpeg-7.1.1")


def test_source_manifest_pins_the_official_archive_checksum_and_signature() -> None:
    manifest = ffmpeg_build.FFMPEG_SOURCE

    assert manifest.archive_url == "https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz"
    assert manifest.archive_sha256 == "733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1"
    assert manifest.signature_url == "https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz.asc"


def test_safe_extract_rejects_linked_archive_members(tmp_path: Path) -> None:
    archive_path = tmp_path / "ffmpeg.tar.xz"
    with tarfile.open(archive_path, "w:xz") as archive:
        linked = tarfile.TarInfo("ffmpeg-7.1.1/linked")
        linked.type = tarfile.SYMTYPE
        linked.linkname = "/outside"
        archive.addfile(linked)

    with pytest.raises(ffmpeg_build.BuildError, match="unsafe archive member"):
        ffmpeg_build.extract_source(archive_path, tmp_path / "extract", "ffmpeg-7.1.1")


def test_builds_universal_binary_and_validates_ebur128_capability(tmp_path: Path) -> None:
    archive_path = tmp_path / "fixture.tar.xz"
    _source_archive(archive_path)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    manifest = ffmpeg_build.FfmpegSourceManifest(
        archive_url="https://fixture.invalid/ffmpeg.tar.xz",
        archive_sha256=checksum,
        signature_url="https://fixture.invalid/ffmpeg.tar.xz.asc",
        source_directory="ffmpeg-7.1.1",
    )
    commands: list[tuple[str, ...]] = []

    def download(url: str, destination: Path) -> None:
        if url.endswith(".asc"):
            destination.write_text("signature", encoding="utf-8")
        else:
            destination.write_bytes(archive_path.read_bytes())

    def run(command: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        if command[0] == "make":
            binary = cwd / "ffmpeg"
            binary.write_text("binary", encoding="utf-8")
            binary.chmod(0o755)
        if command[:2] == ("lipo", "-create"):
            Path(command[command.index("-output") + 1]).write_text("universal", encoding="utf-8")
        stdout = ""
        if command[-1] == "-filters":
            stdout = " ... ebur128 ..."
        elif command[-1] == "filter=ebur128":
            stdout = "peak <int> enable true peak"
        elif command[-1] == "-demuxers":
            stdout = " D  mov,mp4,m4a,3gp,3g2,mj2 QuickTime / MOV"
        elif command[-1] == "-decoders":
            stdout = " A....D aac AAC\n A....D alac ALAC"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    output = ffmpeg_build.build_universal_ffmpeg(tmp_path / "work", tmp_path / "ffmpeg", manifest, download, run)

    assert output.is_file()
    assert output.stat().st_mode & 0o111
    assert {command[0] for command in commands} >= {"./configure", "make", "lipo"}
    assert any(command[0].endswith(".ffmpeg.staging") for command in commands)
    assert any("--arch=arm64" in command for command in commands)
    assert any("--arch=x86_64" in command for command in commands)
    assert any("--enable-filter=ebur128" in command for command in commands)
    assert any("--enable-encoder=pcm_s16le" in command for command in commands)
    assert any("--enable-demuxer=mov" in command for command in commands)
    assert any("--enable-decoder=aac" in command and "--enable-decoder=alac" in command for command in commands)
    assert any("--extra-cflags=-arch arm64 -mmacosx-version-min=11.0" in command for command in commands)
    assert any("--extra-ldflags=-arch x86_64 -mmacosx-version-min=11.0" in command for command in commands)
    assert ("lipo", str(output.with_name(f".{output.name}.staging")), "-verify_arch", "arm64", "x86_64") in commands


def test_failed_staging_validation_preserves_existing_output(tmp_path: Path) -> None:
    archive_path = tmp_path / "fixture.tar.xz"
    _source_archive(archive_path)
    manifest = ffmpeg_build.FfmpegSourceManifest(
        "https://fixture.invalid/ffmpeg.tar.xz",
        hashlib.sha256(archive_path.read_bytes()).hexdigest(),
        "https://fixture.invalid/ffmpeg.tar.xz.asc",
        "ffmpeg-7.1.1",
    )
    output = tmp_path / "ffmpeg"
    output.write_text("prior", encoding="utf-8")
    output.chmod(0o755)

    def download(_url: str, destination: Path) -> None:
        destination.write_bytes(archive_path.read_bytes())

    def run(command: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
        if command[0] == "make":
            (cwd / "ffmpeg").write_text("architecture", encoding="utf-8")
        elif command[:2] == ("lipo", "-create"):
            Path(command[command.index("-output") + 1]).write_text("replacement", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    with pytest.raises(ffmpeg_build.BuildError, match="ebur128"):
        ffmpeg_build.build_universal_ffmpeg(tmp_path / "work", output, manifest, download, run)

    assert output.read_text(encoding="utf-8") == "prior"
    assert list(tmp_path.glob(".ffmpeg.*.staging")) == []


def test_build_refuses_checksum_mismatch_before_running_tools(tmp_path: Path) -> None:
    archive_path = tmp_path / "fixture.tar.xz"
    _source_archive(archive_path)
    called = False

    def download(_url: str, destination: Path) -> None:
        destination.write_bytes(archive_path.read_bytes())

    def run(_command: tuple[str, ...], _cwd: Path) -> subprocess.CompletedProcess[str]:
        nonlocal called
        called = True
        return subprocess.CompletedProcess([], 0, stdout="", stderr="")

    with pytest.raises(ffmpeg_build.BuildError, match="checksum"):
        ffmpeg_build.build_universal_ffmpeg(
            tmp_path / "work", tmp_path / "ffmpeg", ffmpeg_build.FFMPEG_SOURCE, download, run
        )

    assert called is False


def test_binary_validation_fails_closed_without_m4a_decode_capabilities(tmp_path: Path) -> None:
    binary = tmp_path / "ffmpeg"
    binary.write_text("fixture", encoding="utf-8")
    binary.chmod(0o755)

    def run(command: tuple[str, ...], _cwd: Path) -> subprocess.CompletedProcess[str]:
        output = {
            "-filters": " ... ebur128 ...",
            "filter=ebur128": "peak <int> enable true peak",
            "-demuxers": " D  wav",
            "-decoders": " A....D mp3",
        }.get(command[-1], "ffmpeg version 7.1.1")
        return subprocess.CompletedProcess(command, 0, stdout=output, stderr="")

    required_m4a_flags = {"--enable-demuxer=mov", "--enable-decoder=aac", "--enable-decoder=alac"}
    assert required_m4a_flags <= set(ffmpeg_build.CONFIGURE_FLAGS)
    with pytest.raises(ffmpeg_build.BuildError, match="M4A"):
        ffmpeg_build._validate_binary(binary, run)
