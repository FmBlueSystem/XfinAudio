"""Console JSONL entry for PyInstaller; never import the retired desktop runtime."""

from __future__ import annotations

import sys
from pathlib import Path

from runtime_bootstrap import configure_runtime, parse_data_dir

if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        configure_runtime(Path(sys._MEIPASS), parse_data_dir(sys.argv[1:]))
    from xfinaudio.headless.__main__ import main

    main()
