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


def test_application_prep_copilot_generation_builds_intent_and_delegates() -> None:
    from xfinaudio.application.prep_copilot import PrepCopilotGenerationRequest, generate_prep_copilot_plan

    records: list[Any] = [object()]
    generated_plan: Any = object()
    calls: list[tuple[Any, Any]] = []

    def fake_plan_builder(records_arg: Any, intent_arg: Any) -> Any:
        calls.append((records_arg, intent_arg))
        return generated_plan

    request = PrepCopilotGenerationRequest(
        strategy="build",
        target_track_count=12,
        start_path="/music/start.flac",
        required_paths=["/music/start.flac", "/music/must.flac"],
        genre_focus="House",
    )

    result = generate_prep_copilot_plan(records, request, plan_builder=fake_plan_builder)

    assert result is generated_plan
    assert calls[0][0] is records
    intent = calls[0][1]
    assert intent.name == "Desktop Prep Copilot"
    assert intent.strategy == "build"
    assert intent.target_track_count == 12
    assert intent.start_path == "/music/start.flac"
    assert intent.required_paths == ["/music/start.flac", "/music/must.flac"]
    assert intent.genre_focus == "House"
