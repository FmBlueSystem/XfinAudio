"""Stateless presentation helpers for the XfinAudio desktop UI."""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QTableWidgetItem

from xfinaudio.audio.spectral_profile import format_spectral_color as _spectral_color_formatter
from xfinaudio.library.models import TrackRecord
from xfinaudio.quality.recommendation_quality import RecommendationQualityReport

_FIELD_LABELS = {
    "bpm": QCoreApplication.translate("Rendering", "BPM"),
    "camelot_key": QCoreApplication.translate("Rendering", "Camelot key"),
    "energy_level": QCoreApplication.translate("Rendering", "energy level"),
    "duration": QCoreApplication.translate("Rendering", "Duration"),
}


def format_quality_summary(report: RecommendationQualityReport) -> str:
    """Return a desktop-friendly quality summary for a recommendation report."""
    return QCoreApplication.translate(
        "Rendering",
        "Review summary: Tracks: {0} | Transitions: {1} | Average transition score: {2:.3f} | Warnings: {3}",
    ).format(
        report.track_count,
        report.transition_count,
        report.average_transition_score,
        report.warning_count,
    )


def _format_review_score(score: float | None) -> str:
    """Format a transition review score or return an empty cell for unavailable scores."""
    if score is None:
        return ""
    return f"{score:.3f}"


def _score_sort_value(score: float | None) -> float:
    """Sort unavailable scores before explicit zero scores."""
    return score if score is not None else -1.0


def _format_track_tags(track: TrackRecord) -> str:
    """Return display text for tags, including parsed subgenre-style metadata."""
    return ", ".join(track.tags)


def _format_missing_metadata(track: TrackRecord) -> str:
    """Return readable missing metadata field names for incomplete-track worklists."""
    return ", ".join(
        _FIELD_LABELS.get(field_name, field_name.replace("_", " ")) for field_name in track.missing_required_fields
    )


def _format_spectral_color(track: TrackRecord) -> str:
    """Return a compact spectral color badge for the track table."""
    return _spectral_color_formatter(track.spectral_profile)


def _missing_worklist_display_name(missing_field: str) -> str:
    """Return compact DJ-facing field labels for missing-field worklists."""
    labels = {
        "bpm": QCoreApplication.translate("Rendering", "BPM"),
        "camelot_key": QCoreApplication.translate("Rendering", "Key"),
        "energy_level": QCoreApplication.translate("Rendering", "Energy"),
    }
    return labels.get(missing_field, missing_field.replace("_", " ").title())


def _track_vibe_terms(track: TrackRecord) -> set[str]:
    """Return normalized genre/tag terms for desktop candidate compatibility."""
    values = [*track.tags]
    if track.genre:
        values.extend(track.genre.split(","))
        values.append(track.genre)
    return {value.strip().casefold() for value in values if value.strip()}


def _track_similarity_key(
    anchor_terms: set[str],
    anchor_tracks: list[TrackRecord],
    track: TrackRecord,
) -> tuple[int, float, float, str]:
    """Sort compatible DJ candidates before unrelated fallback tracks."""
    terms = _track_vibe_terms(track)
    overlap_count = len(anchor_terms & terms)
    bpm_distance = min(
        (abs((track.bpm or 0.0) - (anchor.bpm or 0.0)) for anchor in anchor_tracks if anchor.bpm is not None),
        default=9999.0,
    )
    energy_distance = min(
        (
            abs((track.energy_level or 0) - (anchor.energy_level or 0))
            for anchor in anchor_tracks
            if anchor.energy_level is not None
        ),
        default=9999,
    )
    return (-overlap_count, bpm_distance, float(energy_distance), track.path)


def _track_review_name(track: object) -> str:
    """Return a compact track label for transition review cells."""
    title = getattr(track, "title", None)
    if title:
        return str(title)
    return str(getattr(track, "path", ""))


def _component_score(transition: object, field_name: str, component_name: str) -> float | None:
    """Read preferred explanation score fields while preserving explicit zero scores."""
    score = getattr(transition, field_name, None)
    if score is not None:
        return score
    component_scores = getattr(transition, "component_scores", {})
    return component_scores.get(component_name)


def format_recommendation_warning(raw_warning: str) -> str:
    """Return desktop-friendly text for a raw recommendation warning."""
    warning = raw_warning.strip()
    if not warning:
        return ""

    missing_marker = " missing required metadata: "
    if missing_marker in warning:
        side, _, fields_text = warning.partition(missing_marker)
        fields = [_FIELD_LABELS.get(field.strip(), field.strip().replace("_", " ")) for field in fields_text.split(",")]
        return QCoreApplication.translate(
            "Rendering",
            "Review metadata: {0} track is missing Mixed In Key {1} metadata. "
            "Re-scan or update tags before relying on this transition.",
        ).format(side, ", ".join(fields))

    invalid_marker = " has invalid Camelot key: "
    if invalid_marker in warning:
        side, _, key = warning.partition(invalid_marker)
        return QCoreApplication.translate(
            "Rendering",
            "Review Mixed In Key metadata: {0} track has invalid Camelot key {1!r}. "
            "Expected values look like 8A or 11B.",
        ).format(side, key)

    if warning == "invalid Camelot key":
        return QCoreApplication.translate(
            "Rendering",
            "Review Mixed In Key metadata: at least one transition has an invalid Camelot key.",
        )

    return QCoreApplication.translate("Rendering", "Review note: {0}").format(warning)


class _SortAwareTableItem(QTableWidgetItem):
    """Table item that sorts by typed values while displaying compact text."""

    def __init__(self, display_value: str, sort_value: object | None = None) -> None:
        super().__init__(display_value)
        self._sort_value = sort_value if sort_value is not None else display_value.casefold()

    def __lt__(self, other: QTableWidgetItem) -> bool:
        other_value = getattr(other, "_sort_value", other.text().casefold())
        try:
            return self._sort_value < other_value  # type: ignore[operator]
        except TypeError:
            return str(self._sort_value).casefold() < str(other_value).casefold()


def _table_item(display_value: str, sort_value: object | None = None) -> QTableWidgetItem:
    """Build a table item with a stable display value and optional typed sort value."""
    return _SortAwareTableItem(display_value, sort_value)


# ---------------------------------------------------------------------------
# Genre enrichment presentation helpers
# ---------------------------------------------------------------------------

# Confidence thresholds for the genre badge (desktop visual indicator).
_GENRE_BADGE_HIGH_THRESHOLD = 0.7
_GENRE_BADGE_MEDIUM_THRESHOLD = 0.4


def format_genre_decision(track: TrackRecord) -> str:
    """Return the canonical (enriched) genre, falling back to the file-tag genre.

    Returns an empty string when the track has neither.
    """
    from xfinaudio.genre.effective_genre import effective_genre

    return effective_genre(track) or ""


def format_genre_badge(track: TrackRecord) -> str:
    """Return a compact confidence badge for the track's genre decision.

    Empty when the track has no decision. The badge combines an indicator
    character with a confidence value so the user can scan the table at a
    glance and still see the exact score.
    """
    decision = track.genre_decision
    if decision is None or decision.primary is None:
        return ""
    if decision.low_confidence or decision.confidence < _GENRE_BADGE_MEDIUM_THRESHOLD:
        return f"❓ low ({decision.confidence:.2f})"
    if decision.confidence >= _GENRE_BADGE_HIGH_THRESHOLD:
        return f"🎯 high ({decision.confidence:.2f})"
    return f"🟡 med ({decision.confidence:.2f})"


def format_genre_cell(track: TrackRecord) -> str:
    """Return the combined genre cell text: canonical genre + badge."""
    canonical = format_genre_decision(track)
    if not canonical:
        return ""
    badge = format_genre_badge(track)
    if badge:
        return f"{canonical}  {badge}"
    return canonical


def format_genre_sources_tooltip(track: TrackRecord) -> str:
    """Return a multi-line explainability tooltip for the track's genre decision.

    Lists the canonical primary, confidence, low-confidence flag, top-N
    candidates, and per-source contributions. Empty when no decision exists.
    """
    decision = track.genre_decision
    if decision is None:
        return ""

    lines: list[str] = []
    lines.append(f"Canonical: {decision.primary or '(none)'}")
    lines.append(f"Confidence: {decision.confidence:.2f}")
    if decision.low_confidence:
        lines.append("Low confidence: yes")
    if decision.top_n:
        top_list = (
            ", ".join(decision.top_n)
            if len(decision.top_n) <= 4
            else (", ".join(decision.top_n[:3]) + f", +{len(decision.top_n) - 3} more")
        )
        lines.append(f"Top-N: {top_list}")
    if decision.provenance.scores:
        lines.append("Scores:")
        for genre, score in decision.provenance.scores.items():
            lines.append(f"  {genre}: {score:.2f}")
    if decision.provenance.candidates:
        sources = sorted({c.source for c in decision.provenance.candidates})
        lines.append(f"Sources: {', '.join(sources)}")
    return "\n".join(lines)
