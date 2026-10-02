"""Neutral guidance preserves the desktop contract without importing Qt or writing tags."""

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.metadata_gaps import build_metadata_gap_report


def _records():
    return [
        TrackRecord(path="/private/z.mp3", title="One gap", bpm=120, camelot_key="8A", release_year=1999),
        TrackRecord(path="/private/a.mp3", title="Locked", bpm=124, metadata_status="complete"),
        TrackRecord(path="/private/b.mp3", title="Complete", bpm=122, camelot_key="8A", energy_level=5),
        TrackRecord(path="/private/c.mp3", bpm=125, camelot_key="9A", missing_required_fields=["bpm"]),
    ]


def test_core_preserves_priority_text_and_injected_translation():
    from xfinaudio.metadata.repair_guidance_core import explain_track_gaps, prioritize_repairs, repair_plan_text

    records = _records()
    locks = frozenset({records[1].path})
    before = [record.model_dump() for record in records]
    priorities = prioritize_repairs(records, locked_paths=locks)
    assert [item.path for item in priorities] == [records[1].path, records[3].path, records[0].path]
    assert priorities[0].missing_fields == ("camelot_key", "energy_level")
    assert priorities[1].title == "Untitled"
    text = explain_track_gaps(records[1])
    assert "harmonic" in text and "energy" in text and "not inferred" in text
    assert "BPM is missing" not in text
    assert "Release year is informational only" in explain_track_gaps(records[2])

    def translated(text):
        return f"translated:{text}"

    assert prioritize_repairs(records, translate=translated)[0].title == "translated:Untitled"
    assert explain_track_gaps(records[1], translate=translated).startswith("translated:Key")
    assert repair_plan_text([], translate=translated).startswith("translated:Local repair assistant")
    assert "No required metadata gaps found" in repair_plan_text([])
    many = [TrackRecord(path=f"/{index:02}.mp3") for index in range(12)]
    assert "2 more tracks" in repair_plan_text(many)
    assert "[locked]" in repair_plan_text(records, locked_paths=locks)
    assert [record.model_dump() for record in records] == before


def test_report_projects_domain_counts_years_priorities_and_opaque_tracks():
    from xfinaudio.headless.metadata_report import build_metadata_report
    from xfinaudio.metadata.repair_guidance_core import explain_track_gaps, repair_plan_text

    records = _records()
    locks = frozenset({records[1].path})
    before = [record.model_dump() for record in records]
    domain = build_metadata_gap_report(records)
    report = build_metadata_report(iter(records), locked_paths=locks)
    assert report["totalTracks"] == domain.total_tracks == 4
    assert report["completeCount"] == domain.complete_count == 1
    assert report["incompleteCount"] == domain.incomplete_count == 3
    assert report["gaps"] == domain.gaps.model_dump() == {"bpm": 0, "camelot_key": 1, "energy_level": 3}
    assert report["yearCoverage"] == {"withReleaseYear": 1, "withoutReleaseYear": 3}
    assert report["readOnly"] is True
    assert report["repairPlan"] == repair_plan_text(records, locked_paths=locks)
    assert [track["priority"] for track in report["tracks"]] == [1, 2, 3]
    for track, entry in zip(report["tracks"], domain.entries, strict=True):
        record = next(record for record in records if record.path == entry.path)
        assert track == {
            "id": hashlib.sha256(entry.path.encode("utf-8")).hexdigest(),
            "title": entry.title or "Untitled",
            "artist": entry.artist or "",
            "releaseYear": entry.release_year,
            "missingFields": entry.missing_fields,
            "explanation": explain_track_gaps(record),
            "locked": entry.path in locks,
            "priority": track["priority"],
        }
    assert "/private/" not in json.dumps(report)
    assert [record.model_dump() for record in records] == before
    assert build_metadata_report(reversed(records), locked_paths=locks) == report
    unlocked = build_metadata_report(records)
    assert [track["priority"] for track in unlocked["tracks"]] == [3, 1, 2]


@pytest.mark.parametrize("records", [[], [_records()[2]]])
def test_report_empty_or_complete_preserves_informational_year_semantics(records):
    from xfinaudio.headless.metadata_report import build_metadata_report

    report = build_metadata_report(records)
    assert report["tracks"] == []
    assert report["incompleteCount"] == 0
    assert report["completeCount"] == len(records)
    assert report["yearCoverage"] == {"withReleaseYear": 0, "withoutReleaseYear": len(records)}
    assert "No required metadata gaps found" in report["repairPlan"]


def test_report_reads_records_without_reading_or_writing_audio(tmp_path):
    from xfinaudio.headless.metadata_report import build_metadata_report

    path = tmp_path / "private.mp3"
    path.write_bytes(b"audio fixture must not be opened")
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    report = build_metadata_report([TrackRecord(path=str(path))])
    assert report["tracks"][0]["title"] == "Untitled"
    assert str(path) not in json.dumps(report)
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before


def test_neutral_guidance_and_report_imports_enforce_qt_firewall():
    script = """
import importlib.abc
import sys
class RejectQt(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in {"PySide6", "PyQt6", "PyQt5", "shiboken6"}:
            raise AssertionError("Forbidden Qt import: " + fullname)
sys.meta_path.insert(0, RejectQt())
from xfinaudio.metadata.repair_guidance_core import repair_plan_text
from xfinaudio.headless.metadata_report import build_metadata_report
from xfinaudio.library.models import TrackRecord
assert "read-only" in repair_plan_text([])
assert build_metadata_report([TrackRecord(path="/private/a.mp3")])["incompleteCount"] == 1
assert not any(name.startswith(("PySide6", "PyQt6", "PyQt5", "shiboken6")) for name in sys.modules)
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.skipif(importlib.util.find_spec("PySide6") is None, reason="Legacy adapter requires Qt environment")
def test_legacy_wrapper_preserves_type_translation_context_and_output(monkeypatch):
    from xfinaudio.metadata import repair_guidance as legacy
    from xfinaudio.metadata import repair_guidance_core as core

    calls = []

    def translate(context, text):
        calls.append(context)
        return f"translated:{text}"

    monkeypatch.setattr(legacy.QCoreApplication, "translate", translate)

    def translator(text):
        return f"translated:{text}"

    locks = frozenset({_records()[1].path})
    assert legacy.RepairPriority is core.RepairPriority
    assert legacy.prioritize_repairs(_records(), locked_paths=locks) == core.prioritize_repairs(
        _records(), locked_paths=locks, translate=translator
    )
    assert legacy.explain_track_gaps(_records()[1]) == core.explain_track_gaps(_records()[1], translate=translator)
    assert legacy.repair_plan_text(_records(), locked_paths=locks) == core.repair_plan_text(
        _records(), locked_paths=locks, translate=translator
    )
    assert calls and set(calls) == {"MetadataRepairGuidance"}
