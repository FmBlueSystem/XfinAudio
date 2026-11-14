"""Size-bounded rotating log file for the headless core.

The headless core speaks JSONL on stdout, so that stream is reserved for protocol
frames and no handler may ever write records there. Diagnostics keep going to stderr
and additionally to a rotating file inside the isolated ``--data-dir``, so support can
read them after the core has exited.

Logging must never be able to stop the core: when the log file cannot be created (a
read-only data directory, a directory sitting where the file should be) the failure is
reported on stderr and the core starts with stderr logging only.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILE_NAME = "core.log"
MAX_LOG_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

LOGGER = logging.getLogger(__name__)


def log_file_path(data_dir: Path | str) -> Path:
    """Return the rotating log file location inside ``data_dir``."""
    return Path(data_dir) / LOG_FILE_NAME


def configure_logging(
    data_dir: Path | str,
    *,
    level: int = logging.WARNING,
    max_bytes: int = MAX_LOG_BYTES,
    backup_count: int = LOG_BACKUP_COUNT,
) -> bool:
    """Send records to stderr and, when possible, to a rotating file in ``data_dir``.

    Returns whether the log file is in place. Never raises: a logging problem keeps
    the stderr stream and lets the core start anyway.
    """
    root = logging.getLogger()
    _attach_stderr_handler(root, level)
    path = log_file_path(data_dir)
    if _file_handler(root, path) is not None:
        return True
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8")
    except OSError as exc:
        LOGGER.warning("Rotating log file unavailable at %s (%s); continuing with stderr only", path, exc)
        return False
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(handler)
    return True


def _attach_stderr_handler(root: logging.Logger, level: int) -> None:
    """Attach the stderr destination with the format the core has always produced."""
    for handler in root.handlers:
        if _is_stderr_handler(handler):
            handler.setLevel(level)
            return
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
    root.addHandler(handler)


def _is_stderr_handler(handler: logging.Handler) -> bool:
    return (
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        and handler.stream is sys.stderr
    )


def _file_handler(root: logging.Logger, path: Path) -> RotatingFileHandler | None:
    """Return the already installed rotating handler for ``path``, if any."""
    for handler in root.handlers:
        if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == path:
            return handler
    return None
