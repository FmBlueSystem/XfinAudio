"""Tests for the legacy MainWindow shell compatibility boundary."""

from __future__ import annotations

from xfinaudio.desktop import layout, shell_compat
from xfinaudio.desktop.main_window import MainWindow


def test_layout_no_longer_owns_legacy_method_installation() -> None:
    assert not hasattr(layout, "install_layout_methods")


def test_shell_compat_names_legacy_layout_methods() -> None:
    assert "choose_folder" in shell_compat.LEGACY_LAYOUT_METHODS
    assert "_apply_song_filter" in shell_compat.LEGACY_LAYOUT_METHODS
    assert "_refresh_idle_action_state" in shell_compat.LEGACY_LAYOUT_METHODS


def test_main_window_keeps_legacy_layout_methods_available() -> None:
    assert callable(MainWindow.choose_folder)
    assert callable(MainWindow._apply_song_filter)
    assert callable(MainWindow._refresh_idle_action_state)


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
