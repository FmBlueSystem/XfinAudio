"""Critical Prep/Review/destination disclosures ship in the compiled Spanish catalog."""

from pathlib import Path

import pytest
from PySide6.QtCore import QTranslator


@pytest.mark.parametrize(
    ("context", "source", "expected"),
    [
        ("BuildScreen", "Cancel Prep", "Cancelar Prep"),
        ("BuildScreen", "Generating safe variant (1/3)...", "Generando variante segura (1/3)..."),
        (
            "PrepGenerationTask",
            "Prep generation cancelled; previous results kept",
            "Generación de Prep cancelada; se conservaron los resultados anteriores",
        ),
        ("ReviewScreen", "Selected transition details", "Detalles de la transición seleccionada"),
        ("ReviewScreen", "Warnings: {0}", "Advertencias: {0}"),
    ],
)
def test_compiled_spanish_prep_review_copy(qapp, context, source, expected):
    translator = QTranslator()
    catalog = Path(__file__).resolve().parents[1] / "assets/translations/xfinaudio_es.qm"
    assert translator.load(str(catalog))
    assert translator.translate(context, source) == expected


def test_spanish_disclosure_and_report_destination_render_in_widgets(qapp):
    from xfinaudio.config.settings import AppSettings
    from xfinaudio.desktop.app_state import AppState
    from xfinaudio.desktop.export_view_model import ExportViewModel
    from xfinaudio.desktop.settings_dialog import SettingsDialog

    translator = QTranslator()
    catalog = Path(__file__).resolve().parents[1] / "assets/translations/xfinaudio_es.qm"
    assert translator.load(str(catalog))
    qapp.installTranslator(translator)
    try:
        dialog = SettingsDialog(AppSettings())
        from PySide6.QtWidgets import QLabel

        label = dialog.findChild(QLabel, "loudness_write_disclosure")
        assert label is not None
        assert "reemplaza los comentarios existentes" in label.text()
        assert "etiquetas de sonoridad" in label.text()
        assert ExportViewModel().safe_folder_label(AppState()) == "Carpeta de informes: opcional"
        assert "directamente a _Serato_/Subcrates" in ExportViewModel().destination_text()
        dialog.close()
    finally:
        qapp.removeTranslator(translator)
