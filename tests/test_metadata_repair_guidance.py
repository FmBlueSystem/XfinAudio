"""Repair guidance must remain grounded and read-only."""

from dataclasses import asdict

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.screens.metadata_screen import MetadataScreen
from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.repair_guidance import explain_track_gaps, prioritize_repairs


def records():
    return [
        TrackRecord(path="/z.mp3", title="One gap", bpm=120, camelot_key="8A"),
        TrackRecord(path="/a.mp3", title="Locked", bpm=124),
        TrackRecord(path="/b.mp3", title="Complete", bpm=122, camelot_key="8A", energy_level=5),
    ]


def test_repair_priority_locks_then_fewer_known_gaps():
    source = records()
    before = [record.model_dump() for record in source]
    plan = prioritize_repairs(source, locked_paths=frozenset({"/a.mp3"}))
    assert [item.path for item in plan] == ["/a.mp3", "/z.mp3"]
    assert plan[0].locked is True
    assert plan[0].missing_fields == ("camelot_key", "energy_level")
    assert [record.model_dump() for record in source] == before
    assert [item.path for item in prioritize_repairs(source)] == ["/z.mp3", "/a.mp3"]


def test_explanation_uses_absent_values_never_stale_status_or_invented_numbers():
    record = TrackRecord(path="/unknown.mp3", metadata_status="complete")
    text = explain_track_gaps(record)
    assert "BPM" in text and "Key" in text and "Energy" in text
    assert "tempo" in text and "harmonic" in text and "energy" in text
    assert "not inferred" in text and "verified" in text
    assert "120" not in text and "8A" not in text
    assert "No required" in explain_track_gaps(records()[2])


def test_metadata_screen_explains_selection_and_priorities_without_writes(qapp):
    screen = MetadataScreen()
    state = AppState(scanned_records=records(), locked_paths=frozenset({"/a.mp3"}))
    before = asdict(state)
    screen.render(state)
    screen.repair_help_button.click()
    text = screen.repair_help.toPlainText()
    assert "Local" in text and "Locked" in text
    assert text.index("Locked") < text.index("One gap")
    screen.worklist_table.selectRow(0)
    assert "One gap" in screen.repair_help.toPlainText()
    assert "Energy" in screen.repair_help.toPlainText()
    assert asdict(state) == before
    screen.render(AppState())
    assert not screen.repair_help_button.isEnabled()
    assert screen.repair_help.toPlainText() == ""


def test_repair_help_follows_filtered_selection_and_bounds_plan(qapp):
    from xfinaudio.metadata.repair_guidance import repair_plan_text

    source = [TrackRecord(path=f"/{index:02}.mp3", title=f"Missing {index}") for index in range(12)]
    assert "2 more tracks" in repair_plan_text(source)
    assert "No required metadata gaps" in repair_plan_text([records()[2]])
    screen = MetadataScreen()
    state = AppState(scanned_records=source)
    screen.render(state)
    screen.worklist_table.selectRow(0)
    assert screen.repair_help.toPlainText().startswith("Missing 0\n")
    screen.status_combo.setCurrentText("Complete")
    screen.render(state)
    assert screen.worklist_table.rowCount() == 0
    assert screen.repair_help.toPlainText().startswith("Local repair assistant")
