"""Tell whether Serato DJ is running, so no crate is written while it is open.

Serato keeps its crates in memory and rewrites its `_Serato_` folder when it
quits, which deletes a crate another program wrote meanwhile. This check is a
guard against that third-party behaviour, not a security boundary: when it
cannot run, it reports "not running" and logs why.
"""

from __future__ import annotations

import logging
import subprocess
import sys
from collections.abc import Callable

LOGGER = logging.getLogger(__name__)

SERATO_PROCESS_NAMES = ("Serato DJ Pro", "Serato DJ Lite")

Runner = Callable[[list[str]], "subprocess.CompletedProcess[str]"]


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=5, check=False)  # noqa: S603


def serato_is_running(*, platform: str | None = None, runner: Runner = _run) -> bool:
    platform = sys.platform if platform is None else platform
    try:
        for name in SERATO_PROCESS_NAMES:
            if platform == "win32":
                image = f"{name}.exe"
                result = runner(["tasklist", "/NH", "/FO", "CSV", "/FI", f"IMAGENAME eq {image}"])
                if f'"{image.casefold()}"' in result.stdout.casefold():
                    return True
            elif runner(["pgrep", "-x", name]).returncode == 0:
                return True
    except (OSError, subprocess.SubprocessError) as error:
        LOGGER.warning("Export continues: could not check whether Serato DJ is running (%s)", error)
    return False
