"""The headless core must leave a size-bounded log file inside its data dir.

S5 (audit point 3, Python side): a core that dies, hangs or mis-analyses used to leave
nothing behind, because its only diagnostics went to a stderr stream nobody kept. The
core therefore also writes a rotating log file under the isolated ``--data-dir`` it
receives, while stdout stays reserved for JSONL protocol frames. A logging failure
must never stop the core: without a usable log file the stderr stream still runs.
"""

from __future__ import annotations

import json
import logging
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import TextIO

import pytest

from xfinaudio.headless import __main__ as core_entry
from xfinaudio.headless import logging_setup

CORE_LOGGER = "xfinaudio.headless.server"


class _LoggingServer:
    """Server stand-in that writes one protocol frame and one log record."""

    def __init__(self, backend: object, output: TextIO) -> None:
        self.backend = backend
        self.output = output

    def run(self, source: object) -> None:
        logging.getLogger(CORE_LOGGER).warning("core started for test")
        self.output.write(json.dumps({"id": "startup", "ok": True}) + "\n")
        self.output.flush()

    def close(self) -> None:
        pass


class _CollectingHandler(logging.Handler):
    """Record collector independent of pytest's own logging plumbing."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@pytest.fixture
def isolated_root_logger() -> Iterator[logging.Logger]:
    """Give the test a bare root logger and restore the process one afterwards."""
    root = logging.getLogger()
    saved_handlers = list(root.handlers)
    saved_level = root.level
    root.handlers.clear()
    try:
        yield root
    finally:
        for handler in list(root.handlers):
            if handler not in saved_handlers:
                root.removeHandler(handler)
                handler.close()
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def _log_file(data_dir: Path) -> Path:
    return data_dir / logging_setup.LOG_FILE_NAME


def test_entry_point_keeps_jsonl_on_stdout_and_writes_a_rotating_log_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    isolated_root_logger: logging.Logger,
) -> None:
    data_dir = tmp_path / "data"
    monkeypatch.setattr(sys, "argv", ["xfinaudio-headless", "--data-dir", str(data_dir)])
    monkeypatch.setattr(core_entry, "JsonlServer", _LoggingServer)

    core_entry.main()

    written = capsys.readouterr()
    assert json.loads(written.out) == {"id": "startup", "ok": True}
    assert "core started for test" not in written.out
    log_file = _log_file(data_dir)
    assert log_file.is_file()
    assert "core started for test" in log_file.read_text(encoding="utf-8")


def test_log_records_reach_stderr_and_the_file_but_never_stdout(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    isolated_root_logger: logging.Logger,
) -> None:
    assert logging_setup.configure_logging(tmp_path) is True

    logging.getLogger("xfinaudio.test").warning("diagnostic %s", "record")

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "diagnostic record" in captured.err
    assert "diagnostic record" in _log_file(tmp_path).read_text(encoding="utf-8")


def test_rotation_keeps_every_log_file_under_the_size_limit(
    tmp_path: Path, isolated_root_logger: logging.Logger
) -> None:
    max_bytes = 1024
    backup_count = 2
    assert logging_setup.configure_logging(tmp_path, max_bytes=max_bytes, backup_count=backup_count) is True

    logger = logging.getLogger("xfinaudio.rotation")
    for index in range(200):
        logger.warning("record %03d %s", index, "x" * 60)

    files = [path for path in tmp_path.iterdir() if path.is_file()]
    assert len(files) >= 2
    assert len(files) <= backup_count + 1
    assert all(path.stat().st_size <= max_bytes for path in files), [(path.name, path.stat().st_size) for path in files]


def test_unusable_log_file_keeps_stderr_logging_and_lets_the_core_start(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    isolated_root_logger: logging.Logger,
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    # A directory in place of the log file makes every open attempt fail.
    _log_file(data_dir).mkdir()
    monkeypatch.setattr(sys, "argv", ["xfinaudio-headless", "--data-dir", str(data_dir)])
    monkeypatch.setattr(core_entry, "JsonlServer", _LoggingServer)

    core_entry.main()

    written = capsys.readouterr()
    assert json.loads(written.out) == {"id": "startup", "ok": True}
    assert "core started for test" in written.err
    assert logging_setup.LOG_FILE_NAME in written.err


def test_failed_log_file_is_reported_on_the_kept_stderr_stream(
    tmp_path: Path, isolated_root_logger: logging.Logger
) -> None:
    (tmp_path / logging_setup.LOG_FILE_NAME).mkdir()
    collector = _CollectingHandler()
    isolated_root_logger.addHandler(collector)

    assert logging_setup.configure_logging(tmp_path) is False

    assert any(logging_setup.LOG_FILE_NAME in message for message in collector.messages), collector.messages


def test_configuring_logging_twice_keeps_one_handler_and_one_logged_line(
    tmp_path: Path, isolated_root_logger: logging.Logger
) -> None:
    assert logging_setup.configure_logging(tmp_path) is True
    assert logging_setup.configure_logging(tmp_path) is True

    file_handlers = [
        handler
        for handler in isolated_root_logger.handlers
        if isinstance(handler, RotatingFileHandler) and Path(handler.baseFilename) == _log_file(tmp_path)
    ]
    assert len(file_handlers) == 1

    logging.getLogger("xfinaudio.once").warning("written once")
    assert _log_file(tmp_path).read_text(encoding="utf-8").count("written once") == 1


def _log_worker_failure(index: int) -> None:
    logging.getLogger("xfinaudio.audio.spectral_profile").warning("worker analysis failure %d", index)


def test_records_logged_by_analysis_worker_threads_reach_the_log_file(
    tmp_path: Path, isolated_root_logger: logging.Logger
) -> None:
    """Profile and loudness completion run on thread pools inside this process."""
    assert logging_setup.configure_logging(tmp_path) is True

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="xfinaudio-profile") as pool:
        list(pool.map(_log_worker_failure, range(3)))

    assert _log_file(tmp_path).read_text(encoding="utf-8").count("worker analysis failure") == 3


def test_refused_data_directory_is_left_untouched_by_logging(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    isolated_root_logger: logging.Logger,
) -> None:
    # The backend refuses an unsafe data directory before using it; logging must
    # not have written into that directory first.
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "sentinel.bin").write_bytes(b"keep")

    def refuse(_data_dir: Path) -> None:
        raise RuntimeError("data directory refused")

    monkeypatch.setattr(sys, "argv", ["xfinaudio-headless", "--data-dir", str(data_dir)])
    monkeypatch.setattr(core_entry, "HeadlessBackend", refuse)

    with pytest.raises(RuntimeError, match="data directory refused"):
        core_entry.main()

    assert sorted(entry.name for entry in data_dir.iterdir()) == ["sentinel.bin"]
