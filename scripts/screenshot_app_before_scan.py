"""Launch XfinAudio offscreen with a folder selected but not scanned, and save a screenshot."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow


def main() -> int:
    db_path = Path("/tmp/xfinaudio_screenshot_before.sqlite3")
    settings_path = Path("/tmp/xfinaudio_screenshot_before_settings.json")
    db_path.unlink(missing_ok=True)
    settings_path.unlink(missing_ok=True)

    folder = Path("/Volumes/dd/_Lossless/por_decada/70s/Pop & Dance")

    app = QApplication(sys.argv)
    app.setApplicationName("XfinAudio")
    window = MainWindow.with_defaults(db_path=db_path, settings_path=settings_path)
    window.set_selected_folder(folder)
    window.show()

    def save_screenshot() -> None:
        output = Path("/tmp/xfinaudio_before_scan_screenshot.png")
        pixmap = window.grab()
        if pixmap.save(str(output)):
            print(f"Screenshot saved to {output}")
        else:
            print("Failed to save screenshot")
        window.close()

    QTimer.singleShot(1000, save_screenshot)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
