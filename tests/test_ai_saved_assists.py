"""Saved-set language uses ephemeral IDs and truthful anonymous aggregates."""

import json
from datetime import datetime

import pytest

from tests.test_ai_intent_copilot import FakeTransport, message_text
from xfinaudio.ai.structured_assists import (
    anonymize_saved_request,
    build_saved_descriptors,
    interpret_saved_request,
)
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.playlist_models import Playlist


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-only")
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent"))


def examples():
    now = datetime(2026, 9, 30)
    playlists = [
        Playlist(91812, "Secret Sunset", now, now, ["/private/a.wav", "/private/b.wav"]),
        Playlist(91813, "Evening", now, now, ["/private/b.wav"]),
    ]
    records = [
        TrackRecord(
            path="/private/a.wav",
            title="Secret Title",
            artist="Secret Artist",
            genre="House",
            duration=120,
            bpm=120,
            energy_level=3,
            tags=["private-tag"],
        )
    ]
    return playlists, records


def test_descriptors_preserve_coverage_and_omit_names_paths_tags_and_real_ids():
    playlists, records = examples()
    descriptors = build_saved_descriptors(playlists, records)
    assert descriptors[0].id == "s0"
    assert descriptors[0].track_count == 2
    assert descriptors[0].duration_known == 1
    assert descriptors[0].duration_minutes is None
    assert descriptors[0].genres == ("House",)
    assert descriptors[1].bpm_min is None
    transport = FakeTransport('{"action":"compare","selected_ids":["s0","s1"]}')
    result = interpret_saved_request(
        anonymize_saved_request("Compare SECRET SUNSET with Evening", playlists), descriptors, transport=transport
    )
    assert result.selected_ids == ("s0", "s1")
    assert result.action == "compare"
    prompt = message_text(transport)
    for private in ("Secret", "Evening", "/private", "91812", "91813", "private-tag"):
        assert private not in prompt
    assert "House" in prompt and '"duration_known": 1' in prompt


def test_anonymization_is_single_pass_and_does_not_replace_name_substrings():
    playlists, _ = examples()
    assert anonymize_saved_request("Evening and Eveningness", playlists) == "s1 and Eveningness"
    playlists[0] = Playlist(7, "s1", playlists[0].created_at, playlists[0].updated_at, [])
    assert anonymize_saved_request("compare s1 and Evening", playlists) == "compare s0 and s1"


def test_ambiguous_named_selection_requires_clarification():
    playlists, _ = examples()
    playlists[1] = Playlist(9, "Secret Sunset", playlists[0].created_at, playlists[0].updated_at, [])
    with pytest.raises(ValueError, match="same name"):
        anonymize_saved_request("find secret sunset", playlists)


@pytest.mark.parametrize(
    "response",
    [
        {"action": "delete", "selected_ids": ["s0"]},
        {"action": "find", "selected_ids": ["s99"]},
        {"action": "find", "selected_ids": [91812]},
        {"action": "find", "selected_ids": ["s0", "s0"]},
        {"action": "compare", "selected_ids": ["s0"]},
        {"action": "find", "selected_ids": [], "paths": []},
    ],
)
def test_saved_selection_rejects_arbitrary_actions_ids_and_fields(response):
    playlists, records = examples()
    with pytest.raises(ValueError, match="AI interpretation"):
        interpret_saved_request(
            "find sets", build_saved_descriptors(playlists, records), transport=FakeTransport(json.dumps(response))
        )


def test_empty_find_is_valid_and_does_not_invent_a_match():
    playlists, records = examples()
    assert (
        interpret_saved_request(
            "find techno",
            build_saved_descriptors(playlists, records),
            transport=FakeTransport('{"action":"find","selected_ids":[]}'),
        ).selected_ids
        == ()
    )


def test_invalid_metadata_stays_unknown_and_path_genres_are_not_shared():
    playlists, records = examples()
    records[0] = records[0].model_copy(update={"genre": records[0].path, "bpm": float("nan"), "energy_level": 0})
    descriptor = build_saved_descriptors(playlists, records)[0]
    assert descriptor.genres == ()
    assert descriptor.bpm_known == descriptor.energy_known == 0
    assert descriptor.bpm_min is descriptor.energy_min is None


def test_unicode_saved_names_are_removed_before_network():
    playlists, _ = examples()
    playlists[0] = Playlist(7, "Straße Sunset", playlists[0].created_at, playlists[0].updated_at, [])
    assert anonymize_saved_request("compare Straße Sunset and Evening", playlists) == "compare s0 and s1"


@pytest.mark.parametrize(
    ("name", "reference"),
    [("Straße Sunset", "STRASSE SUNSET"), ("İstanbul", "istanbul"), ("Café", "Cafe\u0301")],
)
def test_saved_name_unicode_equivalents_are_anonymous_and_preserve_other_text(name, reference):
    playlists, _ = examples()
    playlists[0] = Playlist(7, name, playlists[0].created_at, playlists[0].updated_at, [])
    assert (
        anonymize_saved_request(f"Compara {reference} y Evening para mañana", playlists)
        == "Compara s0 y s1 para mañana"
    )


def test_normalization_ambiguous_saved_names_fail_closed():
    playlists, _ = examples()
    playlists = [
        Playlist(index, name, p.created_at, p.updated_at, [])
        for index, (name, p) in enumerate(zip(["Café", "Cafe"], playlists, strict=True))
    ]
    with pytest.raises(ValueError, match="same name"):
        anonymize_saved_request("find café", playlists)
