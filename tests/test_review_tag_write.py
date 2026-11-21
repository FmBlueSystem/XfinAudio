"""A tag write keeps the same recording, so the list survives it (S20).

The fixtures are real FLAC files: rewriting a tag changes the file size and the
modification time while the audio stream, its duration and the path stay put. A
recording with a different duration, an unreadable file, a deleted file and a
moved file still refuse every edit and drop the stored list, exactly as before.
"""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from tests.test_headless_ai_context import FIXTURES
from tests.test_headless_ai_context import setup as setup  # noqa: F401
from tests.test_headless_backend import tagged_flac
from tests.test_headless_chat_actions import answer, replace_at
from tests.test_headless_list_chat import call, prepare, turn
from tests.test_headless_list_chat import chat_setup as _chat_setup
from tests.test_headless_prep_parity import identity
from tests.test_review_recovery import stored_backend
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.serato_safety import source_identity

chat_setup = _chat_setup

ACCEPTED = "A tag rewrite kept the same recording; the review source identity was refreshed"
COMMENT = "played by a DJ program " + "x" * 2000
REFUSALS = ("different_length", "unreadable", "deleted", "moved")


def _profile() -> SpectralProfile:
    return SpectralProfile(
        red_ratio=0.5,
        green_ratio=0.3,
        blue_ratio=0.2,
        centroid_hz=1000,
        rolloff_hz=2000,
        dominant_color="BLUE",
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )


def _analyzed(backend) -> None:
    """Bind a profile to every file, as a real library with completed analysis does."""
    profile = _profile()
    for record in backend.repository.list_tracks():
        backend.repository.update_spectral_profile(record.path, profile)


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "music"
    shutil.copytree(FIXTURES, root)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    _analyzed(backend)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Tag write review"})
    return backend, root, result


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def state(backend) -> tuple[object, ...]:
    """Everything a refused command must leave exactly as it found it."""
    return (
        backend.review,
        backend.review_id,
        list(backend.review_actions.history),
        list(backend.review_actions.future),
        dict(backend.review_actions.offers),
    )


def rewrite_tags(path: Path) -> None:
    """A DJ program's tag write: size and mtime change, the recording does not."""
    before = (path.stat().st_size, path.stat().st_mtime_ns)
    duration = FLAC(path).info.length
    audio = FLAC(path)
    audio["comment"] = COMMENT
    audio.save()
    after = (path.stat().st_size, path.stat().st_mtime_ns)
    assert before[0] != after[0] and before[1] != after[1]
    assert FLAC(path).info.length == duration


def _mutate(path: Path, case: str) -> None:
    if case == "different_length":
        tagged_flac(path)
    elif case == "unreadable":
        path.write_bytes(b"not audio after generation")
    elif case == "deleted":
        path.unlink()
    else:
        path.rename(path.with_name(path.name + ".moved"))


def _accepted(caplog: pytest.LogCaptureFixture) -> list[logging.LogRecord]:
    return [record for record in caplog.records if record.levelno == logging.INFO and record.message == ACCEPTED]


def test_a_tag_write_keeps_the_list_at_restart_and_refreshes_its_identity(library, caplog) -> None:
    backend, _, result = library
    target = Path(backend.review.recommendation.ordered_tracks[1].path)
    rewrite_tags(target)
    with caplog.at_level(logging.INFO):
        restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert (resumed["available"], resumed["dropped"]) == (True, False)
    assert resumed["review"]["reviewId"] == result["reviewId"]
    # The metadata the list shows is not changed by the acceptance.
    assert resumed["review"]["tracks"] == result["tracks"]
    assert restarted.review.recommendation.ordered_tracks[1].spectral_profile is not None
    assert len(_accepted(caplog)) == 1
    assert restarted.review_actions.sources[str(target)][1] == source_identity(target)


def test_compare_replace_remove_reorder_undo_and_redo_keep_working(library) -> None:
    backend, _, result = library
    target = Path(backend.review.recommendation.ordered_tracks[1].path)
    original = ids(result)
    rewrite_tags(target)
    # The same process: the first read of the rewritten file heals the recorded identity.
    assert ids(backend.execute("review.details", {"reviewId": result["reviewId"]})) == original
    comparison = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": original[2]})
    assert comparison["available"] is True

    # After a restart the restored list is still editable, step by step.
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})["review"]
    review_id = resumed["reviewId"]
    current = ids(resumed)
    comparison = restarted.execute("review.compare", {"reviewId": review_id, "trackId": current[2]})
    assert comparison["available"] is True
    replaced = restarted.execute(
        "review.replace",
        {"reviewId": review_id, "trackId": current[2], "replacementId": comparison["replacement"]["id"]},
    )
    assert len(ids(replaced)) == len(current) and ids(replaced)[2] != current[2]
    unprotected = next(track["id"] for track in replaced["tracks"] if track["id"] not in replaced["protectedTrackIds"])
    removed = restarted.execute("review.remove", {"reviewId": replaced["reviewId"], "trackId": unprotected})
    assert len(ids(removed)) >= 2
    order = ids(removed)[::-1]
    reordered = restarted.execute("review.reorder", {"reviewId": removed["reviewId"], "trackIds": order})
    assert ids(reordered) == order
    undone = restarted.execute("review.undo", {"reviewId": reordered["reviewId"]})
    assert ids(undone) == ids(removed)
    redone = restarted.execute("review.redo", {"reviewId": undone["reviewId"]})
    assert ids(redone) == order


def test_an_undo_state_survives_a_tag_write_on_a_track_out_of_the_list(library) -> None:
    backend, _, result = library
    dropped_id = ids(result)[1]
    dropped_path = Path(backend.review.recommendation.ordered_tracks[1].path)
    shortened = backend.execute("review.drop", {"reviewId": result["reviewId"], "trackId": dropped_id})
    assert dropped_id not in ids(shortened)
    rewrite_tags(dropped_path)
    undone = backend.execute("review.undo", {"reviewId": shortened["reviewId"]})
    assert ids(undone) == ids(result)
    redone = backend.execute("review.redo", {"reviewId": undone["reviewId"]})
    assert ids(redone) == ids(shortened)


def test_a_candidate_with_rewritten_tags_can_enter_the_list(library) -> None:
    backend, _, result = library
    listed = {track.path for track in backend.review.recommendation.ordered_tracks}
    candidate = next(
        record
        for record in backend.repository.list_tracks()
        if record.path not in listed and record.metadata_status == "complete"
    )
    rewrite_tags(Path(candidate.path))
    inserted = backend.execute(
        "review.insert",
        {"reviewId": result["reviewId"], "trackId": identity(candidate), "position": 2},
    )
    assert identity(candidate) in ids(inserted)


def test_an_untouched_library_keeps_the_same_edits_and_restart(library) -> None:
    """PRESERVE: no tag write means every command behaves exactly as before."""
    backend, _, result = library
    original = ids(result)
    comparison = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": original[2]})
    assert comparison["available"] is True
    replaced = backend.execute(
        "review.replace",
        {"reviewId": result["reviewId"], "trackId": original[2], "replacementId": comparison["replacement"]["id"]},
    )
    unprotected = next(track["id"] for track in replaced["tracks"] if track["id"] not in replaced["protectedTrackIds"])
    removed = backend.execute("review.remove", {"reviewId": replaced["reviewId"], "trackId": unprotected})
    order = ids(removed)[::-1]
    reordered = backend.execute("review.reorder", {"reviewId": removed["reviewId"], "trackIds": order})
    assert ids(reordered) == order
    undone = backend.execute("review.undo", {"reviewId": reordered["reviewId"]})
    assert ids(undone) == ids(removed)
    restarted = stored_backend(backend)
    resumed = restarted.execute("review.resume", {})
    assert (resumed["available"], resumed["dropped"]) == (True, False)
    assert ids(resumed["review"]) == ids(removed)


def test_chat_prepare_run_and_apply_work_after_a_tag_write(chat_setup, caplog) -> None:
    facade, transport, backend, _, _ = chat_setup
    _analyzed(backend)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Chat review"})
    target = Path(backend.review.recommendation.ordered_tracks[1].path)
    rewrite_tags(target)
    review_id = result["reviewId"]
    transport.reply = answer(replace_at(2))
    with caplog.at_level(logging.INFO):
        preview = prepare(facade, review_id)
    assert preview["surface"] == "chat" and preview["previewId"]
    # Preparing the chat context accepts the same recording and logs one info line.
    assert len(_accepted(caplog)) == 1
    actions = turn(facade, review_id)["result"]["actions"]
    assert len(actions) == 1
    applied = call(facade, "ai.chat.apply", {"actionId": actions[0]["actionId"]})
    assert applied["review"]["reviewId"] != review_id


@pytest.mark.parametrize("case", REFUSALS)
def test_a_changed_recording_still_refuses_every_edit_and_drops_the_list(library, case, caplog) -> None:
    backend, _, result = library
    target = Path(backend.review.recommendation.ordered_tracks[1].path)
    _mutate(target, case)
    before = state(backend)
    with pytest.raises(BackendError) as error:
        backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": ids(result)[2]})
    assert error.value.code == "stale_review"
    assert state(backend) == before
    with caplog.at_level(logging.INFO):
        restarted = stored_backend(backend)
    assert restarted.execute("review.resume", {}) == {"available": False, "review": None, "dropped": True}
    assert not _accepted(caplog)
