"""The chat reads the disk identity only of the tracks its list holds (S4).

A chat turn must still notice a track of the list changing on disk; every other library
track contributes its stored record without the disk being read, so one prepared chat
request on a large library costs tens of identity reads instead of one per track.
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

chat_setup = _chat_setup

# S4: one chat request on a 200-track library with a 10-track list reads at most this many.
MAX_CHAT_IDENTITY_READS = 60
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
