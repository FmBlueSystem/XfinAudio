"""Tests for the application-level Serato metadata worklist export use case."""

from __future__ import annotations

from pathlib import Path

from xfinaudio.application.serato_metadata_export import (
    export_metadata_status_serato_worklist,
    export_missing_field_serato_worklist,
)
from xfinaudio.exporting.serato_crate import SeratoExportPlan, SeratoWriteResult
from xfinaudio.library.models import MetadataStatus, TrackRecord


def _record(path: Path, *, status: MetadataStatus, missing: list[str] | None = None) -> TrackRecord:
    return TrackRecord(
        path=str(path),
        title=path.stem,
        metadata_status=status,
        missing_required_fields=missing or [],
    )


def test_export_metadata_status_serato_worklist_confirms_write(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        _record(tmp_path / "dd" / "_Lossless" / "Ready.flac", status="complete"),
        _record(tmp_path / "dd" / "_Lossless" / "Needs.flac", status="incomplete", missing=["camelot_key"]),
    ]
    calls: list[tuple[SeratoExportPlan, bool]] = []

    def write_crate(plan: SeratoExportPlan, *, confirm: bool = False) -> SeratoWriteResult:
        calls.append((plan, confirm))
        return SeratoWriteResult(
            written_path=plan.target_path,
            backup_path=None,
            bytes_written=len(plan.crate_bytes),
            validated=True,
            rollback_available=True,
            rollback_action="delete_created_crate",
        )

    result = export_metadata_status_serato_worklist(
        records=records,
        status="incomplete",
        serato_folder=serato_folder,
        writer=write_crate,
    )

    assert "Incomplete" in result.plan.crate_name
    assert result.library.serato_folder == serato_folder
    assert calls == [(result.plan, True)]


def test_export_missing_field_serato_worklist_confirms_write(tmp_path: Path) -> None:
    serato_folder = tmp_path / "dd" / "_Serato_"
    (serato_folder / "Subcrates").mkdir(parents=True)
    records = [
        _record(tmp_path / "dd" / "_Lossless" / "Needs Key.flac", status="incomplete", missing=["camelot_key"]),
        _record(tmp_path / "dd" / "_Lossless" / "Needs Energy.flac", status="incomplete", missing=["energy_level"]),
    ]
    calls: list[tuple[SeratoExportPlan, bool]] = []

    def write_crate(plan: SeratoExportPlan, *, confirm: bool = False) -> SeratoWriteResult:
        calls.append((plan, confirm))
        return SeratoWriteResult(
            written_path=plan.target_path,
            backup_path=None,
            bytes_written=len(plan.crate_bytes),
            validated=True,
            rollback_available=True,
            rollback_action="delete_created_crate",
        )

    result = export_missing_field_serato_worklist(
        records=records,
        missing_field="camelot_key",
        serato_folder=serato_folder,
        writer=write_crate,
    )

    assert "Missing Key" in result.plan.crate_name
    assert result.library.serato_folder == serato_folder
    assert calls == [(result.plan, True)]
