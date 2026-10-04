"""Request-scoped ephemeral tokens and bounded improvement candidate validation."""

from __future__ import annotations

import math
import re

import pytest

from xfinaudio.application.playlist_improvement import (
    MAX_CANDIDATES,
    MAX_DRAFT_TRACKS,
    MAX_REPLACEMENT_CANDIDATES,
    MAX_TOKEN_LENGTH,
    ImprovementError,
    build_candidate_set,
    generate_tokens,
)
from xfinaudio.library.models import MetadataStatus, TrackRecord

TOKEN_PATTERN = re.compile(r"[0-9a-f]{16}")


def record(
    path: str,
    *,
    bpm: float | None = 124.0,
    key: str | None = "8A",
    energy: int | None = 6,
    duration: float | None = 300.0,
    title: str | None = None,
    artist: str | None = None,
    genre: str | None = None,
    status: MetadataStatus = "complete",
    missing: tuple[str, ...] = (),
) -> TrackRecord:
    return TrackRecord(
        path=path,
        title=f"Title {path}" if title is None else title,
        artist=f"Artist {path}" if artist is None else artist,
        bpm=bpm,
        camelot_key=key,
        energy_level=energy,
        duration=duration,
        genre=genre,
        metadata_status=status,
        missing_required_fields=list(missing),
    )


def records_for(paths: list[str]) -> list[TrackRecord]:
    return [record(path) for path in paths]


def token_factory(start: int = 0):
    counter = {"value": start}

    def make() -> str:
        counter["value"] += 1
        return f"{counter['value']:016x}"

    return make


def sequenced(*values: str):
    pending = list(values)

    def make() -> str:
        return pending.pop(0)

    return make


# --- I1.1 ephemeral tokens: random, unique, request-scoped ---------------------


def test_generated_tokens_are_16_lowercase_hex_and_unique() -> None:
    tokens = generate_tokens(MAX_CANDIDATES)
    assert len(tokens) == MAX_CANDIDATES
    assert len(set(tokens)) == MAX_CANDIDATES
    assert all(TOKEN_PATTERN.fullmatch(token) for token in tokens)


def test_token_collision_is_regenerated_never_resolved_first_wins() -> None:
    source = sequenced(f"{1:016x}", f"{1:016x}", f"{2:016x}")
    assert generate_tokens(2, token_source=source) == (f"{1:016x}", f"{2:016x}")


def test_token_generation_fails_closed_when_source_never_varies() -> None:
    with pytest.raises(ImprovementError) as error:
        generate_tokens(2, token_source=lambda: f"{1:016x}")
    assert error.value.code == "invalid_improvement"


@pytest.mark.parametrize("bad", ["", "Z" * MAX_TOKEN_LENGTH, "abc", f"{1:016x}0", None])
def test_token_source_output_is_validated(bad: object) -> None:
    with pytest.raises(ImprovementError) as error:
        generate_tokens(1, token_source=lambda: bad)  # type: ignore[arg-type,return-value]
    assert error.value.code == "invalid_improvement"


def test_token_count_is_bounded_by_total_candidate_cap() -> None:
    assert generate_tokens(0) == ()
    with pytest.raises(ImprovementError) as error:
        generate_tokens(MAX_CANDIDATES + 1)
    assert error.value.code == "ai_context_too_large"


def test_same_draft_produces_fresh_tokens_per_request() -> None:
    paths = ["a", "b", "c"]
    records = records_for(paths)
    first = build_candidate_set(paths, records, token_source=token_factory())
    second = build_candidate_set(paths, records, token_source=token_factory(start=100))
    assert first.draft_tokens != second.draft_tokens
    assert set(first.draft_tokens).isdisjoint(second.draft_tokens)


def test_same_path_never_yields_a_stable_cross_request_token() -> None:
    paths = ["a", "b"]
    records = records_for(paths)
    first = build_candidate_set(paths, records)
    second = build_candidate_set(paths, records)
    assert first.paths_by_token.keys().isdisjoint(second.paths_by_token.keys())


# --- I1.3 authorized candidate set: bounded and local --------------------------


def test_authorized_set_lists_draft_tokens_in_draft_order() -> None:
    paths = ["a", "b", "c"]
    candidate_set = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    assert candidate_set.draft_tokens == (f"{1:016x}", f"{2:016x}", f"{3:016x}")
    assert candidate_set.replacement_tokens == ()
    assert [candidate_set.paths_by_token[token] for token in candidate_set.draft_tokens] == paths


def test_replacement_pool_is_empty_unless_opted_in() -> None:
    paths = ["a", "b"]
    pool = records_for(["p1", "p2", "p3"])
    disabled = build_candidate_set(paths, [*records_for(paths), *pool], token_source=token_factory())
    assert disabled.replacement_tokens == ()
    enabled = build_candidate_set(
        paths, [*records_for(paths), *pool], include_replacements=True, token_source=token_factory()
    )
    assert len(enabled.replacement_tokens) == 3


def test_replacement_pool_excludes_draft_and_excluded_paths() -> None:
    paths = ["a", "b"]
    pool = records_for(["a", "b", "p1", "p2"])
    candidate_set = build_candidate_set(
        paths,
        pool,
        include_replacements=True,
        excluded_paths={"p2"},
        token_source=token_factory(),
    )
    selected = {candidate_set.paths_by_token[token] for token in candidate_set.replacement_tokens}
    assert selected == {"p1"}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"bpm": None},
        {"bpm": 0.0},
        {"bpm": math.nan},
        {"key": None},
        {"key": "13A"},
        {"energy": None},
        {"energy": 0},
        {"energy": 11},
        {"duration": None},
        {"duration": 0.0},
        {"duration": math.inf},
        {"title": ""},
        {"artist": ""},
    ],
)
def test_replacement_pool_excludes_incomplete_metadata(kwargs: dict[str, object]) -> None:
    paths = ["a", "b"]
    incomplete = record("p1", **kwargs)  # type: ignore[arg-type]
    candidate_set = build_candidate_set(
        paths,
        [*records_for(paths), incomplete, record("p2")],
        include_replacements=True,
        token_source=token_factory(),
    )
    assert {candidate_set.paths_by_token[token] for token in candidate_set.replacement_tokens} == {"p2"}


def test_replacement_pool_accepts_records_without_optional_genre() -> None:
    paths = ["a", "b"]
    candidate_set = build_candidate_set(
        paths,
        [*records_for(paths), record("p1", genre=None)],
        include_replacements=True,
        token_source=token_factory(),
    )
    assert {candidate_set.paths_by_token[token] for token in candidate_set.replacement_tokens} == {"p1"}
    assert candidate_set.candidates[-1].genre == ""


def test_replacement_pool_deduplicates_repeated_records() -> None:
    paths = ["a", "b"]
    candidate_set = build_candidate_set(
        paths,
        [*records_for(paths), record("p1"), record("p1"), record("p2")],
        include_replacements=True,
        token_source=token_factory(),
    )
    selected = [candidate_set.paths_by_token[token] for token in candidate_set.replacement_tokens]
    assert selected == ["p1", "p2"]


def test_candidate_set_never_authorizes_a_path_twice() -> None:
    paths = ["a", "b"]
    candidate_set = build_candidate_set(
        paths,
        [*records_for(paths), record("a"), record("p1")],
        include_replacements=True,
        token_source=token_factory(),
    )
    resolved = list(candidate_set.paths_by_token.values())
    assert len(resolved) == len(set(resolved))
    assert resolved.count("a") == 1


def test_replacement_pool_caps_at_twenty() -> None:
    paths = ["a", "b"]
    pool = records_for([f"p{index}" for index in range(30)])
    candidate_set = build_candidate_set(
        paths, [*records_for(paths), *pool], include_replacements=True, token_source=token_factory()
    )
    assert len(candidate_set.replacement_tokens) == MAX_REPLACEMENT_CANDIDATES
    assert len(candidate_set.candidates) == 2 + MAX_REPLACEMENT_CANDIDATES
    assert len(candidate_set.candidates) < MAX_CANDIDATES


def test_total_candidates_never_exceed_one_hundred() -> None:
    paths = [f"d{index}" for index in range(MAX_DRAFT_TRACKS)]
    pool = records_for([f"p{index}" for index in range(30)])
    candidate_set = build_candidate_set(
        paths, [*records_for(paths), *pool], include_replacements=True, token_source=token_factory()
    )
    assert len(candidate_set.candidates) == MAX_CANDIDATES
    assert len(candidate_set.draft_tokens) == MAX_DRAFT_TRACKS
    assert len(candidate_set.replacement_tokens) == MAX_REPLACEMENT_CANDIDATES
    assert len(set(candidate_set.tokens)) == MAX_CANDIDATES


def test_draft_above_cap_fails_closed_without_truncation() -> None:
    paths = [f"d{index}" for index in range(MAX_DRAFT_TRACKS + 1)]
    with pytest.raises(ImprovementError) as error:
        build_candidate_set(paths, records_for(paths))
    assert error.value.code == "ai_context_too_large"
    assert str(MAX_DRAFT_TRACKS) in str(error.value)


def test_exactly_capped_draft_is_authorized() -> None:
    paths = [f"d{index}" for index in range(MAX_DRAFT_TRACKS)]
    candidate_set = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    assert len(candidate_set.draft_tokens) == MAX_DRAFT_TRACKS


def test_empty_or_duplicated_draft_fails_closed() -> None:
    with pytest.raises(ImprovementError) as empty:
        build_candidate_set([], [])
    assert empty.value.code == "invalid_improvement"
    with pytest.raises(ImprovementError) as duplicated:
        build_candidate_set(["a", "a"], records_for(["a"]))
    assert duplicated.value.code == "invalid_improvement"


def test_draft_path_without_local_record_fails_closed_without_path_egress() -> None:
    with pytest.raises(ImprovementError) as error:
        build_candidate_set(["a", "b"], [record("a")])
    assert error.value.code == "invalid_improvement"


def test_draft_candidate_without_title_does_not_derive_it_from_the_path() -> None:
    candidate_set = build_candidate_set(
        ["a", "b"], [record("a", title="", artist=""), record("b")], token_source=token_factory()
    )
    first = candidate_set.candidates[0]
    assert first.title == ""
    assert "a" not in first.as_payload().values()
    assert "path" not in first.as_payload()


def test_replacement_selection_is_deterministic_and_order_independent() -> None:
    paths = ["a", "b"]
    draft = [record("a", bpm=120.0, key="8A"), record("b", bpm=124.0, key="9A")]
    near = record("near", bpm=122.0, key="8A")
    far = record("far", bpm=130.0, key="5A")
    forward = build_candidate_set(paths, [*draft, near, far], include_replacements=True, token_source=token_factory())
    reversed_input = build_candidate_set(
        paths, [*reversed(draft), far, near], include_replacements=True, token_source=token_factory()
    )
    assert [forward.paths_by_token[token] for token in forward.replacement_tokens] == ["near", "far"]
    assert reversed_input.replacement_tokens == forward.replacement_tokens


def test_payload_discloses_only_bounded_fields_and_no_stable_identity() -> None:
    candidate_set = build_candidate_set(["a", "b"], records_for(["a", "b"]), token_source=token_factory())
    payload = candidate_set.candidates[0].as_payload()
    assert set(payload) == {
        "token",
        "title",
        "artist",
        "genre",
        "bpm",
        "key",
        "energy",
        "duration",
        "status",
        "missingFields",
    }
    assert TOKEN_PATTERN.fullmatch(str(payload["token"]))
    serialized = repr(payload)
    assert "/" not in serialized
    assert not re.search(r"[0-9a-f]{64}", serialized)
