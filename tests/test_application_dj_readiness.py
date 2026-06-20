from pathlib import Path
from typing import Any

from xfinaudio.application.dj_readiness import build_application_dj_readiness_report
from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport


def _report() -> DjReadinessReport:
    return DjReadinessReport(
        status="ready",
        summary="Ready — 0 blocker(s), 0 review item(s); max BPM jump 0.00%",
        checks=[DjReadinessCheck(label="Playlist size", status="ready", detail="2 tracks available")],
        blocker_count=0,
        review_count=0,
    )


def test_application_dj_readiness_delegates_to_quality_builder(monkeypatch) -> None:
    calls: list[tuple[Any, Any, Any, Any]] = []
    expected = _report()

    def fake_builder(recommendation, quality_report, *, serato_plan=None, serato_volume_root=None):
        calls.append((recommendation, quality_report, serato_plan, serato_volume_root))
        return expected

    monkeypatch.setattr("xfinaudio.application.dj_readiness._build_dj_readiness_report", fake_builder)
    recommendation: Any = object()
    quality_report: Any = object()

    report = build_application_dj_readiness_report(recommendation, quality_report)

    assert report is expected
    assert calls == [(recommendation, quality_report, None, None)]


def test_application_dj_readiness_preserves_optional_serato_context(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[Any, Any, Any, Any]] = []
    expected = _report()

    def fake_builder(recommendation, quality_report, *, serato_plan=None, serato_volume_root=None):
        calls.append((recommendation, quality_report, serato_plan, serato_volume_root))
        return expected

    monkeypatch.setattr("xfinaudio.application.dj_readiness._build_dj_readiness_report", fake_builder)
    recommendation: Any = object()
    quality_report: Any = object()
    serato_plan: Any = object()

    report = build_application_dj_readiness_report(
        recommendation,
        quality_report,
        serato_plan=serato_plan,
        serato_volume_root=tmp_path,
    )

    assert report is expected
    assert calls == [(recommendation, quality_report, serato_plan, tmp_path)]
