"""Opening a saved playlist creates a real review in the core (S3, S6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.application.playlist_edit_assessment import assess_playlist_edit
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.library.models import TrackRecord


def saved_playlist(
    backend: HeadlessBackend, records: list[TrackRecord], name: str = "Saved set"
) -> tuple[Any, list[str]]:
    """Save the records in reverse path order, so the saved order is not the library order."""
    order = [record.path for record in records][::-1]
    return backend.playlists.create(name, order), order


def test_opening_a_saved_playlist_answers_a_real_saved_review(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 6)
    playlist, order = saved_playlist(backend, records)
    opened = backend.execute("playlist.open", {"playlistId": playlist.id})

    assert opened["reviewId"] == backend.review_id
    assert opened["variant"] == "saved"
    assert opened["savedPlaylistId"] == playlist.id
    assert opened["name"] == "Saved set"
    assert opened["editable"] is True
    by_path = {record.path: record for record in records}
    assert [track["id"] for track in opened["tracks"]] == [identity(by_path[path]) for path in order]
    assessment = assess_playlist_edit(order, records)
    assert opened["qualityScore"] == assessment.quality.average_transition_score
    assert opened["readiness"] == assessment.readiness.status
    assert opened["blockers"] == []
    assert opened["warnings"] == []
    assert opened["readinessChecks"] == [check.model_dump(mode="json") for check in assessment.readiness.checks]
    assert len(opened["transitionScores"]) == len(order) - 1
    assert opened["transitionScores"] == [score.total_score for score in assessment.recommendation.transition_scores]
    assert opened["canUndo"] is False
    assert opened["canRedo"] is False
    # A saved list keeps no required or opening track, so nothing is protected.
    assert opened["protectedTrackIds"] == []
    assert str(tmp_path) not in json.dumps(opened)


def test_the_saved_review_answers_review_details_with_its_own_identity(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 5)
    playlist, order = saved_playlist(backend, records)
    opened = backend.execute("playlist.open", {"playlistId": playlist.id})
    details = backend.execute("review.details", {"reviewId": opened["reviewId"]})

    assert details["reviewId"] == opened["reviewId"]
    assert details["savedPlaylistId"] == playlist.id
    assert details["variant"] == "saved"
    assert [track["id"] for track in details["tracks"]] == [track["id"] for track in opened["tracks"]]
    assert len(details["transitions"]) == len(order) - 1
    assert [transition["totalScore"] for transition in details["transitions"]] == opened["transitionScores"]
    assert "Local engine" in details["engineFacts"]
    assert str(tmp_path) not in json.dumps(details)


def test_a_playlist_with_a_missing_track_or_fewer_than_two_opens_read_only(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 5)
    playlist = backend.playlists.create("Missing", [record.path for record in records])
    Path(records[0].path).unlink()
    opened = backend.execute("playlist.open", {"playlistId": playlist.id})

    assert opened["editable"] is False
    assert set(opened) == {"id", "name", "tracks", "missingTrackCount", "editable"}
    assert opened["id"] == playlist.id
    assert opened["name"] == "Missing"
    assert opened["missingTrackCount"] == 1
    assert identity(records[0]) not in [track["id"] for track in opened["tracks"]]

    short = backend.playlists.create("Short", [records[1].path])
    opened_short = backend.execute("playlist.open", {"playlistId": short.id})
    assert opened_short["editable"] is False
    assert set(opened_short) == {"id", "name", "tracks", "missingTrackCount", "editable"}
    assert opened_short["missingTrackCount"] == 0
    assert [track["id"] for track in opened_short["tracks"]] == [identity(records[1])]


def test_a_read_only_open_leaves_the_generated_list_in_progress_untouched(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 5)
    generated = backend.execute("prep.generate", {"targetTrackCount": 3})
    playlist = backend.playlists.create("Missing", [record.path for record in records])
    listed = {track["id"] for track in generated["tracks"]}
    missing = next(record for record in records if identity(record) not in listed)
    Path(missing.path).unlink()
    opened = backend.execute("playlist.open", {"playlistId": playlist.id})

    assert opened["editable"] is False
    assert opened["missingTrackCount"] == 1
    assert backend.review_id == generated["reviewId"]
    details = backend.execute("review.details", {"reviewId": generated["reviewId"]})
    assert [track["id"] for track in details["tracks"]] == [track["id"] for track in generated["tracks"]]


def test_opening_a_saved_playlist_replaces_the_generated_list_in_progress(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 8)
    generated = backend.execute("prep.generate", {"targetTrackCount": 4})
    assert (backend.data_dir / "active_review.json").exists()
    playlist, order = saved_playlist(backend, records)
    opened = backend.execute("playlist.open", {"playlistId": playlist.id})

    assert opened["reviewId"] != generated["reviewId"]
    assert backend.review_id == opened["reviewId"]
    assert [track.path for track in backend.review.recommendation.ordered_tracks] == order
    with pytest.raises(BackendError) as error:
        backend.execute("review.details", {"reviewId": generated["reviewId"]})
    assert error.value.code == "stale_review"
    assert backend.execute("review.resume", {})["review"]["reviewId"] == opened["reviewId"]
    assert (backend.data_dir / "active_review.json").exists()
