"""Read-only commentary over Metadata counts and already-ranked Live candidates."""

from __future__ import annotations

from typing import Any, cast

from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QVBoxLayout

from xfinaudio.ai import structured_assists
from xfinaudio.desktop.live_assistance import live_session_ready
from xfinaudio.desktop.optional_ai_assist import OptionalAssistController, OptionalAssistPanel, Prepared
from xfinaudio.desktop.optional_ai_surfaces import add_panel, library_context
from xfinaudio.metadata.repair_guidance import prioritize_repairs
from xfinaudio.metadata.tempo import is_valid_bpm
from xfinaudio.recommendation.scoring import bpm_difference_percent, effective_energy_delta


def _commentary_panel(
    window: Any, screen: Any, index: int, disclosure: str
) -> tuple[OptionalAssistPanel, QPlainTextEdit]:
    panel = add_panel(window, screen, index, disclosure)
    output = QPlainTextEdit(panel)
    output.setReadOnly(True)
    output.setMaximumHeight(90)
    output.setAccessibleName(panel.tr("AI-generated commentary; verify against local facts"))
    output.hide()
    cast(QVBoxLayout, panel.layout()).addWidget(output)
    panel.commentary = output  # type: ignore[attr-defined]
    return panel, output


def install_explanation_controls(
    window: Any, *, services: Any = structured_assists
) -> dict[str, OptionalAssistController]:
    result = {}
    for kind, screen, index, disclosure in (
        (
            "metadata",
            window._metadata_screen,
            6,
            "Explain repairs with AI using only total tracks, missing-field counts and locked tracks needing repair.",
        ),
        (
            "live",
            window._live_assistant_screen,
            2,
            "Explain current choices with AI using anonymous candidate IDs, local ranks, scores, "
            "half-time-normalized BPM percentage gaps, absolute energy-level gaps and readiness.",
        ),
    ):
        panel, output = _commentary_panel(window, screen, index, disclosure)
        request = QLineEdit("Explain repair priorities" if kind == "metadata" else "Explain current candidates", panel)
        request.setReadOnly(True)
        request.hide()

        def clear(output: QPlainTextEdit = output) -> None:
            output.clear()
            output.hide()

        def context(kind: str = kind, screen: Any = screen) -> tuple:
            if kind == "metadata":
                return library_context(window)
            return (
                library_context(window),
                screen._session_signature,
                screen._played_paths,
                screen._locked_paths,
                screen._excluded_paths,
                id(screen._current_track),
                tuple(
                    (item.track.path, item.score.total_score, item.readiness.status)
                    for item in screen._ranked_candidates
                ),
            )

        def prepare(_: str, kind: str = kind, screen: Any = screen, output: QPlainTextEdit = output) -> Prepared:
            facts = _metadata_facts(window) if kind == "metadata" else _live_facts(screen)

            def show(value: object) -> None:
                if not isinstance(value, str) or not value.strip() or len(value) > 1200:
                    raise ValueError("Invalid commentary")
                output.setPlainText(output.tr("AI-generated commentary · verify against local facts\n") + value)
                output.show()

            return lambda: services.explain_grounded_evidence(kind, facts), show

        controller = OptionalAssistController(
            panel,
            request,
            prepare=prepare,
            context=context,
            clear=clear,
            configure=window._settings_controller.open_ai_settings_dialog,
            parent=window,
        )
        if kind == "live":
            screen.load_next_requested.connect(controller._invalidate)
            screen.exit_requested.connect(controller._invalidate)
        result[kind] = controller
    return result


def _metadata_facts(window: Any) -> list[dict[str, object]]:
    records = list(window.scanned_records)
    priorities = prioritize_repairs(records, locked_paths=window._state.locked_paths)
    if not records or not priorities:
        raise ValueError("Scan a library with missing metadata before asking AI to explain repairs.")
    return [
        {
            "id": "m0",
            "track_count": len(records),
            "missing_bpm": sum(r.bpm is None for r in records),
            "missing_key": sum(r.camelot_key is None for r in records),
            "missing_energy": sum(r.energy_level is None for r in records),
            "locked_with_gaps": sum(item.locked for item in priorities),
        }
    ]


def _live_facts(screen: Any) -> list[dict[str, object]]:
    current = screen._current_track
    if (
        current is None
        or not screen._ranked_candidates
        or not live_session_ready(
            screen._session_recommendation,
            screen._session_readiness,
            locked_paths=screen._locked_paths,
            excluded_paths=screen._excluded_paths,
            spectral_cohesion=screen._spectral_cohesion,
        )
    ):
        raise ValueError("Apply a ready set and load a current track before requesting an AI explanation.")
    facts = []
    for index, item in enumerate(screen._ranked_candidates[: len(screen._suggestion_rows)]):
        track = item.track
        bpm_delta = (
            bpm_difference_percent(current.bpm, track.bpm)
            if is_valid_bpm(current.bpm) and is_valid_bpm(track.bpm)
            else None
        )
        energy_known = (current.energy_out is not None and track.energy_in is not None) or (
            current.energy_level is not None and track.energy_level is not None
        )
        facts.append(
            {
                "id": f"c{index}",
                "rank": index + 1,
                "score": item.score.total_score,
                "bpm_delta": bpm_delta,
                "energy_delta": effective_energy_delta(current, track)[0] if energy_known else None,
                "readiness": item.readiness.status,
            }
        )
    return facts
