#!/usr/bin/env python3
"""Headless integration test for XfinAudio full DJ flow."""

import sys
import time
from pathlib import Path

# Add project source to path
sys.path.insert(0, "/Users/freddymolina/Documents/audio/src")

from PySide6.QtWidgets import QApplication

from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanProgress

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"
failures = []


def check(label, condition, detail=""):
    if condition:
        print(f"  {PASS} {label}")
    else:
        failures.append(label)
        print(f"  {FAIL} {label}" + (f": {detail}" if detail else ""))


def section(name):
    print(f"\n{'=' * 50}")
    print(f" {name}")
    print("=" * 50)


def ensure_app() -> QApplication:
    existing = QApplication.instance()
    if isinstance(existing, QApplication):
        return existing
    return QApplication([])


def _process_events_until(predicate, timeout_ms: int = 5000) -> bool:
    app = ensure_app()
    deadline = time.monotonic() + timeout_ms / 1000
    while not predicate():
        app.processEvents()
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class FakeScanService:
    def __init__(self) -> None:
        self.scanned_folder: Path | None = None

    def scan(self, folder: Path, **kwargs) -> list[TrackRecord]:
        self.scanned_folder = folder
        progress_callback = kwargs.get("on_progress")
        if progress_callback is not None:
            progress_callback(ScanProgress(processed_count=1, total_count=2, current_path=folder / "track.flac"))
        # Use camelot_key='8A' + harmonic_journey — known to produce 2-track recommendation
        return [
            TrackRecord(
                path=str(folder / "track.flac"),
                title="Track One",
                artist="Artist One",
                bpm=124.0,
                camelot_key="8A",
                energy_level=5,
                genre="House",
                tags=["Peak"],
                metadata_status="complete",
            ),
            TrackRecord(
                path=str(folder / "track2.flac"),
                title="Track Two",
                artist="Artist Two",
                bpm=125.0,
                camelot_key="8A",
                energy_level=6,
                genre="House",
                tags=["Peak"],
                metadata_status="complete",
            ),
        ]


class FakeRepository:
    def __init__(self) -> None:
        self.saved_records: list[TrackRecord] = []

    def save_scan_results(self, records: list[TrackRecord]) -> None:
        self.saved_records = records


# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _table_headers(table) -> list[str]:
    return [
        table.horizontalHeaderItem(col).text()
        for col in range(table.columnCount())
        if table.horizontalHeaderItem(col) is not None
    ]


def _visible_row_count(table) -> int:
    return sum(1 for row in range(table.rowCount()) if not table.isRowHidden(row))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def run_tests():
    app = ensure_app()

    # ------------------------------------------------------------------ #
    section("1. LIBRARY — initial load and scan")
    # ------------------------------------------------------------------ #

    scan_service = FakeScanService()
    window = MainWindow(scan_service=scan_service, repository=FakeRepository())

    # Check tab count and names
    tab_count = window.workflow_tabs.count()
    check("Tab count is 5", tab_count == 5, f"got {tab_count}")

    expected_tabs = ["Library", "Build Playlist", "Review Mix", "Export to Serato", "Metadata Worklist"]
    actual_tabs = [window.workflow_tabs.tabText(i) for i in range(tab_count)]
    check("Tab names correct", actual_tabs == expected_tabs, f"got {actual_tabs}")

    # LibraryScreen has a proceed_button "Build Playlist →"
    check(
        "LibraryScreen.proceed_button exists with correct text",
        hasattr(window._library_screen, "proceed_button"),
        "no proceed_button attribute",
    )
    check(
        "LibraryScreen proceed_button text",
        window._library_screen.proceed_button.text() == "Build Playlist →",
        f"got '{window._library_screen.proceed_button.text()}'",
    )

    # Initial state: scan disabled until folder chosen
    check("scan_button disabled initially", not window.scan_button.isEnabled())
    check("recommend_button disabled initially", not window.recommend_button.isEnabled())

    # ------------------------------------------------------------------ #
    section("8. NAVIGATION CONTROLLER — tab enable/disable state")
    # ------------------------------------------------------------------ #

    # Moment 1: before scan — only Library and Metadata should be enabled
    app.processEvents()
    check("8.1 Library tab enabled before scan", window.workflow_tabs.isTabEnabled(0))
    check("8.1 Build Playlist tab disabled before scan", not window.workflow_tabs.isTabEnabled(1))
    check("8.1 Review Mix tab disabled before scan", not window.workflow_tabs.isTabEnabled(2))
    check("8.1 Export to Serato tab disabled before scan", not window.workflow_tabs.isTabEnabled(3))
    check("8.1 Metadata Worklist tab enabled before scan", window.workflow_tabs.isTabEnabled(4))

    # Simulate scan
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        window.set_selected_folder(tmp_path)
        check("scan_button enabled after folder selected", window.scan_button.isEnabled())
        check(
            "LibraryScreen.search_input has placeholder",
            window._library_screen.search_input.placeholderText() == "Search songs",
            f"got '{window._library_screen.search_input.placeholderText()}'",
        )

        window.scan_selected_folder()
        reached = _process_events_until(lambda: window.current_scan_cancellation_token is None)
        check("Scan completed within timeout", reached)
        check(
            "tracks_table populated (2 rows)",
            window.tracks_table.rowCount() == 2,
            f"got {window.tracks_table.rowCount()}",
        )
        check("scanned_records has 2 entries", len(window.scanned_records) == 2)

        # Moment 2: after scan — Library and Build (and Metadata) should be enabled
        app.processEvents()
        check("8.2 Library tab enabled after scan", window.workflow_tabs.isTabEnabled(0))
        check("8.2 Build Playlist tab enabled after scan", window.workflow_tabs.isTabEnabled(1))
        check("8.2 Review Mix tab disabled after scan", not window.workflow_tabs.isTabEnabled(2))
        check("8.2 Export to Serato tab disabled after scan", not window.workflow_tabs.isTabEnabled(3))
        check("8.2 Metadata Worklist tab enabled after scan", window.workflow_tabs.isTabEnabled(4))

        # Filter test
        window.song_search_input.setText("One")
        visible = _visible_row_count(window.tracks_table)
        check("Filter reduces visible rows to 1", visible == 1, f"got {visible}")
        window.song_search_input.clear()

        # Select first track (start_path controls harmonic_journey to build 2-track result)
        window.tracks_table.selectRow(0)
        check("recommend_button enabled after selection", window.recommend_button.isEnabled())

        # ------------------------------------------------------------------ #
        section("2. BUILD PLAYLIST — navigate and recommend")
        # ------------------------------------------------------------------ #

        # LibraryScreen proceed_button should navigate to tab 1
        window._library_screen.proceed_button.clicked.emit()
        app.processEvents()
        check("Tab navigated to Build Playlist (index 1)", window.workflow_tabs.currentIndex() == 1)

        # BuildScreen back button navigates to Library
        window._build_screen.back_button.clicked.emit()
        app.processEvents()
        check("Back button returns to Library (index 0)", window.workflow_tabs.currentIndex() == 0)

        # Navigate back to Build
        window.workflow_tabs.setCurrentIndex(1)

        # Check BuildScreen recommend_button state (should be enabled because a track is selected)
        build_recommend_enabled = window._build_screen.recommend_button.isEnabled()
        check("BuildScreen.recommend_button enabled with track selected", build_recommend_enabled)

        # Trigger recommendation via BuildScreen — use harmonic_journey to get 2-track result
        window.strategy_combo.setCurrentText("harmonic_journey")
        window.recommend_playlist()
        reached = _process_events_until(lambda: window.recommend_button.isEnabled())
        check("Recommendation completed within timeout", reached)

        # Moment 3: after recommendation — Library, Build, Review, Export, and Metadata enabled
        # (_show_dj_readiness fires automatically after recommendation, enabling Export)
        app.processEvents()
        check("8.3 Library tab enabled after recommendation", window.workflow_tabs.isTabEnabled(0))
        check("8.3 Build Playlist tab enabled after recommendation", window.workflow_tabs.isTabEnabled(1))
        check("8.3 Review Mix tab enabled after recommendation", window.workflow_tabs.isTabEnabled(2))
        check("8.3 Export to Serato tab enabled after recommendation", window.workflow_tabs.isTabEnabled(3))
        check("8.3 Metadata Worklist tab enabled after recommendation", window.workflow_tabs.isTabEnabled(4))

        # Check recommendation table
        rec_row_count = window.recommendation_table.rowCount()
        check("recommendation_table populated (>0 rows)", rec_row_count > 0, f"got {rec_row_count}")
        check("recommendation_table hidden=False", not window.recommendation_table.isHidden())

        # Verify no extra top-level visible windows (excluding our window)
        top_level = [w for w in app.topLevelWidgets() if w.isVisible() and w is not window]
        check(
            "No unexpected visible top-level windows",
            len(top_level) == 0,
            f"found: {[type(w).__name__ for w in top_level]}",
        )

        # ------------------------------------------------------------------ #
        section("3. REVIEW MIX — readiness badge and export button state")
        # ------------------------------------------------------------------ #

        window.workflow_tabs.setCurrentIndex(2)
        app.processEvents()
        check("Tab navigated to Review Mix (index 2)", window.workflow_tabs.currentIndex() == 2)

        # ReviewScreen has readiness_badge
        check(
            "ReviewScreen.readiness_badge exists",
            hasattr(window._review_screen, "readiness_badge"),
        )
        badge_text = window._review_screen.readiness_badge.text()
        check(
            "readiness_badge text is non-empty",
            bool(badge_text),
            f"got '{badge_text}'",
        )
        # Should not say "No playlist" since we have a recommendation
        check(
            "readiness_badge does not say 'No playlist generated'",
            badge_text != "No playlist generated",
            f"got '{badge_text}'",
        )

        # ReviewScreen.export_button should be enabled (READY or NEEDS_REVIEW)
        export_btn_enabled = window._review_screen.export_button.isEnabled()
        check("ReviewScreen.export_button enabled (recommendation ready)", export_btn_enabled)

        # Review screen back button goes to Build Playlist
        window._review_screen.back_button.clicked.emit()
        app.processEvents()
        check("ReviewScreen back goes to Build (index 1)", window.workflow_tabs.currentIndex() == 1)

        # ------------------------------------------------------------------ #
        section("4. EXPORT TO SERATO — tab elements visible")
        # ------------------------------------------------------------------ #

        window.workflow_tabs.setCurrentIndex(3)
        app.processEvents()
        check("Tab navigated to Export to Serato (index 3)", window.workflow_tabs.currentIndex() == 3)

        # ExportScreen widgets
        check("ExportScreen.export_button exists", hasattr(window._export_screen, "export_button"))
        check("ExportScreen.back_button exists", hasattr(window._export_screen, "back_button"))
        check("ExportScreen.preview_button exists", hasattr(window._export_screen, "preview_button"))

        # export_button state: should be enabled when recommendation exists
        export_screen_enabled = window._export_screen.export_button.isEnabled()
        check("ExportScreen.export_button enabled", export_screen_enabled)

        # back button navigates to Review Mix
        window._export_screen.back_button.clicked.emit()
        app.processEvents()
        check("ExportScreen back goes to Review Mix (index 2)", window.workflow_tabs.currentIndex() == 2)

        # ------------------------------------------------------------------ #
        section("5. BACK NAVIGATION — each tab has a functional back button")
        # ------------------------------------------------------------------ #

        # Metadata tab back → Library
        window.workflow_tabs.setCurrentIndex(4)
        app.processEvents()
        window._metadata_screen.back_button.clicked.emit()
        app.processEvents()
        check("MetadataScreen back goes to Library (index 0)", window.workflow_tabs.currentIndex() == 0)

        # ------------------------------------------------------------------ #
        section("6. SIGNAL CONNECTIVITY — emit signals without crash")
        # ------------------------------------------------------------------ #

        # Emit selection_changed from LibraryScreen
        try:
            window._library_screen.selection_changed.emit([str(tmp_path / "track.flac")])
            app.processEvents()
            check("LibraryScreen.selection_changed emits without crash", True)
        except Exception as exc:
            check("LibraryScreen.selection_changed emits without crash", False, str(exc))

        # Emit recommend_requested from BuildScreen
        try:
            window._build_screen.recommend_requested.emit("warmup", [])
            app.processEvents()
            check("BuildScreen.recommend_requested emits without crash", True)
        except Exception as exc:
            check("BuildScreen.recommend_requested emits without crash", False, str(exc))

        # Emit back_requested from ReviewScreen
        window.workflow_tabs.setCurrentIndex(2)
        try:
            window._review_screen.back_requested.emit()
            app.processEvents()
            check("ReviewScreen.back_requested emits without crash", True)
        except Exception as exc:
            check("ReviewScreen.back_requested emits without crash", False, str(exc))

        # Emit back_requested from ExportScreen
        window.workflow_tabs.setCurrentIndex(3)
        try:
            window._export_screen.back_requested.emit()
            app.processEvents()
            check("ExportScreen.back_requested emits without crash", True)
        except Exception as exc:
            check("ExportScreen.back_requested emits without crash", False, str(exc))

        # ------------------------------------------------------------------ #
        section("7. REVIEW MIX — proceed_to_export navigates correctly")
        # ------------------------------------------------------------------ #

        # Navigate to Review Mix and hit proceed_to_export
        window.workflow_tabs.setCurrentIndex(2)
        app.processEvents()
        # proceed_to_export_requested goes to Export (index 3) only if can_export
        from xfinaudio.desktop.review_view_model import ReviewViewModel

        vm = ReviewViewModel()
        # Sync state so it has current recommendation
        window._sync_state()
        can_export = vm.can_export(window._state)
        check(
            "ReviewViewModel.can_export is True after recommendation",
            can_export,
            f"state has recommendation: {window._state.last_recommendation is not None}, "
            f"readiness: {window._state.last_dj_readiness_report}",
        )

        if can_export:
            window._review_screen.proceed_to_export_requested.emit()
            app.processEvents()
            check(
                "proceed_to_export navigates to Export (index 3)",
                window.workflow_tabs.currentIndex() == 3,
                f"got index {window.workflow_tabs.currentIndex()}",
            )

    # ------------------------------------------------------------------ #
    section("FINAL SUMMARY")
    # ------------------------------------------------------------------ #
    if failures:
        print(f"\n{FAIL} {len(failures)} failure(s):")
        for f in failures:
            print(f"   - {f}")
        sys.exit(1)
    else:
        print(f"\n{PASS} All checks passed")
        sys.exit(0)


if __name__ == "__main__":
    run_tests()
