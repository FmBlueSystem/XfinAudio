"""Launch XfinAudio offscreen with pre-scanned color fixtures and save a screenshot."""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from xfinaudio.application.playlist_workflow import PlaylistWorkflowService
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.track_repository import TrackRepository


def main() -> int:
    db_path = Path("/tmp/xfinaudio_screenshot.sqlite3")
    settings_path = Path("/tmp/xfinaudio_screenshot_settings.json")
    db_path.unlink(missing_ok=True)
    settings_path.unlink(missing_ok=True)

    folder = Path(__file__).resolve().parents[1] / "assets" / "synthetic_color_tests"

    print(f"Scanning {folder} ...")
    repository = TrackRepository(db_path)
    workflow = PlaylistWorkflowService(scan_service=None, repository=repository)
    # Use internal scan service directly to avoid protocol issues
    from xfinaudio.library.scan_service import MetadataScanService

    workflow.scan_service = MetadataScanService()
    result = workflow.scan_folder(folder)
    print(f"Scanned {len(result.records)} tracks")

    app = QApplication(sys.argv)
    app.setApplicationName("XfinAudio")
    window = MainWindow.with_defaults(db_path=db_path, settings_path=settings_path)
    window.show()

    def save_screenshot() -> None:
        output = Path("/tmp/xfinaudio_color_screenshot.png")
        pixmap = window.grab()
        if pixmap.save(str(output)):
            print(f"Screenshot saved to {output}")
        else:
            print("Failed to save screenshot")
        window.close()

    QTimer.singleShot(2000, save_screenshot)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
