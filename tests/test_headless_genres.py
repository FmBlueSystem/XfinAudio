"""Read-only genre catalog for the Prep genre picker (compatible-first ordering)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from xfinaudio.headless.backend import BackendError, HeadlessBackend


def tagged_flac(
    path: Path,
    *,
    title: str,
    genre: str | None = None,
    bpm: float | None = None,
    key: str | None = None,
    energy: int | None = None,
) -> None:
    """A metadata-only FLAC fixture, never used as a playback fixture."""
    path.parent.mkdir(parents=True, exist_ok=True)
    streaminfo = b"\x10\x00\x10\x00" + bytes(6)
    streaminfo += ((44100 << 44) | (1 << 41) | (15 << 36) | (44100 * 240)).to_bytes(8, "big")
    path.write_bytes(b"fLaC\x80\x00\x00\x22" + streaminfo + bytes(16))
    tags = FLAC(path)
    tags["title"] = title
    tags["artist"] = "Test Artist"
    if genre is not None:
        tags["genre"] = genre
    if bpm is not None:
        tags["bpm"] = str(bpm)
    if key is not None:
        tags["initialkey"] = key
    if energy is not None:
        tags["energylevel"] = str(energy)
    tags.save()


def library(tmp_path: Path, specs: list[tuple[str, str | None, float | None, str | None, int | None]]):
    root = tmp_path / "music"
    for name, genre, bpm, key, energy in specs:
        tagged_flac(root / f"{name}.flac", title=name, genre=genre, bpm=bpm, key=key, energy=energy)
    backend = HeadlessBackend(tmp_path / "data")
    scanned = backend.execute("library.scan", {"root": str(root)})["tracks"]
    identities = {track["title"]: track["id"] for track in scanned}
    return backend, identities


def seed_library(tmp_path: Path):
    """One seed at 124 BPM / 8A / energy 5 plus one neighbour per compatibility rule."""
    return library(
        tmp_path,
        [
            ("seed", "House", 124, "8A", 5),
            ("house-mix", "House", 126, "8A", 6),
            ("deep-one", "Deep House", 125, "8B", 5),
            ("deep-two", "Deep House", 62, "8A", 5),
            ("ambient-one", "Ambient", 62, "8A", 5),
            ("techno-one", "Techno", 140, "8A", 5),
            ("techno-two", "Techno", 141, "8A", 5),
            ("drum-one", "Drum & Bass", 124, "8A", 9),
            ("trance-one", "Trance", 124, "1A", 5),
            ("soul-one", "Soul", 124, "8A", 7),
        ],
    )


def test_genres_group_case_and_accent_insensitively_with_the_stored_spelling(tmp_path: Path) -> None:
    backend, _ = library(
        tmp_path,
        [
            ("a", "Techno", 120, "8A", 5),
            ("b", "TECHNO", 121, "8A", 5),
            ("c", "techno", 122, "8A", 5),
            ("d", "Electrónica", 120, "8A", 5),
            ("e", "ELECTRÓNICA", 120, "8A", 5),
            ("f", "Electronica", 120, "8A", 5),
            ("g", None, 120, "8A", 5),
        ],
    )
    result = backend.execute("prep.genres", {})
    assert result["groups"] == [
        {
            "kind": "library",
            "genres": [
                {"name": "Techno", "count": 3},
                {"name": "Electrónica", "count": 2},
                {"name": "Electronica", "count": 1},
            ],
        }
    ]
    assert result["totalGenres"] == 3
    assert result["seedTitle"] is None


def test_without_a_seed_the_genres_are_one_list_ordered_by_track_count(tmp_path: Path) -> None:
    backend, _ = seed_library(tmp_path)
    result = backend.execute("prep.genres", {})
    assert [group["kind"] for group in result["groups"]] == ["library"]
    assert result["groups"][0]["genres"] == [
        {"name": "Deep House", "count": 2},
        {"name": "House", "count": 2},
        {"name": "Techno", "count": 2},
        {"name": "Ambient", "count": 1},
        {"name": "Drum & Bass", "count": 1},
        {"name": "Soul", "count": 1},
        {"name": "Trance", "count": 1},
    ]
    assert result["totalGenres"] == 7
    assert result["seedTitle"] is None


def test_a_seed_shows_its_own_genre_first_then_compatible_genres_then_the_rest(tmp_path: Path) -> None:
    backend, identities = seed_library(tmp_path)
    result = backend.execute("prep.genres", {"startTrackId": identities["seed"]})
    assert result["seedTitle"] == "seed"
    assert [group["kind"] for group in result["groups"]] == ["compatible", "library"]
    assert result["groups"][0]["genres"] == [
        {"name": "House", "count": 2},
        {"name": "Deep House", "count": 2},
        {"name": "Ambient", "count": 1},
    ]
    assert result["groups"][1]["genres"] == [
        {"name": "Drum & Bass", "count": 1},
        {"name": "Soul", "count": 1},
        {"name": "Techno", "count": 2},
        {"name": "Trance", "count": 1},
    ]
    assert result["totalGenres"] == 7


def test_half_and_double_time_bpm_still_mix_while_a_far_tempo_does_not(tmp_path: Path) -> None:
    backend, identities = library(
        tmp_path,
        [
            ("seed", "House", 124, "8A", 5),
            ("half", "Downtempo", 62, "8A", 5),
            ("double", "Hard Techno", 248, "8A", 5),
            ("far", "Speedcore", 200, "8A", 5),
        ],
    )
    result = backend.execute("prep.genres", {"startTrackId": identities["seed"]})
    assert result["groups"][0]["genres"] == [
        {"name": "House", "count": 1},
        {"name": "Downtempo", "count": 1},
        {"name": "Hard Techno", "count": 1},
    ]
    assert result["groups"][1]["genres"] == [{"name": "Speedcore", "count": 1}]


def test_a_clashing_key_or_a_distant_energy_level_is_not_compatible(tmp_path: Path) -> None:
    backend, identities = seed_library(tmp_path)
    result = backend.execute("prep.genres", {"startTrackId": identities["seed"]})
    rest = [option["name"] for group in result["groups"][1:] for option in group["genres"]]
    assert rest == ["Drum & Bass", "Soul", "Techno", "Trance"]
    assert "Trance" in rest, "a key that clashes with the seed is not compatible"
    assert "Soul" in rest, "two energy levels away is not similar energy"


def test_an_incomplete_track_counts_in_its_genre_but_never_ranks_as_compatible(tmp_path: Path) -> None:
    backend, identities = library(
        tmp_path,
        [
            ("seed", "House", 124, "8A", 5),
            ("broken", "Dubstep", 124, "8A", None),
        ],
    )
    result = backend.execute("prep.genres", {"startTrackId": identities["seed"]})
    assert [group["kind"] for group in result["groups"]] == ["compatible", "library"]
    assert result["groups"][0]["genres"] == [{"name": "House", "count": 1}]
    assert result["groups"][1]["genres"] == [{"name": "Dubstep", "count": 1}]


def test_the_stored_genre_availability_is_casefolded_and_fails_closed(tmp_path: Path) -> None:
    backend, _ = seed_library(tmp_path)
    assert backend.execute("prep.genres", {"genre": "deep HOUSE"})["genreAvailable"] is True
    assert backend.execute("prep.genres", {"genre": "  House  "})["genreAvailable"] is True
    assert backend.execute("prep.genres", {"genre": "Deep"})["genreAvailable"] is False
    assert backend.execute("prep.genres", {"genre": "Garage"})["genreAvailable"] is False
    assert backend.execute("prep.genres", {})["genreAvailable"] is True
    assert backend.execute("prep.genres", {"genre": ""})["genreAvailable"] is True


def test_unknown_or_malformed_seed_identities_fail_closed(tmp_path: Path) -> None:
    backend, _ = seed_library(tmp_path)
    with pytest.raises(BackendError) as unknown:
        backend.execute("prep.genres", {"startTrackId": "f" * 64})
    assert unknown.value.code == "not_found"
    for malformed in ["/tmp/music", "seed", "F" * 64, "", None, 42, "f" * 63]:
        with pytest.raises(BackendError) as error:
            backend.execute("prep.genres", {"startTrackId": malformed})
        assert error.value.code == "invalid_params"


def test_unexpected_or_unbounded_parameters_fail_closed(tmp_path: Path) -> None:
    backend, _ = seed_library(tmp_path)
    for params in ({"start": "x"}, {"genre": "x" * 101}, {"genre": 3}, {"genre": "House\u0000"}):
        with pytest.raises(BackendError) as error:
            backend.execute("prep.genres", params)
        assert error.value.code == "invalid_params"


def test_the_catalog_never_exposes_authorized_library_paths(tmp_path: Path) -> None:
    backend, identities = seed_library(tmp_path)
    payload = json.dumps(backend.execute("prep.genres", {"startTrackId": identities["seed"]}))
    assert str(tmp_path) not in payload
    assert ".flac" not in payload
