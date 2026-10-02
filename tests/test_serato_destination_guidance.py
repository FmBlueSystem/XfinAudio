"""Serato UI identifies the actual direct crate and optional report destinations."""

from PySide6.QtCore import Qt

from tests.test_build_screen import _plan_state, _track
from xfinaudio.desktop.main_window import MainWindow
from xfinaudio.desktop.screens.export_screen import ExportScreen


def test_serato_preview_distinguishes_crate_reports_and_backup_without_writing(qapp, tmp_path):
    serato = tmp_path / "music" / "_Serato_"
    subcrates = serato / "Subcrates"
    subcrates.mkdir(parents=True)
    target = subcrates / "Preview.crate"
    target.write_bytes(b"existing synthetic crate")
    window = MainWindow.with_defaults(tmp_path / "db.sqlite3", tmp_path / "settings.json")
    plan = _plan_state([_track(str(serato.parent / "a.flac")), _track(str(serato.parent / "b.flac"))])
    assert plan.last_prep_copilot_plan is not None
    window._replace_app_state(
        window._state.model_copy(
            update={
                "last_recommendation": plan.last_prep_copilot_plan.variants[0].recommendation,
            }
        )
    )
    try:
        window.preview_serato_export(serato_folder=serato, crate_name="Preview")
        text = window._export_screen.export_guidance_label.text()
        assert str(target) in text
        assert f"Readiness report folder: {subcrates}" in text
        assert f"Backup beside crate: {subcrates}" in text
        assert "report folder" in window._export_screen.safe_export_folder_label.text().lower()
        assert "optional" in window._export_screen.safe_export_folder_label.text().lower()
        assert target.read_bytes() == b"existing synthetic crate"
        assert list(subcrates.iterdir()) == [target]
    finally:
        window.close()


def test_destination_guidance_is_selectable_and_identifies_report_folder(qapp):
    screen = ExportScreen()
    assert "report" in screen.safe_folder_button.text().lower()
    assert "directly" in screen.export_guidance_label.text().lower()
    assert screen.export_guidance_label.textInteractionFlags() & Qt.TextInteractionFlag.TextSelectableByKeyboard
