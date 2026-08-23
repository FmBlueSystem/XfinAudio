from __future__ import annotations

import hashlib
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
    service = object()
    monkeypatch.setattr(window_factory, "create_loudness_completion_service", lambda: service)
    app = QApplication.instance() or QApplication([])
    repository = Mock()
    repository.db_path = None
    window = MainWindow(scan_service=Mock(), repository=repository)

    assert window._library_controller._loudness_completion_service is service
    assert app is QApplication.instance()
