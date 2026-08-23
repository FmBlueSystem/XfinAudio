"""Safe runtime composition for the optional FFmpeg loudness service."""

from __future__ import annotations

import hashlib
import logging
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from xfinaudio.audio.loudness import FfmpegCapabilityError, FfmpegLoudnessAdapter
from xfinaudio.audio.loudness_completion import LoudnessCompletionService
from xfinaudio.audio.loudness_tags import write_loudness_tags

VersionProbe = Callable[[Path], str | None]
AdapterFactory = Callable[[Path, str], FfmpegLoudnessAdapter]

_log = logging.getLogger(__name__)


def resolve_ffmpeg(
    *, frozen: bool | None = None, bundle_dir: Path | None = None, which: Callable[[str], str | None] = shutil.which
) -> Path | None:
    """Resolve the bundle binary in frozen mode, with PATH permitted only for development."""
    frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
    if frozen:
        root = bundle_dir or getattr(sys, "_MEIPASS", None)
        return (Path(root) / "ffmpeg").resolve() if root is not None else None
    return Path(path).resolve() if (path := which("ffmpeg")) is not None else None


def probe_engine_fingerprint(executable: Path) -> str | None:
    """Fingerprint the complete successful version output without a shell."""
    try:
        result = subprocess.run(
            (str(executable), "-version"),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return f"ffmpeg-sha256:{hashlib.sha256((result.stdout or '').encode()).hexdigest()}"


def _adapter(executable: Path, fingerprint: str) -> FfmpegLoudnessAdapter:
    return FfmpegLoudnessAdapter(executable, engine_fingerprint=fingerprint)


def create_loudness_completion_service(
    *,
    frozen: bool | None = None,
    bundle_dir: Path | None = None,
    which: Callable[[str], str | None] = shutil.which,
    version_probe: VersionProbe = probe_engine_fingerprint,
    adapter_factory: AdapterFactory = _adapter,
) -> LoudnessCompletionService | None:
    """Return a preflighted service, or leave startup operational without loudness.

    Startup stays operational without loudness, but never quietly: each abort names its
    own reason so a stage that vanishes can be traced from the log alone.
    """
    if (executable := resolve_ffmpeg(frozen=frozen, bundle_dir=bundle_dir, which=which)) is None:
        _log.warning("Loudness analysis disabled: no FFmpeg executable could be resolved")
        return None
    if (fingerprint := version_probe(executable)) is None:
        _log.warning("Loudness analysis disabled: FFmpeg at %s did not report a usable version", executable)
        return None
    try:
        adapter = adapter_factory(executable, fingerprint)
        adapter.preflight()
    except (FfmpegCapabilityError, OSError) as error:
        _log.warning("Loudness analysis disabled: FFmpeg at %s failed capability preflight: %s", executable, error)
        return None
    return LoudnessCompletionService(adapter, engine_fingerprint=fingerprint, tag_writer=write_loudness_tags)
