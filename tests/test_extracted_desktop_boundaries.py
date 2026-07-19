from types import SimpleNamespace

from xfinaudio.desktop import export_coordinator
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
    calls = []
    scan_service = SimpleNamespace(
        set_state_accessors=lambda **kwargs: calls.append(("state", kwargs)),
        set_ui=lambda **kwargs: calls.append(("ui", kwargs)),
        set_actions=lambda **kwargs: calls.append(("actions", kwargs)),
    )
    host = SimpleNamespace(
        _scan_service=scan_service,
        selected_folder=None,
        scanned_records=[],
        _state=object(),
        _library_screen=object(),
        _build_screen=object(),
        status_label=object(),
        scan_progress_label=object(),
        library_guidance_label=object(),
        recommendation_guidance_label=object(),
        tr=lambda text: text,
        _sync_state=lambda: None,
        show_tracks=lambda: None,
        _clear_scan_dependent_state=lambda: None,
        _refresh_idle_action_state=lambda: None,
        _cancel_spectral_completion_worker=lambda: None,
    )

    wire_main_scan_service(host)

    assert [name for name, _kwargs in calls] == ["state", "ui", "actions"]
    assert calls[0][1]["state"] is host._state
    assert calls[1][1]["library_screen"] is host._library_screen


def test_extracted_export_previews_update_user_visible_guidance(monkeypatch, tmp_path) -> None:
    class Label:
        text = ""

        def setText(self, value):
            self.text = value

    recommendation = SimpleNamespace(ordered_tracks=[1, 2])
    host = SimpleNamespace(
        last_recommendation=recommendation,
        settings=SimpleNamespace(export=SimpleNamespace(safe_export_folder=tmp_path)),
        applied_prep_copilot_variant_name=None,
        last_dj_readiness_report=None,
        status_label=Label(),
        _export_screen=SimpleNamespace(export_guidance_label=Label()),
        tr=lambda text: text,
    )

    class SoftwareBoundary(SoftwareExportCoordinatorMixin):
        _host = host

        def selected_software(self):
            return "Rekordbox"

        def _build_export_gate_request(self, *_args):
            return object()

        def _handle_denied_export_gate(self, *_args):
            return False

    monkeypatch.setattr(export_coordinator, "evaluate_export_gate", lambda _request: object())
    monkeypatch.setattr(
        export_coordinator,
        "preview_playlist_file_export",
        lambda **_kwargs: SimpleNamespace(target_path=tmp_path / "set.m3u8"),
    )
    SoftwareBoundary().preview_export(crate_name="Set")
    assert "Rekordbox export preview" in host.status_label.text
    assert "Tracks: 2" in host._export_screen.export_guidance_label.text

    class SeratoBoundary(SeratoRecommendationExportMixin):
        _host = host

        def _build_export_gate_request(self, *_args):
            return object()

        def _handle_denied_export_gate(self, *_args):
            return False

        def _plan_current_serato_export(self, **_kwargs):
            return SimpleNamespace(target_path=tmp_path / "Set.crate", relative_paths=["a", "b"]), object()

    SeratoBoundary().preview_serato_export(crate_name="Set")
    assert "Serato export preview" in host.status_label.text
    assert "Tracks: 2" in host._export_screen.export_guidance_label.text


def test_extracted_metadata_export_routes_missing_field(tmp_path) -> None:
    calls = []
    host = SimpleNamespace(
        _selected_missing_metadata_filter=lambda: "artist",
        _selected_metadata_status_filter=lambda: "incomplete",
    )

    class Boundary(SeratoMetadataWorklistExportMixin):
        _host = host

        def _export_missing_metadata_worklist_to_serato(self, field, *, serato_folder=None):
            calls.append((field, serato_folder))

    folder = tmp_path / "_Serato_"
    Boundary().export_metadata_status_to_serato(serato_folder=folder)
    assert calls == [("artist", folder)]


def test_generic_write_updates_visible_status_and_forwards_export_arguments(monkeypatch, tmp_path) -> None:
    label = SimpleNamespace(text="", setText=lambda value: setattr(label, "text", value))
    guidance = SimpleNamespace(text="", setText=lambda value: setattr(guidance, "text", value))
    recommendation = SimpleNamespace(ordered_tracks=[1])
    host = SimpleNamespace(
        last_recommendation=recommendation,
        settings=SimpleNamespace(export=SimpleNamespace(safe_export_folder=tmp_path)),
        applied_prep_copilot_variant_name="Warm",
        status_label=label,
        _export_screen=SimpleNamespace(export_guidance_label=guidance),
        tr=lambda text: text,
    )
    forwarded = []

    class Boundary(SoftwareExportCoordinatorMixin):
        _host = host

        def selected_software(self):
            return "Rekordbox"

        def _build_export_gate_request(self, *_args):
            return object()

        def _handle_denied_export_gate(self, *_args):
            return False

    monkeypatch.setattr(export_coordinator, "evaluate_export_gate", lambda _request: object())
    monkeypatch.setattr(
        export_coordinator,
        "export_playlist_file",
        lambda **kwargs: forwarded.append(kwargs) or SimpleNamespace(written_path=tmp_path / "Set.m3u8"),
    )
    Boundary().export_recommendation(crate_name="Set")
    assert forwarded[0]["recommendation"] is recommendation
    assert forwarded[0]["requested_name"] == "Set"
    assert "Exported Rekordbox playlist" in label.text
    assert "playlist exported" in guidance.text


def test_serato_write_observes_backup_sidecars_history_and_callback(monkeypatch, tmp_path) -> None:
    label = SimpleNamespace(text="", setText=lambda value: setattr(label, "text", value))
    guidance = SimpleNamespace(text="", setText=lambda value: setattr(guidance, "text", value))
    recommendation = SimpleNamespace(ordered_tracks=[1], strategy=SimpleNamespace(name="Flow"))
    host = SimpleNamespace(
        last_recommendation=recommendation,
        applied_prep_copilot_variant_name="Warm",
        last_quality_report=None,
        last_dj_readiness_report=object(),
        settings=SimpleNamespace(export=SimpleNamespace(safe_export_folder=tmp_path)),
        status_label=label,
        _export_screen=SimpleNamespace(
            export_guidance_label=guidance,
            history_table=SimpleNamespace(setVisible=lambda visible: history_visibility.append(visible)),
        ),
        serato_export_history=[],
        _sync_state=lambda: sync_calls.append("sync"),
        tr=lambda text: text,
    )
    callbacks = []
    history_visibility = []
    sync_calls = []

    class Boundary(SeratoRecommendationExportMixin):
        _host = host

        def _on_export_success(self):
            callbacks.append("success")

        def _build_export_gate_request(self, *_args):
            return object()

        def _handle_denied_export_gate(self, *_args):
            return False

    written = tmp_path / "Set.crate"
    backup = tmp_path / "Set.crate.bak"
    monkeypatch.setattr(export_coordinator, "evaluate_export_gate", lambda _request: object())
    monkeypatch.setattr(
        export_coordinator,
        "export_serato_playlist",
        lambda **_kwargs: SimpleNamespace(
            plan=object(),
            library=SimpleNamespace(volume_root=tmp_path),
            write_result=SimpleNamespace(written_path=written, backup_path=backup),
        ),
    )
    monkeypatch.setattr(
        export_coordinator,
        "write_readiness_sidecars",
        lambda *_args, **_kwargs: (tmp_path / "ready.json", tmp_path / "ready.csv"),
    )
    monkeypatch.setattr(
        "xfinaudio.desktop.serato_recommendation_export.populate_serato_export_history_table",
        lambda *_args, **_kwargs: None,
    )
    Boundary().export_recommendation_to_serato(crate_name="Set")
    assert str(backup) in guidance.text
    assert "ready.json" in guidance.text and "ready.csv" in guidance.text
    assert host.serato_export_history[0]["path"] == str(written)
    assert host.serato_export_history[0]["readiness_json_path"] == str(tmp_path / "ready.json")
    assert host.serato_export_history[0]["readiness_csv_path"] == str(tmp_path / "ready.csv")
    assert sync_calls == ["sync"]
    assert history_visibility == [True]
    assert callbacks == ["success"]


def test_metadata_status_write_updates_visible_status_and_forwards_records(monkeypatch, tmp_path) -> None:
    label = SimpleNamespace(text="", setText=lambda value: setattr(label, "text", value))
    guidance = SimpleNamespace(text="", setText=lambda value: setattr(guidance, "text", value))
    records = [object()]
    host = SimpleNamespace(
        _selected_missing_metadata_filter=lambda: None,
        _selected_metadata_status_filter=lambda: "complete",
        _metadata_status_records=lambda status: records if status == "complete" else [],
        status_label=label,
        _export_screen=SimpleNamespace(export_guidance_label=guidance),
        tr=lambda text: text,
    )
    forwarded = []
    monkeypatch.setattr(
        "xfinaudio.desktop.serato_metadata_worklist_export.export_metadata_status_serato_worklist",
        lambda **kwargs: (
            forwarded.append(kwargs)
            or SimpleNamespace(write_result=SimpleNamespace(written_path=tmp_path / "Complete.crate"))
        ),
    )

    class Boundary(SeratoMetadataWorklistExportMixin):
        _host = host

    Boundary().export_metadata_status_to_serato()
    assert forwarded[0]["records"] is records
    assert forwarded[0]["status"] == "complete"
    assert "Exported complete metadata crate" in label.text
    assert "Metadata worklist exported" in guidance.text
