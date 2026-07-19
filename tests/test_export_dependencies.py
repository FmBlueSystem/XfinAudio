"""Tests for the ``ExportDependencies`` bundle — field surface and static typing."""

from __future__ import annotations

import dataclasses

from xfinaudio.desktop.export_dependencies import ExportDependencies, default_export_dependencies


def test_export_dependencies_has_no_unused_readiness_report_field() -> None:
    field_names = {field.name for field in dataclasses.fields(ExportDependencies)}

    assert "write_application_dj_readiness_report" not in field_names


def test_default_export_dependencies_still_builds_without_the_removed_field() -> None:
    dependencies = default_export_dependencies()

    field_names = {field.name for field in dataclasses.fields(dependencies)}
    assert "write_application_dj_readiness_report" not in field_names


def test_export_dependencies_declares_no_callable_any_fields() -> None:
    fields = dataclasses.fields(ExportDependencies)

    assert fields, "expected ExportDependencies to expose fields"
    for field in fields:
        assert field.type != "Callable[..., Any]", f"field {field.name!r} must not be typed Callable[..., Any]"
