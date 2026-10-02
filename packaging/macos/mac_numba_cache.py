"""Frozen-aware Numba locator with a direct validated application cache root."""

from __future__ import annotations

from pathlib import Path

from numba import config
from numba.core.caching import UserWideCacheLocator


class AppDataCacheLocator(UserWideCacheLocator):
    """Retain Numba's executable hash/disambiguation without AppDirs on Mac."""

    def __init__(self, py_func, py_file):
        root = Path(config.CACHE_DIR)
        if not root.is_absolute() or root.resolve() != root or root.exists() and not root.is_dir():
            raise ValueError("Numba cache requires the validated application directory")
        path = root / self.get_suitable_cache_subpath(py_file)
        if path.resolve() != path:
            raise ValueError("Numba cache child must not traverse symlinks")
        super().__init__(py_func, py_file)
        self._cache_path = str(path)
