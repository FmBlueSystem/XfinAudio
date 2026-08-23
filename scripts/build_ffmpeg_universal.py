#!/usr/bin/env python3
"""Build the pinned LGPL FFmpeg source into a macOS universal2 executable."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import shutil
import subprocess
import tarfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath


@dataclass(frozen=True)
class FfmpegSourceManifest:
    archive_url: str
    archive_sha256: str
    signature_url: str
    source_directory: str


FFMPEG_SOURCE = FfmpegSourceManifest(
    archive_url="https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz",
    archive_sha256="733984395e0dbbe5c046abda2dc49a5544e7e0e1e2366bba849222ae9e3a03b1",
    signature_url="https://ffmpeg.org/releases/ffmpeg-7.1.1.tar.xz.asc",
    source_directory="ffmpeg-7.1.1",
)
ARCHITECTURES = ("arm64", "x86_64")
MACOS_DEPLOYMENT_TARGET = "11.0"
CONFIGURE_FLAGS = (
    "--disable-everything",
    "--disable-gpl",
    "--disable-nonfree",
    "--disable-network",
    "--disable-doc",
    "--disable-debug",
    "--disable-autodetect",
    "--enable-ffmpeg",
    "--disable-ffprobe",
    "--enable-avcodec",
    "--enable-avformat",
    "--enable-avfilter",
    "--enable-avutil",
    "--enable-protocol=file",
    "--enable-demuxer=aiff",
    "--enable-demuxer=flac",
    "--enable-demuxer=mp3",
    "--enable-demuxer=mov",
    "--enable-demuxer=wav",
    "--enable-decoder=flac",
    "--enable-decoder=aac",
    "--enable-decoder=alac",
    "--enable-decoder=mp3",
    "--enable-decoder=pcm_s16be",
    "--enable-decoder=pcm_s16le",
    "--enable-decoder=pcm_s24be",
    "--enable-decoder=pcm_s24le",
    "--enable-decoder=pcm_s32be",
    "--enable-decoder=pcm_s32le",
    "--enable-filter=ebur128",
    "--enable-filter=aformat",
    "--enable-filter=aresample",
    "--enable-muxer=null",
    "--enable-encoder=pcm_s16le",
    "--enable-encoder=wrapped_avframe",
)

Run = Callable[[tuple[str, ...], Path], subprocess.CompletedProcess[str]]
Download = Callable[[str, Path], None]


class BuildError(RuntimeError):
    """Raised when a source or binary verification invariant fails."""


def _download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url) as response, destination.open("wb") as target:
        shutil.copyfileobj(response, target)


def _run(command: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_source(archive_path: Path, destination: Path, source_directory: str) -> Path:
    """Safely extract only regular files and directories under the expected root."""
    with tarfile.open(archive_path, "r:xz") as archive:
        members = archive.getmembers()
        for member in members:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or path.parts[0] != source_directory
                or not (member.isfile() or member.isdir())
            ):
                raise BuildError(f"unsafe archive member: {member.name}")
        archive.extractall(destination, members=members)
    return destination / source_directory


def _checked(run: Run, command: tuple[str, ...], cwd: Path, action: str) -> subprocess.CompletedProcess[str]:
    result = run(command, cwd)
    if result.returncode != 0:
        raise BuildError(f"{action} failed: {result.stderr.strip()}")
    return result


def _validate_binary(binary: Path, run: Run) -> None:
    if not binary.is_absolute() or not binary.is_file() or not os.access(binary, os.X_OK):
        raise BuildError(f"FFmpeg output is not executable: {binary}")
    _checked(run, (str(binary), "-version"), binary.parent, "FFmpeg version probe")
    filters = _checked(run, (str(binary), "-hide_banner", "-filters"), binary.parent, "FFmpeg filter probe")
    if re.search(r"\bebur128\b", filters.stdout) is None:
        raise BuildError("FFmpeg is missing ebur128")
    help_output = _checked(
        run, (str(binary), "-hide_banner", "-h", "filter=ebur128"), binary.parent, "FFmpeg ebur128 probe"
    )
    if re.search(r"\bpeak\b.*\btrue\b|\btrue\b.*\bpeak\b", help_output.stdout.lower()) is None:
        raise BuildError("FFmpeg ebur128 lacks true-peak support")
    demuxers = _checked(run, (str(binary), "-hide_banner", "-demuxers"), binary.parent, "FFmpeg demuxer probe")
    decoders = _checked(run, (str(binary), "-hide_banner", "-decoders"), binary.parent, "FFmpeg decoder probe")
    if not _has_m4a_decode_capabilities(demuxers.stdout, decoders.stdout):
        raise BuildError("FFmpeg lacks required M4A MOV/AAC/ALAC decoding")


def _has_m4a_decode_capabilities(demuxers: str, decoders: str) -> bool:
    return bool(
        re.search(r"^\s*D\s+mov(?:,|$)", demuxers, re.MULTILINE)
        and re.search(r"^\s*[A-Z.]{6}\s+aac(?:\s|$)", decoders, re.MULTILINE)
        and re.search(r"^\s*[A-Z.]{6}\s+alac(?:\s|$)", decoders, re.MULTILINE)
    )


def build_universal_ffmpeg(
    work_directory: Path,
    output: Path,
    manifest: FfmpegSourceManifest = FFMPEG_SOURCE,
    download: Download = _download,
    run: Run = _run,
    jobs: int = 2,
) -> Path:
    """Download, verify, build, lipo, and validate the pinned universal2 binary."""
    work_directory = work_directory.resolve()
    output = output.resolve()
    sources = work_directory / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    archive_path = sources / Path(manifest.archive_url).name
    signature_path = sources / Path(manifest.signature_url).name
    download(manifest.archive_url, archive_path)
    download(manifest.signature_url, signature_path)
    if _sha256(archive_path) != manifest.archive_sha256:
        raise BuildError("FFmpeg source checksum did not match the pinned manifest")

    binaries: list[Path] = []
    for architecture in ARCHITECTURES:
        architecture_directory = work_directory / architecture
        shutil.rmtree(architecture_directory, ignore_errors=True)
        source = extract_source(archive_path, architecture_directory, manifest.source_directory)
        architecture_flags = f"-arch {architecture} -mmacosx-version-min={MACOS_DEPLOYMENT_TARGET}"
        configure = (
            "./configure",
            f"--arch={architecture}",
            "--target-os=darwin",
            "--cc=clang",
            f"--extra-cflags={architecture_flags}",
            f"--extra-ldflags={architecture_flags}",
            *CONFIGURE_FLAGS,
        )
        _checked(run, configure, source, f"{architecture} configure")
        _checked(run, ("make", f"-j{jobs}"), source, f"{architecture} make")
        binary = source / "ffmpeg"
        if not binary.is_file():
            raise BuildError(f"{architecture} build did not produce ffmpeg")
        destination = work_directory / f"ffmpeg-{architecture}"
        shutil.copy2(binary, destination)
        binaries.append(destination)

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = output.with_name(f".{output.name}.staging")
    staging.unlink(missing_ok=True)
    try:
        lipo_command = ("lipo", "-create", *(str(binary) for binary in binaries), "-output", str(staging))
        _checked(run, lipo_command, output.parent, "lipo")
        staging.chmod(staging.stat().st_mode | 0o111)
        _checked(run, ("lipo", str(staging), "-verify_arch", *ARCHITECTURES), output.parent, "lipo architecture check")
        _validate_binary(staging, run)
        os.replace(staging, output)
    finally:
        staging.unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    build_universal_ffmpeg(args.work_directory, args.output, jobs=args.jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
