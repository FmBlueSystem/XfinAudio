"""MetadataViewModel — transforms AppState into display data for the Metadata screen."""

from __future__ import annotations

from xfinaudio.desktop.app_state import AppState


class MetadataViewModel:
    """Pure data transformer: AppState → metadata screen display values. No PySide6."""

    def status_text(self, state: AppState) -> str:
        """Return a human-readable metadata status summary.

        - No tracks: "Scan your library first to see metadata status"
        - With tracks: "{N} tracks scanned — {M} complete, {K} incomplete"
        """
        if not state.scanned_records:
            return "Scan your library first to see metadata status"
        total = len(state.scanned_records)
        complete = sum(1 for r in state.scanned_records if r.metadata_status == "complete")
        incomplete = total - complete
        return f"{total} tracks scanned — {complete} complete, {incomplete} incomplete"
