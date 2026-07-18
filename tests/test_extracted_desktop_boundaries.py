from xfinaudio.desktop.main_window_layout import responsive_sidebar_width
from xfinaudio.desktop.serato_metadata_worklist_export import MetadataWorklistExport, SeratoMetadataWorklistExportMixin
from xfinaudio.desktop.serato_recommendation_export import SeratoRecommendationExportMixin
from xfinaudio.desktop.software_export_coordinator import SoftwareExportCoordinator, SoftwareExportCoordinatorMixin
from xfinaudio.desktop.window_service_wiring import wire_main_scan_service, wire_services


def test_responsive_sidebar_width_has_two_layout_states() -> None:
    assert responsive_sidebar_width(899) == 120
    assert responsive_sidebar_width(900) == 180


def test_wire_services_invokes_scan_then_recommendation() -> None:
    calls = []
    wire_services(lambda: calls.append("scan"), lambda: calls.append("recommendation"))
    assert calls == ["scan", "recommendation"]


def test_software_export_coordinator_forwards_arguments() -> None:
    calls = []
    boundary = SoftwareExportCoordinator(lambda **kwargs: calls.append(kwargs))
    boundary.run(crate_name="Set")
    assert calls == [{"crate_name": "Set"}]


def test_metadata_worklist_export_forwards_arguments() -> None:
    calls = []
    boundary = MetadataWorklistExport(lambda **kwargs: calls.append(kwargs))
    boundary.run(status="incomplete")
    assert calls == [{"status": "incomplete"}]


def test_extracted_boundaries_own_real_responsibilities() -> None:
    assert "preview_export" in SoftwareExportCoordinatorMixin.__dict__
    assert "preview_serato_export" in SeratoRecommendationExportMixin.__dict__
    assert "export_metadata_status_to_serato" in SeratoMetadataWorklistExportMixin.__dict__
    assert callable(wire_main_scan_service)
