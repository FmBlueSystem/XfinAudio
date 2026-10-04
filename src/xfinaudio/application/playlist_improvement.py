"""Request-scoped ephemeral tokens and bounded improvement candidate validation.

This is the pure local core of the AI playlist-improvement feature. It owns the
request-scoped token map, the bounded authorized candidate set (open draft plus an
optional replacement pool), and the dedicated token-only validator. It performs no I/O,
contacts no provider, and never mutates a playlist or an audio file.

The provider only ever sees ephemeral 16-hex pseudonyms; filesystem paths stay local and
are resolved exclusively through :meth:`ImprovementCandidateSet.paths_by_token` or the
mapping a caller passes to :func:`validate_improvement_proposal`.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable

__all__ = [
    "MAX_CANDIDATES",
    "MAX_DRAFT_TRACKS",
    "MAX_REPLACEMENT_CANDIDATES",
    "MAX_TOKEN_LENGTH",
    "MIN_IMPROVEMENT_TRACKS",
    "ImprovementError",
    "generate_tokens",
]

# 16 lowercase hex characters = 64 random bits, delivered as `secrets.token_hex(8)`.
MAX_TOKEN_LENGTH = 16
MAX_DRAFT_TRACKS = 80
MAX_REPLACEMENT_CANDIDATES = 20
MAX_CANDIDATES = MAX_DRAFT_TRACKS + MAX_REPLACEMENT_CANDIDATES
MIN_IMPROVEMENT_TRACKS = 2

# A collision is regenerated, never resolved first-wins. The bound only exists so a
# broken/constant token source fails closed instead of looping forever.
_TOKEN_ATTEMPTS = 64

_HEX_DIGITS = frozenset("0123456789abcdef")
TokenSource = Callable[[], str]


class ImprovementError(ValueError):
    """A local improvement input violated a bound, membership, or format rule.

    ``code`` lets the headless boundary map the failure onto its existing error codes
    (for example ``ai_context_too_large`` for an over-cap draft) without this pure
    module depending on the backend.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def generate_tokens(count: int, *, token_source: TokenSource | None = None) -> tuple[str, ...]:
    """Return ``count`` unique 16-hex tokens for one request only."""
    if type(count) is not int or count < 0 or count > MAX_CANDIDATES:
        raise ImprovementError("ai_context_too_large", f"At most {MAX_CANDIDATES} candidates can be authorized.")
    source = token_source or _random_token
    seen: set[str] = set()
    tokens: list[str] = []
    for _ in range(count):
        token = _unique_token(source, seen)
        seen.add(token)
        tokens.append(token)
    return tuple(tokens)


def _random_token() -> str:
    return secrets.token_hex(MAX_TOKEN_LENGTH // 2)


def _is_token(value: object) -> bool:
    return isinstance(value, str) and len(value) == MAX_TOKEN_LENGTH and set(value) <= _HEX_DIGITS


def _unique_token(source: TokenSource, seen: set[str]) -> str:
    for _ in range(_TOKEN_ATTEMPTS):
        token = source()
        if not _is_token(token):
            raise ImprovementError("invalid_improvement", "The token source produced an invalid token.")
        if token not in seen:
            return token
    raise ImprovementError("invalid_improvement", "Could not generate a unique request token.")
