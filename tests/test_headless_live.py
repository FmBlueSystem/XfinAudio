"""Ready-only local guidance uses synthetic files and the existing scoring engine."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import replace
from uuid import uuid4

import pytest

from tests.test_headless_backend import tagged_flac
from xfinaudio.headless.backend import BackendError, HeadlessBackend


@pytest.fixture
def ready_live(tmp_path):
    music = tmp_path / "music"
    for index in range(4):
        tagged_flac(music / f"{index}.flac", index)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})
    review = backend.execute("prep.generate", {"targetTrackCount": 4})
    assert review["readiness"] == "ready"
    return backend, review, music


def test_live_core_import_does_not_enter_qt_desktop_or_provider_packages():
    code = """
import importlib.abc,sys
class Block(importlib.abc.MetaPathFinder):
 def find_spec(self,fullname,path=None,target=None):
  if fullname.startswith(('PySide6','xfinaudio.desktop','openai','anthropic')): raise RuntimeError(fullname)
sys.meta_path.insert(0,Block())
from xfinaudio.application.live_assistance import live_session_ready,rank_live_candidates
assert live_session_ready(None,None) is False
print('Qt-free')
"""
    result = subprocess.run(
        [sys.executable, "-c", code], env={**os.environ, "PYTHONPATH": "src"}, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "Qt-free"


def test_legacy_live_import_preserves_function_and_candidate_identity():
    pytest.importorskip("PySide6")
    from xfinaudio.application import live_assistance as neutral
    from xfinaudio.desktop import live_assistance as legacy

    assert neutral.LiveCandidate is legacy.LiveCandidate
    assert neutral.live_session_ready is legacy.live_session_ready
    assert neutral.rank_live_candidates is legacy.rank_live_candidates


def test_live_starts_from_exact_ready_review_and_returns_actual_ranked_scores(ready_live):
    from xfinaudio.application.live_assistance import rank_live_candidates

    backend, review, music = ready_live
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in music.iterdir()}
    state = backend.execute("live.open", {"reviewId": review["reviewId"]})
    assert state["current"] == review["tracks"][0]
    assert state["history"] == [] and state["revision"] == 0 and state["state"] == "active"
    assert state["sourceReviewId"] == review["reviewId"]
    assert backend.review is not None
    recommendation = backend.review.recommendation
    ranked = rank_live_candidates(
        recommendation,
        (recommendation.ordered_tracks[0].path,),
        spectral_cohesion=backend.preferences.spectral_cohesion(),
    )
    assert [item["track"]["id"] for item in state["candidates"]] == [
        hashlib.sha256(c.track.path.encode()).hexdigest() for c in ranked[:5]
    ]
    assert [item["score"] for item in state["candidates"]] == [c.score.total_score for c in ranked[:5]]
    assert str(music) not in json.dumps(state)
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in music.iterdir()}


def test_manual_next_rotates_revision_preserves_history_and_finishes_exact_pool(ready_live):
    backend, review, _ = ready_live
    state = backend.execute("live.open", {"reviewId": review["reviewId"]})
    seen = [state["current"]["id"]]
    while state["candidates"]:
        previous = state
        state = backend.execute(
            "live.next",
            {
                "sessionId": state["sessionId"],
                "revision": state["revision"],
                "trackId": state["candidates"][0]["track"]["id"],
            },
        )
        assert state["revision"] == previous["revision"] + 1
        assert state["history"][-1]["track"] == previous["current"]
        assert state["history"][-1]["startedAt"].endswith("+00:00")
        seen.append(state["current"]["id"])
    assert state["state"] == "complete"
    assert len(seen) == len(set(seen)) == len(review["tracks"])
    assert set(seen) == {track["id"] for track in review["tracks"]}


def test_open_same_review_resumes_and_explicit_clear_resets(ready_live):
    backend, review, _ = ready_live
    state = backend.execute("live.open", {"reviewId": review["reviewId"]})
    state = backend.execute(
        "live.next", {"sessionId": state["sessionId"], "revision": 0, "trackId": state["candidates"][0]["track"]["id"]}
    )
    resumed = backend.execute("live.open", {"reviewId": review["reviewId"]})
    assert resumed["sessionId"] == state["sessionId"] and resumed["revision"] == 1
    assert resumed["history"] == state["history"]
    assert backend.execute("live.clear", {"sessionId": state["sessionId"]}) == {"cleared": True}
    with pytest.raises(BackendError):
        backend.execute("live.status", {"sessionId": state["sessionId"]})
    assert backend.execute("live.open", {"reviewId": review["reviewId"]})["sessionId"] != state["sessionId"]


@pytest.mark.parametrize("change", ["missing", "scan", "generate", "metadata", "blocked"])
def test_context_changes_invalidate_live_before_any_next_action(ready_live, change):
    backend, review, music = ready_live
    state = backend.execute("live.open", {"reviewId": review["reviewId"]})
    if change == "missing":
        next(music.iterdir()).unlink()
    elif change == "scan":
        backend.execute("library.scan", {"root": str(music)})
    elif change == "generate":
        backend.execute("prep.generate", {"targetTrackCount": 2})
    elif change == "metadata":
        path = next(music.iterdir())
        path.write_bytes(path.read_bytes() + b"changed fixture")
    else:
        backend.review_blocked = True
    with pytest.raises(BackendError) as failure:
        backend.execute(
            "live.next",
            {"sessionId": state["sessionId"], "revision": 0, "trackId": state["candidates"][0]["track"]["id"]},
        )
    assert failure.value.code == "stale_live"
    with pytest.raises(BackendError):
        backend.execute("live.status", {"sessionId": state["sessionId"]})


def test_duplicate_revision_and_forged_candidate_do_not_advance(ready_live):
    backend, review, _ = ready_live
    state = backend.execute("live.open", {"reviewId": review["reviewId"]})
    request = {"sessionId": state["sessionId"], "revision": 0, "trackId": state["candidates"][0]["track"]["id"]}
    advanced = backend.execute("live.next", request)
    for bad in [
        request,
        {**request, "revision": 1, "trackId": "f" * 64},
        {**request, "revision": 1, "trackId": advanced["current"]["id"]},
    ]:
        with pytest.raises(BackendError):
            backend.execute("live.next", bad)
    assert backend.execute("live.status", {"sessionId": state["sessionId"]})["revision"] == 1


def test_live_rejects_absent_wrong_needs_review_or_blocked_input(ready_live):
    backend, review, _ = ready_live
    for value in [str(uuid4()), "../path", "", None]:
        with pytest.raises(BackendError):
            backend.execute("live.open", {"reviewId": value})
    assert backend.review is not None
    for status in ["needs_review", "blocked"]:
        backend.review = replace(
            backend.review, readiness_report=backend.review.readiness_report.model_copy(update={"status": status})
        )
        with pytest.raises(BackendError) as failure:
            backend.execute("live.open", {"reviewId": review["reviewId"]})
        assert failure.value.code == "live_not_ready"


@pytest.mark.parametrize("params", [{}, {"reviewId": "x", "path": "/tmp"}, {"reviewId": None}, {"reviewId": 5}])
def test_live_open_schema_is_bounded_and_path_free(ready_live, params):
    with pytest.raises(BackendError):
        ready_live[0].execute("live.open", params)


def test_live_preserves_real_arc_order_and_does_not_offer_the_end_early(ready_live):
    backend, review, _ = ready_live
    end = review["tracks"][-1]["id"]
    arc = backend.execute("prep.generate", {"targetTrackCount": 4, "strategy": "warmup", "endTrackId": end})
    assert arc["readiness"] == "ready"
    state = backend.execute("live.open", {"reviewId": arc["reviewId"]})
    assert [item["track"]["id"] for item in state["candidates"]] == [arc["tracks"][1]["id"]]
    assert state["candidates"][0]["track"]["id"] != end
    with pytest.raises(BackendError):
        backend.execute("live.next", {"sessionId": state["sessionId"], "revision": 0, "trackId": end})


def test_live_elapsed_uses_monotonic_current_track_time_and_resets_only_on_advance(ready_live):
    backend, review, _ = ready_live
    clock = [20.0]
    backend.live._clock = lambda: clock[0]
    state = backend.execute("live.open", {"reviewId": review["reviewId"]})
    assert state["elapsedSeconds"] == 0
    clock[0] = 27.5
    state = backend.execute("live.status", {"sessionId": state["sessionId"]})
    assert state["elapsedSeconds"] == 7.5
    resumed = backend.execute("live.open", {"reviewId": review["reviewId"]})
    assert resumed["elapsedSeconds"] == 7.5
    advanced = backend.execute(
        "live.next", {"sessionId": state["sessionId"], "revision": 0, "trackId": state["candidates"][0]["track"]["id"]}
    )
    assert advanced["elapsedSeconds"] == 0


@pytest.mark.parametrize(
    "patch",
    [
        {"revision": True},
        {"revision": -1},
        {"revision": 501},
        {"revision": 0.5},
        {"trackId": "../file"},
        {"trackId": None},
        {"path": "/tmp/file"},
    ],
)
def test_live_next_rejects_bad_bounds_and_paths_without_advancing(ready_live, patch):
    backend, review, _ = ready_live
    state = backend.execute("live.open", {"reviewId": review["reviewId"]})
    params = {"sessionId": state["sessionId"], "revision": 0, "trackId": state["candidates"][0]["track"]["id"], **patch}
    with pytest.raises(BackendError):
        backend.execute("live.next", params)
    assert backend.execute("live.status", {"sessionId": state["sessionId"]})["revision"] == 0
