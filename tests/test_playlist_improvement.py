"""Request-scoped ephemeral tokens and bounded improvement candidate validation."""

from __future__ import annotations

import hashlib
import math
import re
from uuid import UUID

import pytest

from xfinaudio.application.playlist_edit_intents import validate_edit
from xfinaudio.application.playlist_improvement import (
    MAX_CANDIDATES,
    MAX_DRAFT_TRACKS,
    MAX_REPLACEMENT_CANDIDATES,
    MAX_TOKEN_LENGTH,
    MIN_IMPROVEMENT_TRACKS,
    ImprovementError,
    build_candidate_set,
    build_improvement_proposal,
    draft_fingerprint,
    generate_tokens,
    proposal_digest,
    track_id,
    validate_improvement_proposal,
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


# --- I1.5 / I1.6 token-only validator ------------------------------------------


def authorized(count: int, *, factory_start: int = 0) -> tuple[dict[str, str], list[str]]:
    tokens = generate_tokens(count, token_source=token_factory(factory_start))
    return {token: f"path-{index}" for index, token in enumerate(tokens)}, list(tokens)


def test_validator_resolves_authorized_tokens_to_paths() -> None:
    mapping, tokens = authorized(4)
    source = tokens[:2]
    ordered = [tokens[1], tokens[3]]
    assert validate_improvement_proposal(source, mapping, ordered) == ("path-1", "path-3")


def test_validator_allows_reorder_removal_and_bounded_addition() -> None:
    mapping, tokens = authorized(4)
    source = tokens[:3]
    assert validate_improvement_proposal(source, mapping, [tokens[1], tokens[0]]) == ("path-1", "path-0")
    assert validate_improvement_proposal(source, mapping, [tokens[1], tokens[2], tokens[3]]) == (
        "path-1",
        "path-2",
        "path-3",
    )


@pytest.mark.parametrize("ordered", [[], ["unknown-token-value"]])
def test_validator_rejects_empty_and_unknown_orders(ordered: list[str]) -> None:
    mapping, tokens = authorized(3)
    with pytest.raises(ImprovementError) as error:
        validate_improvement_proposal(tokens[:2], mapping, ordered)
    assert error.value.code == "invalid_improvement"


def test_validator_rejects_out_of_scope_token() -> None:
    mapping, tokens = authorized(3)
    outside = generate_tokens(1, token_source=token_factory(500))[0]
    with pytest.raises(ImprovementError):
        validate_improvement_proposal(tokens[:2], mapping, [tokens[0], outside])


def test_validator_rejects_duplicate_tokens() -> None:
    mapping, tokens = authorized(3)
    with pytest.raises(ImprovementError) as error:
        validate_improvement_proposal(tokens[:2], mapping, [tokens[0], tokens[0]])
    assert error.value.code == "invalid_improvement"


def test_validator_rejects_source_token_outside_the_request() -> None:
    mapping, tokens = authorized(3)
    outside = generate_tokens(1, token_source=token_factory(500))[0]
    with pytest.raises(ImprovementError):
        validate_improvement_proposal([tokens[0], outside], mapping, tokens[:2])


@pytest.mark.parametrize("bad", ["a" * 64, "A" * 16, "", "token", 12, None])
def test_validator_rejects_non_token_members(bad: object) -> None:
    mapping, tokens = authorized(3)
    with pytest.raises(ImprovementError):
        validate_improvement_proposal(tokens[:2], mapping, [tokens[0], bad])  # type: ignore[list-item]


def test_validator_rejects_additions_beyond_pool_cap() -> None:
    mapping, tokens = authorized(MIN_IMPROVEMENT_TRACKS + MAX_REPLACEMENT_CANDIDATES + 1)
    source = tokens[:MIN_IMPROVEMENT_TRACKS]
    additions = tokens[MIN_IMPROVEMENT_TRACKS:]
    assert len(additions) == MAX_REPLACEMENT_CANDIDATES + 1
    with pytest.raises(ImprovementError) as error:
        validate_improvement_proposal(source, mapping, [*source, *additions])
    assert "20" in str(error.value)


def test_validator_honors_explicit_addition_cap() -> None:
    mapping, tokens = authorized(4)
    source = tokens[:2]
    with pytest.raises(ImprovementError):
        validate_improvement_proposal(source, mapping, [tokens[0], tokens[2]], max_additions=0)
    assert validate_improvement_proposal(source, mapping, [tokens[0], tokens[2]], max_additions=1) == (
        "path-0",
        "path-2",
    )


def test_validator_rejects_result_below_minimum() -> None:
    mapping, tokens = authorized(3)
    with pytest.raises(ImprovementError) as error:
        validate_improvement_proposal(tokens[:2], mapping, [tokens[0]])
    assert error.value.code == "invalid_improvement"


def test_validator_rejects_oversized_result_and_source() -> None:
    mapping, tokens = authorized(MAX_DRAFT_TRACKS + 1)
    with pytest.raises(ImprovementError) as result_error:
        validate_improvement_proposal(tokens[:2], mapping, tokens)
    assert result_error.value.code == "ai_context_too_large"
    with pytest.raises(ImprovementError) as source_error:
        validate_improvement_proposal(tokens, mapping, tokens[:2])
    assert source_error.value.code == "ai_context_too_large"


def test_validator_honors_explicit_total_cap() -> None:
    mapping, tokens = authorized(6)
    with pytest.raises(ImprovementError):
        validate_improvement_proposal(tokens[:2], mapping, tokens[2:], max_total=3)
    assert validate_improvement_proposal(tokens[:2], mapping, tokens[2:], max_total=4) == (
        "path-2",
        "path-3",
        "path-4",
        "path-5",
    )


def test_validator_returns_resolved_paths_and_never_tokens() -> None:
    mapping, tokens = authorized(3)
    resolved = validate_improvement_proposal(tokens[:2], mapping, [tokens[1], tokens[2]])
    assert resolved == (mapping[tokens[1]], mapping[tokens[2]])
    assert all(not TOKEN_PATTERN.fullmatch(path) for path in resolved)


def test_manual_save_path_still_rejects_additions() -> None:
    with pytest.raises(ValueError):
        validate_edit(["a", "b"], ["a", "b", "c"])
    with pytest.raises(ValueError):
        validate_edit(["a", "b"], ["a", "a"])
    validate_edit(["a", "b"], ["b", "a"])


# --- I1.7 / I1.8 proposal binding, digest, and exact-order resolution ----------


def test_track_id_matches_the_renderer_public_identity() -> None:
    path = "/music/song.flac"
    assert track_id(path) == hashlib.sha256(path.encode("utf-8")).hexdigest()


def test_proposal_binds_session_revision_draft_order_and_resolved_order() -> None:
    paths = ["a", "b", "c"]
    candidate_set = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    tokens = list(candidate_set.draft_tokens)
    proposal = build_improvement_proposal(
        edit_id="edit-id",
        source_revision="revision",
        before_paths=paths,
        candidate_set=candidate_set,
        ordered_tokens=[tokens[1], tokens[2]],
    )
    assert str(UUID(proposal.proposal_id)) == proposal.proposal_id
    assert proposal.edit_id == "edit-id"
    assert proposal.source_revision == "revision"
    assert proposal.before_paths == ("a", "b", "c")
    assert proposal.after_paths == ("b", "c")
    assert proposal.source_tokens == tuple(tokens)
    assert proposal.order_tokens == (tokens[1], tokens[2])
    assert dict(proposal.candidates_by_token) == dict(candidate_set.paths_by_token)
    applied_ids = [track_id(path) for path in proposal.after_paths]
    assert proposal.draft_fingerprint == draft_fingerprint("edit-id", "revision", applied_ids)
    assert proposal.digest == proposal_digest(
        "edit-id",
        "revision",
        proposal.draft_fingerprint,
        proposal.before_paths,
        proposal.after_paths,
        proposal.candidates_by_token,
    )


def test_proposal_digest_is_deterministic_and_covers_every_binding() -> None:
    paths = ["a", "b", "c"]
    candidate_set = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    tokens = list(candidate_set.draft_tokens)

    def make(*, revision: str, order: list[str], before: list[str] = paths):
        return build_improvement_proposal(
            edit_id="edit-id",
            source_revision=revision,
            before_paths=before,
            candidate_set=candidate_set,
            ordered_tokens=order,
        )

    first = make(revision="r1", order=[tokens[0], tokens[1]])
    repeat = make(revision="r1", order=[tokens[0], tokens[1]])
    other_revision = make(revision="r2", order=[tokens[0], tokens[1]])
    other_order = make(revision="r1", order=[tokens[1], tokens[0]])
    other_before = make(revision="r1", order=[tokens[0], tokens[1]], before=["a", "b", "c", "d"])
    assert repeat.digest == first.digest
    assert repeat.proposal_id != first.proposal_id
    assert len({first.digest, other_revision.digest, other_order.digest, other_before.digest}) == 4
    assert first.draft_fingerprint != other_order.draft_fingerprint


def test_build_proposal_rejects_an_order_outside_the_authorized_set() -> None:
    paths = ["a", "b"]
    candidate_set = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    outside = generate_tokens(1, token_source=token_factory(500))[0]
    with pytest.raises(ImprovementError):
        build_improvement_proposal(
            edit_id="edit-id",
            source_revision="revision",
            before_paths=paths,
            candidate_set=candidate_set,
            ordered_tokens=[candidate_set.draft_tokens[0], outside],
        )


def test_proposal_digest_covers_the_authorized_token_map() -> None:
    paths = ["a", "b"]
    first_set = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    second_set = build_candidate_set(paths, records_for(paths), token_source=token_factory(100))

    def make(candidate_set):
        return build_improvement_proposal(
            edit_id="edit-id",
            source_revision="revision",
            before_paths=paths,
            candidate_set=candidate_set,
            ordered_tokens=list(candidate_set.draft_tokens),
        )

    first, second = make(first_set), make(second_set)
    assert first.after_paths == second.after_paths == ("a", "b")
    assert first.source_tokens != second.source_tokens
    assert first.digest != second.digest


def test_build_proposal_honors_an_explicit_identity() -> None:
    paths = ["a", "b"]
    candidate_set = build_candidate_set(paths, records_for(paths), token_source=token_factory())
    proposal = build_improvement_proposal(
        edit_id="edit-id",
        source_revision="revision",
        before_paths=paths,
        candidate_set=candidate_set,
        ordered_tokens=list(candidate_set.draft_tokens),
        proposal_id="chosen-identity",
    )
    assert proposal.proposal_id == "chosen-identity"
