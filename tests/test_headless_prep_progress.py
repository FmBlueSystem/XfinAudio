"""Named Spanish stages for the core's prep.generate progress (0–3 of 3)."""

from __future__ import annotations

import io
import time
from pathlib import Path
from uuid import uuid4

from tests.test_headless_prep_parity import seeded
from tests.test_headless_protocol import messages, request
from xfinaudio.headless.prep import PREP_GENERATE_FINAL_STAGE, PREP_GENERATE_STAGES, prep_generate_stage
from xfinaudio.headless.server import JsonlServer


def test_generate_stage_names_cover_the_three_variants_and_the_final_step() -> None:
    assert PREP_GENERATE_STAGES == (
        "Preparando alternativa segura",
        "Preparando alternativa equilibrada",
        "Preparando alternativa aventurera",
    )
    assert [prep_generate_stage(index) for index in range(3)] == list(PREP_GENERATE_STAGES)
    assert prep_generate_stage(3) == PREP_GENERATE_FINAL_STAGE
    for invalid in (-1, 4, 99, 1.5, "1", None, True):
        assert prep_generate_stage(invalid) is None  # type: ignore[arg-type]


def _wait_for(output: io.StringIO, request_id: str, *, seconds: float = 60.0) -> None:
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if any(message.get("id") == request_id for message in messages(output)):
            return
        time.sleep(0.01)
    raise AssertionError("prep.generate did not finish before the deadline")


def test_prep_generate_progress_carries_the_spanish_stage_names(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    output = io.StringIO()
    server = JsonlServer(backend, output)
    request_id = str(uuid4())
    assert server.process_line(request("prep.generate", {"targetTrackCount": 4}, request_id)) is True
    _wait_for(output, request_id)
    server.close()

    progress = [message["data"] for message in messages(output) if message.get("event") == "progress"]
    assert [item["processedCount"] for item in progress] == [0, 1, 2, 3]
    assert [item["totalCount"] for item in progress] == [3, 3, 3, 3]
    assert [item["stage"] for item in progress] == [*PREP_GENERATE_STAGES, PREP_GENERATE_FINAL_STAGE]
    finished = [message for message in messages(output) if message.get("id") == request_id]
    assert len(finished) == 1 and finished[0]["ok"] is True


def test_progress_for_other_operations_is_untouched_by_the_stage_names(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    seen: list[dict] = []
    backend.execute("library.list", {}, progress=seen.append)
    assert seen == []
