from __future__ import annotations

import hashlib
import logging
import subprocess
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtWidgets import QApplication

from xfinaudio.audio.loudness import FfmpegCapabilityError
from xfinaudio.audio.loudness_runtime import (
    create_loudness_completion_service,
    probe_engine_fingerprint,
    resolve_ffmpeg,
)
from xfinaudio.audio.loudness_tags import write_loudness_tags
from xfinaudio.desktop import window_factory
from xfinaudio.desktop.main_window import MainWindow


def test_frozen_resolution_uses_only_the_bundle_relative_binary(tmp_path: Path) -> None:
    assert (
        resolve_ffmpeg(frozen=True, bundle_dir=tmp_path, which=lambda _: (_ for _ in ()).throw(AssertionError()))
        == (tmp_path / "ffmpeg").resolve()
    )


def test_version_probe_is_shell_free_and_fingerprints_exact_output(monkeypatch, tmp_path: Path) -> None:
    output = "ffmpeg version test\nconfiguration: exact\n"
    run = Mock(return_value=subprocess.CompletedProcess([], 0, output, ""))
    monkeypatch.setattr("xfinaudio.audio.loudness_runtime.subprocess.run", run)

    assert (
        probe_engine_fingerprint(tmp_path / "ffmpeg") == f"ffmpeg-sha256:{hashlib.sha256(output.encode()).hexdigest()}"
    )
    assert run.call_args.args[0] == (str(tmp_path / "ffmpeg"), "-version")
    assert run.call_args.kwargs["shell"] is False


def test_runtime_factory_preflights_and_returns_none_when_unavailable_or_unsupported(tmp_path: Path) -> None:
    adapter = Mock()
    service = create_loudness_completion_service(
        frozen=False,
        which=lambda _: str(tmp_path / "ffmpeg"),
        version_probe=lambda _: "ffmpeg-test",
        adapter_factory=lambda *_: adapter,
    )

    assert service is not None
    assert service._engine_fingerprint == "ffmpeg-test"
    assert service._tag_writer is write_loudness_tags
    adapter.preflight.assert_called_once_with()
    adapter.preflight.side_effect = FfmpegCapabilityError("missing peak")
    assert (
        create_loudness_completion_service(
            frozen=False,
            which=lambda _: str(tmp_path / "ffmpeg"),
            version_probe=lambda _: "ffmpeg-test",
            adapter_factory=lambda *_: adapter,
        )
        is None
    )
    assert create_loudness_completion_service(frozen=False, which=lambda _: None) is None


def test_window_factory_injects_available_loudness_service(monkeypatch) -> None:
    service = Mock()
    monkeypatch.setattr(window_factory, "create_loudness_completion_service", lambda: service)
    app = QApplication.instance() or QApplication([])
    repository = Mock()
    repository.db_path = None
    window = MainWindow(scan_service=Mock(), repository=repository)

    assert window._library_controller._loudness_completion_service is service
    assert app is QApplication.instance()


def test_window_factory_wires_one_watcher_to_scan_and_loudness_and_stops_it(monkeypatch) -> None:
    service = Mock()
    monkeypatch.setattr(window_factory, "create_loudness_completion_service", lambda: service)
    app = QApplication.instance() or QApplication([])
    repository = Mock()
    repository.db_path = None
    window = MainWindow(scan_service=Mock(), repository=repository)
    watcher = window._library_watch_service
    watcher.stop = Mock()

    assert window._scan_service._watch_service is watcher
    service.set_path_suppressor.assert_called_once_with(watcher)

    window.close()

    watcher.stop.assert_called_once_with()
    assert app is QApplication.instance()


def test_every_runtime_skip_reason_is_logged_distinguishably(caplog, tmp_path: Path) -> None:
    """A stage that disappears must say why; the three abort paths must not look alike."""
    adapter = Mock()
    adapter.preflight.side_effect = FfmpegCapabilityError("missing peak")

    with caplog.at_level(logging.WARNING, logger="xfinaudio.audio.loudness_runtime"):
        assert create_loudness_completion_service(frozen=False, which=lambda _: None) is None
        assert (
            create_loudness_completion_service(
                frozen=False, which=lambda _: str(tmp_path / "ffmpeg"), version_probe=lambda _: None
            )
            is None
        )
        assert (
            create_loudness_completion_service(
                frozen=False,
                which=lambda _: str(tmp_path / "ffmpeg"),
                version_probe=lambda _: "ffmpeg-test",
                adapter_factory=lambda *_: adapter,
            )
            is None
        )

    messages = [record.getMessage() for record in caplog.records]
    assert len(messages) == 3
    assert len(set(messages)) == 3
    assert all("loudness" in message.lower() for message in messages)
    assert any("missing peak" in message for message in messages)


def test_controller_logs_when_a_scan_skips_the_loudness_stage(monkeypatch, caplog) -> None:
    """The per-scan skip is the moment the user loses the stage, so it is logged there."""
    monkeypatch.setattr(window_factory, "create_loudness_completion_service", lambda: None)
    app = QApplication.instance() or QApplication([])
    repository = Mock()
    repository.db_path = None
    window = MainWindow(scan_service=Mock(), repository=repository)
    controller = window._library_controller

    with caplog.at_level(logging.WARNING):
        controller.start_loudness_completion([])

    assert [message for message in caplog.messages if "loudness" in message.lower()] != []
    assert app is QApplication.instance()
