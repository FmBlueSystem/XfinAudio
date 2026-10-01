"""Native Cocoa diagnostic baseline, not an external accessibility regression.

This uses synthetic plans and pointer events. It does not issue AppKit AX
requests, reproduce the reported crash, or establish its cause.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys

import PySide6
import pytest
from PySide6.QtCore import Qt, QThread, qVersion
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
from test_build_screen import _plan_state, _track

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.build_view_model import BuildViewModel
from xfinaudio.desktop.screens.build_screen import BuildScreen


@pytest.mark.skipif(
    sys.platform != "darwin"
    or os.environ.get("GITHUB_ACTIONS") != "true"
    or os.environ.get("GITHUB_REF") != "refs/heads/fix/watcher-event-lifecycle"
    or os.environ.get("QT_QPA_PLATFORM") != "offscreen",
    reason="Subprocess diagnostic is scoped to the authorized macOS CI branch",
)
def test_balanced_native_diagnostic_subprocess(capsys: pytest.CaptureFixture[str]) -> None:
    """Run the Cocoa baseline separately from the ordinary offscreen suite."""
    environment = os.environ.copy()
    environment.update(QT_QPA_PLATFORM="cocoa", QT_ACCESSIBILITY="1")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-s", f"{__file__}::test_balanced_pointer_selection_and_redraw_native"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=90,
    )
    with capsys.disabled():
        print(result.stdout, flush=True)
        print(result.stderr, file=sys.stderr, flush=True)
    assert result.returncode == 0, f"Cocoa diagnostic exited {result.returncode}:\n{result.stdout}\n{result.stderr}"
    assert '"platform": "cocoa"' in result.stdout
    assert "Cocoa pointer/redraw baseline passed" in result.stdout


@pytest.mark.skipif(
    sys.platform != "darwin" or os.environ.get("QT_QPA_PLATFORM") != "cocoa",
    reason="Native diagnostic requires an explicitly selected macOS Cocoa process",
)
def test_balanced_pointer_selection_and_redraw_native(qapp: QApplication) -> None:
    """Exercise selection and destructive redraw without files or AI requests."""
    assert qapp.platformName() == "cocoa"
    assert os.environ.get("QT_ACCESSIBILITY") == "1"
    assert QThread.currentThread() == qapp.thread()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    print(
        "Native diagnostic metadata: "
        + json.dumps(
            {
                "revision": revision,
                "macos": platform.mac_ver()[0],
                "architecture": platform.machine(),
                "python": platform.python_version(),
                "pyside": PySide6.__version__,
                "qt": qVersion(),
                "platform": qapp.platformName(),
                "external_ax_requests": False,
                "own_process_ax_getters": False,
                "production_translator_loaded": False,
                "reported_spanish_label_exercised": False,
            },
            sort_keys=True,
        ),
        flush=True,
    )
    screen = BuildScreen()
    screen.resize(1100, 900)
    vm = BuildViewModel()
    tracks = [_track("/synthetic/a.flac"), _track("/synthetic/b.flac")]
    state = _plan_state(tracks)
    applied: list[int] = []
    screen.copilot_variant_applied.connect(applied.append)
    try:
        screen.show()
        screen.render(vm, state)
        screen.controls_scroll.ensureWidgetVisible(screen.copilot_table)
        QTest.qWait(100)
        assert screen.isVisible()
        assert screen.copilot_table.isVisible()
        assert screen.variant_details_label.isVisible()
        assert screen.apply_variant_button.text() == "Use balanced · 2 tracks"
        for cycle in range(12):
            for row in (0, 2, 1):
                item = screen.copilot_table.item(row, 0)
                assert item is not None
                name = ("safe", "balanced", "adventurous")[row]
                assert item.text() == name
                screen.copilot_table.scrollToItem(item)
                rect = screen.copilot_table.visualItemRect(item)
                assert not rect.isEmpty()
                assert screen.copilot_table.viewport().visibleRegion().contains(rect.center())
                QTest.mouseClick(screen.copilot_table.viewport(), Qt.MouseButton.LeftButton, pos=rect.center())
                QTest.qWait(10)
                assert screen.copilot_table.currentRow() == row
                assert screen.copilot_table.selectedIndexes()
                assert screen.variant_details_label.isVisible()
                assert "2 of 25 requested" in screen.variant_details_label.text()
                assert screen.apply_variant_button.text() == f"Use {name} · 2 tracks"
                screen.render(vm, state)
                qapp.processEvents()
                assert screen.copilot_table.currentRow() == row
            state = _plan_state(tracks, blocked=frozenset({1}) if cycle % 2 == 0 else frozenset())
            screen.render(vm, state)
            qapp.processEvents()
            assert screen.copilot_table.currentRow() == 1
            readiness = screen.copilot_table.item(1, 3)
            assert readiness is not None
            assert readiness.text() == ("Blocked" if cycle % 2 == 0 else "Ready")
        screen.controls_scroll.ensureWidgetVisible(screen.apply_variant_button)
        QTest.qWait(20)
        assert screen.apply_variant_button.isVisible()
        assert screen.apply_variant_button.isEnabled()
        QTest.mouseClick(screen.apply_variant_button, Qt.MouseButton.LeftButton)
        assert applied == [1]
        screen.render(vm, AppState())
        qapp.processEvents()
        assert screen.copilot_table.rowCount() == 0
        screen.render(vm, state)
        qapp.processEvents()
        assert screen.copilot_table.rowCount() == 3
        assert screen.copilot_table.currentRow() == 1
        print("Cocoa pointer/redraw baseline passed; external AX path NOT exercised", flush=True)
    finally:
        screen.close()
        screen.deleteLater()
        qapp.processEvents()
