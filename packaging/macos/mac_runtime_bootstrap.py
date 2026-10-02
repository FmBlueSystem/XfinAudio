"""Mac-only override after the unchanged canonical frozen-runtime bootstrap."""

from __future__ import annotations

import os
from pathlib import Path

from runtime_bootstrap import configure_runtime as _shared_configure
from runtime_bootstrap import parse_data_dir as parse_data_dir


def configure_runtime(bundle: Path | None, data: Path | None = None) -> None:
    """Select the direct locator before importing any scientific/JIT modules."""
    _shared_configure(bundle, data)
    if bundle is not None:
        os.environ["NUMBA_CACHE_LOCATOR_CLASSES"] = "mac_numba_cache.AppDataCacheLocator"
