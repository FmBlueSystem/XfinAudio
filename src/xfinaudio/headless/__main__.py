"""Run the local-only bridge: python -m xfinaudio.headless --data-dir PATH."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from xfinaudio.headless import logging_setup
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.server import JsonlServer


def main() -> None:
    parser = argparse.ArgumentParser(description="XfinAudio Qt-free local JSONL backend")
    parser.add_argument("--data-dir", required=True, type=Path)
    args = parser.parse_args()
    if not args.data_dir.is_absolute():
        parser.error("--data-dir must be an absolute, isolated application directory")
    # stdout carries JSONL protocol frames only: warnings go to stderr at once.
    # The rotating file is added only after the backend has accepted the data
    # directory, so a refused directory is never written to.
    logging_setup.configure_stderr_logging()
    backend = HeadlessBackend(args.data_dir)
    logging_setup.configure_logging(args.data_dir)
    server = JsonlServer(backend, sys.stdout)
    try:
        server.run(sys.stdin.buffer)
    except (BrokenPipeError, KeyboardInterrupt):
        server.close()


if __name__ == "__main__":
    main()
