"""Regression coverage for the loudness module's shipped translation catalogs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QTranslator
from PySide6.QtWidgets import QApplication

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CATALOGS = {
    "en": {
        "Consistent Loudness": "Consistent Loudness",
        "Hard filter: measured tracks must stay within the configured integrated loudness band.": (
            "Hard filter: measured tracks must stay within the configured integrated loudness band."
        ),
        "Loudness Settings": "Loudness Settings",
        "Enable loudness analysis": "Enable loudness analysis",
        "Target LUFS:": "Target LUFS:",
        "Tolerance LU:": "Tolerance LU:",
        "Analyzing loudness {0:,}/{1:,}": "Analyzing loudness {0:,}/{1:,}",
        "Selected track loudness details": "Selected track loudness details",
        "Selected track loudness measurements": "Selected track loudness measurements",
        "True peak status": "True peak status",
        "Loudness: not measured": "Loudness: not measured",
        "Loudness: unavailable (too short)": "Loudness: unavailable (too short)",
        "LUFS: {0:.1f} · LRA: unavailable · True peak: unavailable (too short)": (
            "LUFS: {0:.1f} · LRA: unavailable · True peak: unavailable (too short)"
        ),
        "Loudness: unmeasurable": "Loudness: unmeasurable",
        "Loudness: temporarily unavailable": "Loudness: temporarily unavailable",
        "Loudness: unsupported": "Loudness: unsupported",
        "Loudness: incomplete measurement": "Loudness: incomplete measurement",
        "LUFS: {0:.1f} · LRA: {1:.1f} · True peak: {2:.1f} dBTP": (
            "LUFS: {0:.1f} · LRA: {1:.1f} · True peak: {2:.1f} dBTP"
        ),
        "True peak clipping": "True peak clipping",
        "True peak warning": "True peak warning",
        "Reanalyze loudness": "Reanalyze loudness",
    },
    "es": {
        "Consistent Loudness": "Sonoridad consistente",
        "Hard filter: measured tracks must stay within the configured integrated loudness band.": (
            "Filtro estricto: las pistas medidas deben mantenerse dentro de la banda de sonoridad integrada "
            "configurada."
        ),
        "Loudness Settings": "Configuración de sonoridad",
        "Enable loudness analysis": "Activar análisis de sonoridad",
        "Target LUFS:": "LUFS objetivo:",
        "Tolerance LU:": "Tolerancia LU:",
        "Analyzing loudness {0:,}/{1:,}": "Analizando sonoridad {0:,}/{1:,}",
        "Selected track loudness details": "Detalles de sonoridad de la pista seleccionada",
        "Selected track loudness measurements": "Mediciones de sonoridad de la pista seleccionada",
        "True peak status": "Estado del pico verdadero",
        "Loudness: not measured": "Sonoridad: sin medir",
        "Loudness: unavailable (too short)": "Sonoridad: no disponible (demasiado corta)",
        "LUFS: {0:.1f} · LRA: unavailable · True peak: unavailable (too short)": (
            "LUFS: {0:.1f} · LRA: no disponible · Pico verdadero: no disponible (demasiado corta)"
        ),
        "Loudness: unmeasurable": "Sonoridad: no medible",
        "Loudness: temporarily unavailable": "Sonoridad: temporalmente no disponible",
        "Loudness: unsupported": "Sonoridad: no compatible",
        "Loudness: incomplete measurement": "Sonoridad: medición incompleta",
        "LUFS: {0:.1f} · LRA: {1:.1f} · True peak: {2:.1f} dBTP": (
            "LUFS: {0:.1f} · LRA: {1:.1f} · Pico verdadero: {2:.1f} dBTP"
        ),
        "True peak clipping": "Pico verdadero con recorte",
        "True peak warning": "Advertencia de pico verdadero",
        "Reanalyze loudness": "Volver a analizar sonoridad",
    },
}
_BUILD_VIEW_MODEL_SOURCES = frozenset(list(_CATALOGS["en"])[:2])
_SETTINGS_DIALOG_SOURCES = frozenset(list(_CATALOGS["en"])[2:6])


def _catalog_messages(language: str) -> dict[str, ET.Element]:
    root = ET.parse(_REPO_ROOT / "translations" / f"xfinaudio_{language}.ts").getroot()
    return {
        message.findtext("source", ""): message
        for context in root.findall("context")
        for message in context.findall("message")
    }


@pytest.mark.parametrize("language", ("en", "es"))
def test_loudness_ts_entries_are_finished(language: str) -> None:
    messages = _catalog_messages(language)

    for source, expected in _CATALOGS[language].items():
        message = messages[source]
        translation = message.find("translation")
        assert translation is not None
        assert translation.attrib.get("type") != "unfinished"
        assert translation.text == expected


@pytest.mark.parametrize("language", ("en", "es"))
def test_loudness_qm_catalog_translates_every_new_string(language: str) -> None:
    app = QApplication.instance() or QApplication([])
    translator = QTranslator()

    assert translator.load(str(_REPO_ROOT / "assets" / "translations" / f"xfinaudio_{language}.qm"))
    app.installTranslator(translator)
    try:
        for source, expected in _CATALOGS[language].items():
            context = (
                "BuildViewModel"
                if source in _BUILD_VIEW_MODEL_SOURCES
                else "SettingsDialog"
                if source in _SETTINGS_DIALOG_SOURCES
                else "LibraryScreen"
            )
            assert QCoreApplication.translate(context, source) == expected
    finally:
        app.removeTranslator(translator)
