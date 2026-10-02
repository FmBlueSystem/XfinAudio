"""Bind frozen subprocess tools and JIT code cache to trusted application paths."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path


def _validate_data_dir(data: Path) -> None:
    if not data.is_absolute() or data.resolve() != data or (data.exists() and not data.is_dir()):
        raise ValueError("--data-dir must be an absolute, canonical application directory")


def parse_data_dir(args: Sequence[str]) -> Path:
    """Validate the headless destination before creating any cache directories."""
    parser = argparse.ArgumentParser(description="XfinAudio Qt-free local JSONL backend")
    parser.add_argument("--data-dir", required=True, type=Path)
    data = parser.parse_args(args).data_dir
    try:
        _validate_data_dir(data)
    except (OSError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    return data


def configure_runtime(bundle: Path | None, data: Path | None = None) -> None:
    """Keep development unchanged; never inherit external frozen JIT/cache paths."""
    if bundle is None:
        return
    if data is None:
        raise ValueError("Frozen runtime requires a validated application data directory")
    _validate_data_dir(data)
    cache = data / "cache" / "numba"
    if cache.resolve() != cache:
        raise ValueError("Application code cache must not traverse symlinks")
    cache.mkdir(parents=True, exist_ok=True)
    os.environ["PATH"] = str(bundle)
    os.environ["NUMBA_CACHE_DIR"] = str(cache)
    os.environ["XDG_CACHE_HOME"] = str(cache.parent)
    # Frozen co_filenames can be relative/non-files. Use Numba's built-in
    # frozen-aware locator, with its standard numba directory now app-owned.
    os.environ["NUMBA_CACHE_LOCATOR_CLASSES"] = "UserWideCacheLocator"
    # Retain librosa's disabled joblib cache default; only NumPy/Numba code is cached.
    os.environ.pop("LIBROSA_CACHE_DIR", None)
