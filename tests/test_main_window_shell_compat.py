"""Tests for the legacy MainWindow shell compatibility boundary."""

from __future__ import annotations

import inspect

from xfinaudio.desktop import layout, shell_compat, shell_layout_compat, shell_state_compat
from xfinaudio.desktop import main_window as main_window_module
from xfinaudio.desktop.main_window import MainWindow


def test_layout_no_longer_owns_legacy_method_installation() -> None:
    assert not hasattr(layout, "install_layout_methods")


def test_shell_compat_names_legacy_layout_methods() -> None:
    assert "_apply_song_filter" in shell_compat.LEGACY_LAYOUT_METHODS


def test_main_window_keeps_legacy_layout_methods_available() -> None:
    assert callable(MainWindow.choose_folder)
    assert callable(MainWindow._apply_song_filter)
    assert callable(MainWindow._refresh_idle_action_state)


def test_library_shell_methods_are_explicit_main_window_methods() -> None:
    assert "choose_folder" not in shell_layout_compat.LEGACY_LAYOUT_METHODS
    assert "_refresh_idle_action_state" not in shell_layout_compat.LEGACY_LAYOUT_METHODS

    assert MainWindow.__dict__["choose_folder"] is not shell_layout_compat.LEGACY_LAYOUT_METHODS.get("choose_folder")
    assert MainWindow.__dict__["_refresh_idle_action_state"] is not shell_layout_compat.LEGACY_LAYOUT_METHODS.get(
        "_refresh_idle_action_state"
    )
    assert callable(MainWindow.choose_folder)
    assert callable(MainWindow._refresh_idle_action_state)


def test_export_shell_methods_are_explicit_main_window_methods() -> None:
    explicit_export_methods = (
        "choose_safe_export_folder",
        "set_safe_export_folder",
        "_format_safe_export_folder_label",
        "export_dj_readiness_report",
        "preview_export",
        "export_recommendation",
        "preview_serato_export",
        "export_recommendation_to_serato",
        "export_metadata_status_to_serato",
    )

    for method_name in explicit_export_methods:
        assert method_name not in shell_layout_compat.LEGACY_LAYOUT_METHODS
        assert method_name in MainWindow.__dict__
        assert callable(getattr(MainWindow, method_name))


def test_settings_shell_methods_are_explicit_main_window_methods() -> None:
    explicit_settings_methods = (
        "_open_settings_dialog",
        "_on_spectral_cohesion_changed",
    )

    for method_name in explicit_settings_methods:
        assert method_name not in shell_layout_compat.LEGACY_LAYOUT_METHODS
        assert method_name in MainWindow.__dict__
        assert callable(getattr(MainWindow, method_name))


def test_scan_entry_shell_methods_are_explicit_main_window_methods() -> None:
    explicit_scan_methods = (
        "scan_selected_folder",
        "_begin_scan_state",
        "cancel_scan",
        "_clear_scan_dependent_state",
    )

    for method_name in explicit_scan_methods:
        assert method_name not in shell_layout_compat.LEGACY_LAYOUT_METHODS
        assert method_name in MainWindow.__dict__
        assert callable(getattr(MainWindow, method_name))


def test_main_window_uses_explicit_shell_compatibility_surfaces() -> None:
    source = inspect.getsource(main_window_module)

    assert "shell_compat" not in source
    assert "shell_layout_compat" in source
    assert "shell_state_compat" in source


def test_shell_compat_exposes_legacy_state_write_boundary() -> None:
    assert "workflow_service" in shell_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES
    assert "current_scan_cancellation_token" in shell_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES
    assert "_records_by_path" in shell_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES
    assert callable(shell_compat.try_set_legacy_app_state_attribute)


def test_shell_compat_handles_legacy_state_write_and_service_mirrors() -> None:
    class State:
        workflow_service: object | None = None
        current_scan_cancellation_token: object | None = None
        records_by_path: object | None = None
        applied_variant_name: object | None = None

    class Service:
        workflow_service: object | None = None
        current_scan_cancellation_token: object | None = None

    class Target:
        pass

    target = Target()
    target._state = State()
    target._scan_service = Service()
    target._recommendation_service = Service()

    workflow_service = object()
    assert shell_compat.try_set_legacy_app_state_attribute(target, "workflow_service", workflow_service)

    assert target._state.workflow_service is workflow_service
    assert target._scan_service.workflow_service is workflow_service
    assert target._recommendation_service.workflow_service is workflow_service

    token = object()
    assert shell_compat.try_set_legacy_app_state_attribute(target, "current_scan_cancellation_token", token)

    assert target._state.current_scan_cancellation_token is token
    assert target._scan_service.current_scan_cancellation_token is token

    records_by_path = {"track.mp3": object()}
    assert shell_compat.try_set_legacy_app_state_attribute(target, "_records_by_path", records_by_path)
    assert target._state.records_by_path is records_by_path

    assert not shell_compat.try_set_legacy_app_state_attribute(target, "plain_attribute", object())


def test_shell_compat_exposes_legacy_state_read_boundary() -> None:
    assert callable(shell_compat.try_get_legacy_app_state_attribute)


def test_shell_compat_handles_legacy_state_read_aliases_and_scan_token_sync() -> None:
    class State:
        records_by_path: object | None = None
        applied_variant_name: object | None = None
        current_scan_cancellation_token: object | None = None
        workflow_service: object | None = None

    class ScanService:
        current_scan_cancellation_token: object | None = None

    class Target:
        pass

    records_by_path = {"track.mp3": object()}
    variant_name = "Warmup"
    token = object()

    target = Target()
    target._state = State()
    target._state.records_by_path = records_by_path
    target._state.applied_variant_name = variant_name
    target._scan_service = ScanService()
    target._scan_service.current_scan_cancellation_token = token

    assert shell_compat.try_get_legacy_app_state_attribute(target, "_records_by_path") is records_by_path
    assert shell_compat.try_get_legacy_app_state_attribute(target, "applied_prep_copilot_variant_name") == variant_name
    assert shell_compat.try_get_legacy_app_state_attribute(target, "current_scan_cancellation_token") is token
    assert target._state.current_scan_cancellation_token is token


def test_shell_compat_handles_delegated_reads_and_missing_private_attributes() -> None:
    class Toolbar:
        undo = object()
        redo = object()

    class LibraryController:
        on_track_remove_requested = object()

    class Target:
        pass

    target = Target()
    target._undo_toolbar = Toolbar()
    target._library_controller = LibraryController()

    assert shell_compat.try_get_legacy_app_state_attribute(target, "undo") is target._undo_toolbar.undo
    assert shell_compat.try_get_legacy_app_state_attribute(target, "redo") is target._undo_toolbar.redo
    assert (
        shell_compat.try_get_legacy_app_state_attribute(target, "_on_track_remove_requested")
        is target._library_controller.on_track_remove_requested
    )
    assert shell_compat.is_missing_legacy_attribute(
        shell_compat.try_get_legacy_app_state_attribute(target, "plain_attribute")
    )

    try:
        shell_compat.try_get_legacy_app_state_attribute(target, "_missing_private")
    except AttributeError as exc:
        assert exc.args == ("_missing_private",)
    else:
        raise AssertionError("Expected AttributeError for missing private attribute")


def test_shell_compat_surfaces_are_split_by_responsibility() -> None:
    assert shell_compat.LEGACY_LAYOUT_METHODS is shell_layout_compat.LEGACY_LAYOUT_METHODS
    assert shell_compat.install_legacy_layout_methods is shell_layout_compat.install_legacy_layout_methods
    assert shell_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES is shell_state_compat.LEGACY_APP_STATE_WRITE_ATTRIBUTES
    assert shell_compat.try_set_legacy_app_state_attribute is shell_state_compat.try_set_legacy_app_state_attribute
    assert shell_compat.try_get_legacy_app_state_attribute is shell_state_compat.try_get_legacy_app_state_attribute
    assert shell_compat.is_missing_legacy_attribute is shell_state_compat.is_missing_legacy_attribute
