"""Dependency-only frozen QA probe; no provider, tags, Serato or app release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
from pathlib import Path

from mac_runtime_bootstrap import configure_runtime, parse_data_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--music", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    data = parse_data_dir(["--data-dir", str(args.data_dir)])
    if not getattr(sys, "frozen", False):
        raise ValueError("This probe requires the frozen dependency executable")
    configure_runtime(Path(sys._MEIPASS), data)
    attempts = []

    def blocked(*_args, **_kwargs):
        attempts.append(True)
        raise AssertionError("Dependency probe forbids network")

    socket.socket.connect = blocked
    socket.socket.connect_ex = blocked
    socket.create_connection = blocked
    from mac_numba_cache import AppDataCacheLocator
    from numba import config

    from xfinaudio.audio.analyzer import (
        LibrosaDanceabilityAnalyzer,
        LibrosaEdgeSpectralAnalyzer,
        LibrosaSpectralAnalyzer,
    )

    before, measured = {}, []
    for name in ("tone.wav", "tone.flac", "tone.mp3", "tone.aac.m4a", "tone.alac.m4a", "tone.aiff"):
        path = args.music / name
        before[name] = (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns)
        result = {"name": name}
        for stage, analyzer in [
            ("spectral", LibrosaSpectralAnalyzer),
            ("danceability", LibrosaDanceabilityAnalyzer),
            ("edge", LibrosaEdgeSpectralAnalyzer),
        ]:
            profile = analyzer().analyze(path)
            if profile is None:
                raise AssertionError(f"Original {stage} profile unavailable for {name}")
            result[stage] = profile.model_dump()
        if before[name] != (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_mtime_ns):
            raise AssertionError("Read-only dependency probe changed fixture")
        measured.append(result)

    def stamp_function():
        return 1

    locator = AppDataCacheLocator.from_function(stamp_function, "frozen_probe.py")
    if locator is None:
        raise AssertionError("Frozen locator unavailable")
    cache = data / "cache/numba"
    files = [p.relative_to(cache).as_posix() for p in cache.rglob("*") if p.is_file()]
    if not files or str(cache) != config.CACHE_DIR or attempts:
        raise AssertionError("Frozen cache confinement failed")
    report = {
        "frozen": True,
        "executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "locator_stamp_sha256": locator.get_source_stamp().hex(),
        "cache_locator": config.CACHE_LOCATOR_CLASSES,
        "cache_files": sorted(files),
        "source_hashes_mtimes": before,
        "profiles": measured,
        "qt_imported": any(name.startswith(("PySide", "PyQt", "shiboken")) for name in sys.modules),
        "network_attempts": len(attempts),
        "decoder_path": os.environ["PATH"],
    }
    if report["qt_imported"] or report["executable_sha256"] != report["locator_stamp_sha256"]:
        raise AssertionError("Frozen inventory/stamp failed")
    args.report.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
