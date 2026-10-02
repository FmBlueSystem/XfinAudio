"""Tests for MetadataViewModel worklist guidance (Work Unit 7)."""

from __future__ import annotations

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.metadata_view_model import MetadataViewModel
from xfinaudio.library.models import TrackRecord


def _record(
    path: str,
    *,
    bpm: float | None = 128.0,
    camelot_key: str | None = "8A",
    energy_level: int | None = 7,
    release_year: int | None = None,
    metadata_status: str = "complete",
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=path,
        artist="Test Artist",
        bpm=bpm,
        camelot_key=camelot_key,
        energy_level=energy_level,
        release_year=release_year,
        metadata_status=metadata_status,  # type: ignore[arg-type]
    )


def _mixed_state() -> AppState:
    return AppState(
        scanned_records=[
            _record("/music/complete.flac", release_year=2001),
            _record("/music/no-bpm.flac", bpm=None, release_year=1999, metadata_status="incomplete"),
            _record(
                "/music/no-key-energy.flac",
                camelot_key=None,
                energy_level=None,
                metadata_status="incomplete",
            ),
        ]
    )


class TestWorklistGuidance:
    def test_worklist_guidance_mentions_bpm_key_energy(self) -> None:
        vm = MetadataViewModel()
        text = vm.worklist_guidance_text()
        assert text is not None
        assert "bpm" in text.lower() or "key" in text.lower() or "energy" in text.lower()

    def test_fix_metadata_guidance_mentions_external_fix(self) -> None:
        vm = MetadataViewModel()
        text = vm.fix_metadata_guidance_text()
        assert text is not None
        assert "external" in text.lower() or "tag" in text.lower() or "editor" in text.lower()

    def test_refresh_guidance_mentions_rescan(self) -> None:
        vm = MetadataViewModel()
        text = vm.refresh_guidance_text()
        assert text is not None
        assert "scan" in text.lower() or "refresh" in text.lower()

    def test_fix_guidance_marks_release_year_as_informational(self) -> None:
        """The year note is bounded: it never claims the year is required."""
        vm = MetadataViewModel()

        text = vm.fix_metadata_guidance_text()

        assert "year" in text.lower()
        assert "informational" in text.lower()


class TestGapSummary:
    def test_gap_summary_reports_per_field_missing_counts_and_year_coverage(self) -> None:
        vm = MetadataViewModel()

        text = vm.gap_summary_text(_mixed_state())

        assert "BPM: 1" in text
        assert "Key: 1" in text
        assert "Energy: 1" in text
        assert "2/3" in text

    def test_gap_summary_is_all_zero_without_scanned_records(self) -> None:
        vm = MetadataViewModel()

        text = vm.gap_summary_text(AppState())

        assert "BPM: 0" in text
        assert "Key: 0" in text
        assert "Energy: 0" in text
        assert "0/0" in text

    def test_gap_summary_uses_no_f_string_placeholders(self) -> None:
        """Translated strings carry {0}..{4} placeholders consumed by .format."""
        vm = MetadataViewModel()

        text = vm.gap_summary_text(_mixed_state())

        assert "{" not in text
        assert "}" not in text


class TestGapReportExportEnabled:
    def test_disabled_when_no_gaps_to_export(self) -> None:
        vm = MetadataViewModel()
        state = AppState(scanned_records=[_record("/music/complete.flac")])

        assert vm.gap_report_export_enabled(state) is False

    def test_enabled_when_gaps_exist_and_state_is_ready(self) -> None:
        vm = MetadataViewModel()

        assert vm.gap_report_export_enabled(_mixed_state()) is True

    def test_disabled_while_scanning_or_recommending(self) -> None:
        vm = MetadataViewModel()
        state = _mixed_state()
        state = state.model_copy(update={"is_scanning": True})
        assert vm.gap_report_export_enabled(state) is False

        state = _mixed_state()
        state = state.model_copy(update={"is_recommending": True})
        assert vm.gap_report_export_enabled(state) is False
