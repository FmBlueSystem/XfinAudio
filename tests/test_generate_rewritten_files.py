"""Generating and selecting a set after a DJ program rewrote tags (S5).

The fixtures are real FLAC files: rewriting a tag changes the file size and the
modification time while the path, the audio stream and its duration stay put. A
track that is missing, moved, unreadable or of another duration is never accepted
into a generated list.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from tests.test_headless_ai_context import FIXTURES
from tests.test_headless_backend import tagged_flac
from tests.test_headless_prep_parity import identity
from tests.test_review_recovery import stored_backend
from tests.test_review_tag_write import _analyzed, rewrite_tags  # noqa: PLC2701
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.serato_safety import source_identity

CHANGED_RECORDINGS = ("deleted", "different_length", "unreadable", "moved")


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "music"
    shutil.copytree(FIXTURES, root)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    _analyzed(backend)
    return backend, root


def ids(result: dict) -> list[str]:
    return [track["id"] for track in result["tracks"]]


def records(backend):
    return {record.path: record for record in backend.repository.list_tracks()}


def profiles_kept(backend, paths: list[Path]) -> bool:
    """The generated list keeps the profiles the scan recorded for these paths."""
    listed = {track.path: track for track in backend.review.recommendation.ordered_tracks}
    return all(str(path) in listed and listed[str(path)].spectral_profile is not None for path in paths)


def mutate(path: Path, case: str) -> None:
    if case == "different_length":
        tagged_flac(path)
    elif case == "unreadable":
        path.write_bytes(b"not audio after the scan")
    elif case == "deleted":
        path.unlink()
    else:
        path.rename(path.with_name(path.name + ".moved"))


def test_generate_accepts_several_rewritten_tracks(library) -> None:
    backend, root = library
    rewritten = sorted(root.glob("*.flac"))[:3]
    for path in rewritten:
        rewrite_tags(path)
    required = [identity(records(backend)[str(path)]) for path in rewritten]

    result = backend.execute(
        "prep.generate", {"targetTrackCount": 4, "name": "Rewritten library", "requiredTrackIds": required}
    )
    assert result["variant"] == "balanced"
    assert len(result["tracks"]) == 4
    assert set(required) <= set(ids(result))
    assert profiles_kept(backend, rewritten)
    assert all(backend.review_actions.sources[str(path)][1] == source_identity(path) for path in rewritten)
    selected = backend.execute("prep.select", {"planId": result["planId"], "variant": "safe"})
    assert selected["planId"] == result["planId"]
    assert selected["variant"] == "safe"
    assert len(ids(selected)) == 4


def test_generate_accepts_a_rewritten_opening_track(library) -> None:
    backend, root = library
    opening = sorted(root.glob("*.flac"))[0]
    rewrite_tags(opening)
    opening_id = identity(records(backend)[str(opening)])

    result = backend.execute(
        "prep.generate", {"targetTrackCount": 4, "name": "Rewritten opener", "startTrackId": opening_id}
    )
    assert ids(result)[0] == opening_id
    assert len(ids(result)) == 4
    assert profiles_kept(backend, [opening])
    assert backend.execute("review.details", {"reviewId": result["reviewId"]})["planId"] == result["planId"]


def test_generate_after_a_stored_review_and_rewritten_tags(library) -> None:
    backend, root = library
    backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Earlier set"})
    rewritten = sorted(root.glob("*.flac"))[:3]
    for path in rewritten:
        rewrite_tags(path)
    required = [identity(records(backend)[str(path)]) for path in rewritten]

    restarted = stored_backend(backend)
    result = restarted.execute(
        "prep.generate", {"targetTrackCount": 4, "name": "Current set", "requiredTrackIds": required}
    )
    assert set(required) <= set(ids(result))
    assert profiles_kept(restarted, rewritten)


def test_select_accepts_rewritten_tags_after_generation(library) -> None:
    backend, root = library
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Earlier set"})
    rewritten = sorted(root.glob("*.flac"))[:3]
    for path in rewritten:
        rewrite_tags(path)

    selected = backend.execute("prep.select", {"planId": result["planId"], "variant": "adventurous"})
    assert selected["planId"] == result["planId"]
    assert selected["variant"] == "adventurous"
    assert len(ids(selected)) == 4
    assert all(
        restarted_source is not None
        for restarted_source in (backend.review_actions.sources.get(str(path)) for path in rewritten)
    )


@pytest.mark.parametrize("case", CHANGED_RECORDINGS)
def test_a_changed_recording_never_enters_the_generated_list(library, case) -> None:
    backend, root = library
    changed = sorted(root.glob("*.flac"))[0]
    changed_id = identity(records(backend)[str(changed)])
    mutate(changed, case)
    if case == "different_length":
        assert abs(FLAC(changed).info.length - 2.0) > 2.0

    result = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Changed recording"})
    assert changed_id not in ids(result)
    assert len(ids(result)) == 4
    assert str(changed) not in backend.review_actions.sources
    assert backend.execute("prep.select", {"planId": result["planId"], "variant": "safe"})["variant"] == "safe"


def test_a_missing_opening_track_is_refused_without_a_review(library) -> None:
    backend, root = library
    missing = sorted(root.glob("*.flac"))[0]
    missing_id = identity(records(backend)[str(missing)])
    before = len(records(backend))
    mutate(missing, "deleted")

    with pytest.raises(BackendError) as refused:
        backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Missing opener", "startTrackId": missing_id})
    assert refused.value.code == "invalid_params"
    assert backend.review is None and backend.plan is None
    assert len(records(backend)) == before


def test_an_untouched_library_still_generates_and_selects(library) -> None:
    """PRESERVE: no tag write leaves generation, selection and profiles unchanged."""
    backend, root = library
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Untouched"})
    assert result["variant"] == "balanced"
    assert len(ids(result)) == 4
    assert profiles_kept(backend, sorted(root.glob("*.flac"))[:4])
    selected = backend.execute("prep.select", {"planId": result["planId"], "variant": "safe"})
    assert selected["planId"] == result["planId"]
    assert len(ids(selected)) == 4
