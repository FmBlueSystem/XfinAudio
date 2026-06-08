"""MetadataViewModel — transforms AppState into display data for the Metadata screen."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QCoreApplication

from xfinaudio.desktop.app_state import AppState

_MISSING_FIELD_MAP = {
    "Missing BPM": "bpm",
    "Missing Key": "camelot_key",
    "Missing Energy": "energy_level",
}


@dataclass(frozen=True)
class WorklistRow:
    """One row in the metadata worklist table."""

    path: str
    title: str
    artist: str
    bpm: str
    key: str
    energy: str
    missing: str
    status: str


class MetadataViewModel:
    """Pure data transformer: AppState → metadata screen display values. No PySide6."""

    def status_text(self, state: AppState) -> str:
        """Return a human-readable metadata status summary.

        - No tracks: "Scan your library first to see metadata status"
        - With tracks: "{N} tracks scanned — {M} complete, {K} incomplete"
        """
        if not state.scanned_records:
            return QCoreApplication.translate(
                "MetadataViewModel",
                "Scan your library first to see metadata status",
            )
        total = len(state.scanned_records)
        complete = sum(1 for r in state.scanned_records if r.metadata_status == "complete")
        incomplete = total - complete
        return QCoreApplication.translate(
            "MetadataViewModel",
            "{0} tracks scanned — {1} complete, {2} incomplete",
        ).format(total, complete, incomplete)

    def worklist_rows(
        self,
        state: AppState,
        status_filter: str | None = None,
        missing_filter: str | None = None,
    ) -> list[WorklistRow]:
        """Incomplete tracks matching the active filters. Empty when no tracks scanned."""
        records = state.scanned_records
        if not records:
            return []

        # Normalise status filter
        norm_status: str | None = None
        all_label = QCoreApplication.translate("MetadataViewModel", "All")
        if status_filter and status_filter.casefold() not in (all_label.casefold(), ""):
            complete_label = QCoreApplication.translate("MetadataViewModel", "Complete")
            incomplete_label = QCoreApplication.translate("MetadataViewModel", "Incomplete")
            if status_filter.casefold() == complete_label.casefold():
                norm_status = "complete"
            elif status_filter.casefold() == incomplete_label.casefold():
                norm_status = "incomplete"
            else:
                norm_status = status_filter.casefold()

        # Resolve missing-field filter label → internal field name
        missing_field: str | None = None
        if missing_filter and missing_filter.casefold() not in (all_label.casefold(), ""):
            translated_map = {
                QCoreApplication.translate("MetadataViewModel", k): v for k, v in _MISSING_FIELD_MAP.items()
            }
            missing_field = translated_map.get(missing_filter, missing_filter)

        rows: list[WorklistRow] = []
        for record in records:
            # Status filter
            if norm_status is not None and record.metadata_status != norm_status:
                continue
            # Missing-field filter
            if missing_field is not None and missing_field not in record.missing_required_fields:
                continue

            bpm = str(int(record.bpm)) if record.bpm is not None else "—"
            key = record.camelot_key if record.camelot_key is not None else "—"
            energy = str(record.energy_level) if record.energy_level is not None else "—"
            missing_str = ", ".join(record.missing_required_fields) if record.missing_required_fields else "—"

            rows.append(
                WorklistRow(
                    path=record.path,
                    title=record.title or "—",
                    artist=record.artist or "—",
                    bpm=bpm,
                    key=key,
                    energy=energy,
                    missing=missing_str,
                    status=record.metadata_status,
                )
            )
        return rows

    @staticmethod
    def status_filter_options() -> list[str]:
        """["All", "Complete", "Incomplete"]"""
        return [
            QCoreApplication.translate("MetadataViewModel", "All"),
            QCoreApplication.translate("MetadataViewModel", "Complete"),
            QCoreApplication.translate("MetadataViewModel", "Incomplete"),
        ]

    @staticmethod
    def missing_filter_options() -> list[str]:
        """["All", "Missing BPM", "Missing Key", "Missing Energy"]"""
        return [
            QCoreApplication.translate("MetadataViewModel", "All"),
            QCoreApplication.translate("MetadataViewModel", "Missing BPM"),
            QCoreApplication.translate("MetadataViewModel", "Missing Key"),
            QCoreApplication.translate("MetadataViewModel", "Missing Energy"),
        ]

    def export_enabled(self, state: AppState) -> bool:
        """True when there are incomplete tracks to export."""
        return any(r.metadata_status == "incomplete" for r in state.scanned_records)

    def worklist_guidance_text(self) -> str:
        """Explain the purpose of the metadata worklist."""
        return QCoreApplication.translate(
            "MetadataViewModel",
            "The worklist shows tracks missing BPM, Key, or Energy. "
            "These fields are required for harmonic mixing recommendations.",
        )

    def fix_metadata_guidance_text(self) -> str:
        """Explain how to fix missing metadata."""
        return QCoreApplication.translate(
            "MetadataViewModel",
            "Fix missing tags in an external tag editor, then return to XfinAudio.",
        )

    def refresh_guidance_text(self) -> str:
        """Explain how to refresh after fixing metadata."""
        return QCoreApplication.translate(
            "MetadataViewModel",
            "Refresh the library scan to pick up corrected metadata.",
        )
