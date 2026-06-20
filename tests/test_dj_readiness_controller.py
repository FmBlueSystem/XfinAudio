from pathlib import Path
from typing import Any

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.dj_readiness_controller import DjReadinessController
from xfinaudio.quality.dj_readiness import DjReadinessCheck, DjReadinessReport


class _Label:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:
        self.text = text


class _ReviewScreen:
    def __init__(self) -> None:
        self.dj_readiness_label = _Label()
        self.readiness_table = object()


def _report() -> DjReadinessReport:
    return DjReadinessReport(
        status="needs_review",
        summary="Needs Review — 0 blocker(s), 1 review item(s); max BPM jump 10.00%",
        checks=[DjReadinessCheck(label="BPM continuity", status="needs_review", detail="Max jump is 10.00%")],
        blocker_count=0,
        review_count=1,
    )


def test_controller_delegates_readiness_building_to_injected_application_boundary(monkeypatch, tmp_path: Path) -> None:
    screen = _ReviewScreen()
    captured_tables: list[tuple[Any, DjReadinessReport]] = []
    monkeypatch.setattr(
        "xfinaudio.desktop.dj_readiness_controller.populate_dj_readiness_table",
        lambda table, report, **_: captured_tables.append((table, report)),
    )
    recommendation = object()
    quality_report = object()
    serato_plan = object()
    expected_report = _report()
    builder_calls: list[tuple[Any, Any, Any, Any]] = []

    def readiness_builder(recommendation_arg, quality_report_arg, *, serato_plan=None, serato_volume_root=None):
        builder_calls.append((recommendation_arg, quality_report_arg, serato_plan, serato_volume_root))
        return expected_report

    stored_reports: list[DjReadinessReport | None] = []
    sync_calls = 0

    def sync_state() -> None:
        nonlocal sync_calls
        sync_calls += 1

    controller = DjReadinessController(
        state=AppState(),
        review_screen=screen,  # type: ignore[arg-type]
        sync_state=sync_state,
        last_report_setter=stored_reports.append,
        readiness_builder=readiness_builder,
    )

    controller.show(
        recommendation,  # type: ignore[arg-type]
        quality_report,  # type: ignore[arg-type]
        serato_plan=serato_plan,
        serato_volume_root=tmp_path,
    )

    assert builder_calls == [(recommendation, quality_report, serato_plan, tmp_path)]
    assert stored_reports == [expected_report]
    assert sync_calls == 1
    assert screen.dj_readiness_label.text == (
        "DJ Readiness: Needs Review — 0 blocker(s), 1 review item(s); max BPM jump 10.00%"
    )
    assert captured_tables == [(screen.readiness_table, expected_report)]
