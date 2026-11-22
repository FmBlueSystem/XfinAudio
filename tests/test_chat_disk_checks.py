"""The chat reads the disk identity only of the tracks its list holds (S3, S4, S5).

A chat turn must still notice a track of the list changing on disk; every other library
track contributes its stored record without the disk being read, so one prepared chat
request on a large library resolves tens of paths and reads the library table once
instead of walking every library file per guard.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.test_headless_ai_context import setup as setup  # noqa: F401
from tests.test_headless_list_chat import QUESTION, ChatTransport, call, forbidden, prepare
from tests.test_headless_list_chat import chat_setup as _chat_setup
from tests.test_headless_prep_parity import seeded
from xfinaudio.ai import nan_client
from xfinaudio.headless import ai_context as ai_context_module
from xfinaudio.headless import generated_review as generated_review_module
from xfinaudio.headless import profiles as profiles_module
from xfinaudio.headless import serato_source as serato_source_module
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.optional_ai import OptionalAI
from xfinaudio.library.track_repository import TrackRepository

chat_setup = _chat_setup

# S3, S4: one chat request on a 200-track library with a 10-track list reads at most this many.
MAX_CHAT_IDENTITY_READS = 60
# S3: one prepared turn resolves this many paths on disk and reads the library table once.
MAX_CHAT_DISK_RESOLVES = 60
MAX_CHAT_LIBRARY_READS = 1
TRACKS_IN_LIBRARY = 200
TRACKS_IN_LIST = 10

MUTATIONS = ("changed", "moved", "deleted")


@pytest.fixture
def identity_reads(monkeypatch):
    """Count every on-disk identity read a chat command makes, wherever it comes from."""
    reads: list[str] = []
    for module in (ai_context_module, generated_review_module, profiles_module, serato_source_module):
        read = module.source_identity

        def counting(path, _read=read):
            reads.append(str(path))
            return _read(path)

        monkeypatch.setattr(module, "source_identity", counting)
    return reads


@pytest.fixture
def disk_resolves(monkeypatch):
    """Count every path checked against the authorized roots while a command runs (S3)."""
    resolves: list[str] = []
    for module in (generated_review_module, profiles_module, serato_source_module):
        inside = module._inside

        def counting(path, root, _inside=inside):
            resolves.append(str(path))
            return _inside(path, root)

        monkeypatch.setattr(module, "_inside", counting)
    return resolves


@pytest.fixture
def library_reads(monkeypatch):
    """Count every whole-library read, wherever it comes from (S3)."""
    reads: list[int] = []
    listed = TrackRepository.list_display_tracks

    def counting(self):
        reads.append(1)
        return listed(self)

    monkeypatch.setattr(TrackRepository, "list_display_tracks", counting)
    return reads


def mutate(path: str, mutation: str) -> None:
    target = Path(path)
    if mutation == "changed":
        target.write_bytes(b"changed after the list was prepared")
    elif mutation == "moved":
        target.rename(target.with_name(target.name + ".moved"))
    else:
        target.unlink()


def chat(tmp_path: Path, monkeypatch):
    """One offline chat facade over a seeded library, with every real request forbidden."""
    monkeypatch.setattr(nan_client, "_urlopen", forbidden)
    backend, _ = seeded(tmp_path, TRACKS_IN_LIBRARY)
    result = backend.execute("prep.generate", {"targetTrackCount": TRACKS_IN_LIST})
    return OptionalAI(backend, transport=ChatTransport()), backend, result


def test_one_chat_request_reads_the_disk_identity_only_of_the_tracks_in_the_list(
    tmp_path: Path, identity_reads, monkeypatch
) -> None:
    facade, backend, result = chat(tmp_path, monkeypatch)
    assert len(result["tracks"]) == TRACKS_IN_LIST
    listed = {track.path for track in backend.review.recommendation.ordered_tracks}
    del identity_reads[:]
    prepared = call(
        facade,
        "ai.prepare",
        {"surface": "chat", "request": QUESTION, "context": {"reviewId": result["reviewId"]}},
    )
    assert prepared["surface"] == "chat"
    # The list, and not the other library tracks: one entry per track of the list.
    assert set(identity_reads) <= listed
    assert len(identity_reads) <= MAX_CHAT_IDENTITY_READS


def test_one_prepared_chat_request_reads_the_library_once_and_resolves_only_its_tracks(
    tmp_path: Path, disk_resolves, library_reads, monkeypatch
) -> None:
    facade, backend, result = chat(tmp_path, monkeypatch)
    assert len(result["tracks"]) == TRACKS_IN_LIST
    listed = {track.path for track in backend.review.recommendation.ordered_tracks}
    del disk_resolves[:]
    del library_reads[:]

    prepared = call(
        facade,
        "ai.prepare",
        {"surface": "chat", "request": QUESTION, "context": {"reviewId": result["reviewId"]}},
    )

    assert prepared["surface"] == "chat"
    # The list, and no other library track, is checked against the authorized roots.
    assert set(disk_resolves) <= listed
    assert len(disk_resolves) <= MAX_CHAT_DISK_RESOLVES
    # One command reads the stored library once instead of once per guard.
    assert len(library_reads) == MAX_CHAT_LIBRARY_READS


def test_a_generation_still_checks_every_library_track_on_disk(tmp_path: Path, disk_resolves) -> None:
    """PRESERVE: the shared source builder keeps checking what a generation acts on (S3)."""
    backend, records = seeded(tmp_path, TRACKS_IN_LIBRARY)
    del disk_resolves[:]

    result = backend.execute("prep.generate", {"targetTrackCount": TRACKS_IN_LIST})

    assert len(result["tracks"]) == TRACKS_IN_LIST
    assert {record.path for record in records} <= set(disk_resolves)


@pytest.mark.parametrize("mutation", MUTATIONS)
def test_a_list_track_changed_on_disk_makes_a_prepared_chat_turn_stale(chat_setup, mutation: str) -> None:
    facade, transport, backend, _, _ = chat_setup
    prepared = prepare(facade, backend.review_id)
    mutate(backend.review.recommendation.ordered_tracks[1].path, mutation)
    with pytest.raises(BackendError) as error:
        call(facade, "ai.run", {"previewId": prepared["previewId"], "confirmed": True})
    assert error.value.code == "stale_ai"
    # A refused turn never reached the provider.
    assert transport.bodies == []
