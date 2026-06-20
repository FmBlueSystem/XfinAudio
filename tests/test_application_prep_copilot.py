from typing import Any

from xfinaudio.application.prep_copilot import build_prep_copilot_variant_application


def test_application_prep_copilot_builds_variant_application_result(monkeypatch) -> None:
    calls: list[Any] = []
    recommendation: Any = object()
    readiness: Any = object()
    explanation: Any = object()
    quality_report: Any = object()
    variant: Any = type(
        "Variant",
        (),
        {"name": "balanced", "recommendation": recommendation, "readiness": readiness},
    )()

    def fake_explanation_builder(recommendation_arg):
        calls.append(("explanation", recommendation_arg))
        return explanation

    def fake_quality_builder(recommendation_arg):
        calls.append(("quality", recommendation_arg))
        return quality_report

    monkeypatch.setattr("xfinaudio.application.prep_copilot._build_playlist_explanation", fake_explanation_builder)
    monkeypatch.setattr("xfinaudio.application.prep_copilot._build_quality_report", fake_quality_builder)

    result = build_prep_copilot_variant_application(variant)

    assert result.recommendation is recommendation
    assert result.explanation is explanation
    assert result.quality_report is quality_report
    assert result.readiness_report is readiness
    assert result.variant_name == "balanced"
    assert calls == [("explanation", recommendation), ("quality", recommendation)]
