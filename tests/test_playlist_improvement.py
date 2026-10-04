"""Request-scoped ephemeral tokens and bounded improvement candidate validation."""

from __future__ import annotations

import re

import pytest

from xfinaudio.application.playlist_improvement import (
    MAX_CANDIDATES,
    MAX_TOKEN_LENGTH,
    ImprovementError,
    generate_tokens,
)

TOKEN_PATTERN = re.compile(r"[0-9a-f]{16}")


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
