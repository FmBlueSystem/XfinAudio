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
