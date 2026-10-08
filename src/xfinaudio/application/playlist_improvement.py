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

import hashlib
import json
import math
import secrets
from collections.abc import Callable, Collection, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from uuid import uuid4

from xfinaudio.library.models import TrackRecord
from xfinaudio.metadata.tempo import is_valid_bpm
from xfinaudio.recommendation.camelot import CamelotKey, parse_camelot_key

__all__ = [
    "MAX_CANDIDATES",
    "MAX_DRAFT_TRACKS",
    "MAX_REPLACEMENT_CANDIDATES",
    "MAX_TOKEN_LENGTH",
    "MIN_IMPROVEMENT_TRACKS",
    "ImprovementCandidate",
    "ImprovementCandidateSet",
    "ImprovementError",
    "ImprovementProposal",
    "build_candidate_set",
    "build_improvement_proposal",
    "draft_fingerprint",
    "generate_tokens",
    "proposal_digest",
    "track_id",
    "validate_improvement_proposal",
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


@dataclass(frozen=True)
class ImprovementCandidate:
    """One authorized candidate: an ephemeral token plus locally disclosed metadata."""

    token: str
    path: str
    title: str
    artist: str
    genre: str
    bpm: float | None
    camelot_key: str | None
    energy_level: int | None
    duration: float | None
    metadata_status: str
    missing_fields: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        """Return the bounded field set the provider may receive. Never includes the path."""
        return {
            "token": self.token,
            "title": self.title,
            "artist": self.artist,
            "genre": self.genre,
            "bpm": self.bpm,
            "key": self.camelot_key,
            "energy": self.energy_level,
            "duration": self.duration,
            "status": self.metadata_status,
            "missingFields": list(self.missing_fields),
        }


@dataclass(frozen=True)
class ImprovementCandidateSet:
    """Immutable request-scoped candidate set: draft tokens first, then pool tokens."""

    draft_tokens: tuple[str, ...]
    replacement_tokens: tuple[str, ...]
    candidates: tuple[ImprovementCandidate, ...]

    @property
    def tokens(self) -> tuple[str, ...]:
        return tuple(candidate.token for candidate in self.candidates)

    @property
    def candidates_by_token(self) -> Mapping[str, ImprovementCandidate]:
        return MappingProxyType({candidate.token: candidate for candidate in self.candidates})

    @property
    def paths_by_token(self) -> Mapping[str, str]:
        """The only local token-to-path resolution surface. Never disclosed."""
        return MappingProxyType({candidate.token: candidate.path for candidate in self.candidates})


@dataclass(frozen=True)
class ImprovementProposal:
    """A locally validated, exact-order proposal bound to one draft of one edit session.

    ``before_paths`` is the renderer draft order the provider saw; ``after_paths`` is the
    resolved validated order that a dedicated save may persist. ``source_revision`` binds
    the original saved playlist (including its original paths), and ``draft_fingerprint``
    binds the applied renderer draft order that the save must still match.
    """

    proposal_id: str
    edit_id: str
    source_revision: str
    draft_fingerprint: str
    before_paths: tuple[str, ...]
    after_paths: tuple[str, ...]
    source_tokens: tuple[str, ...]
    order_tokens: tuple[str, ...]
    candidates_by_token: Mapping[str, str]
    digest: str


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


def build_candidate_set(
    draft_paths: Sequence[str],
    records: Sequence[TrackRecord],
    *,
    include_replacements: bool = False,
    excluded_paths: Collection[str] = (),
    token_source: TokenSource | None = None,
) -> ImprovementCandidateSet:
    """Build the bounded authorized candidate set for one request from local state only.

    The draft is always authorized and is never truncated: a draft above
    ``MAX_DRAFT_TRACKS`` fails closed. Replacement candidates are opt-in, capped at
    ``MAX_REPLACEMENT_CANDIDATES``, exclude draft/excluded paths, exclude records whose
    disclosure-critical metadata is incomplete, and are ordered deterministically.

    A draft path with no local record fails closed: deriving a title from the path would
    leak path-derived text to the provider.
    """
    draft = _validated_draft(draft_paths)
    by_path = {record.path: record for record in records}
    draft_records = [_draft_record(path, by_path) for path in draft]
    replacements = (
        _select_replacements(records, draft_records, excluded=set(excluded_paths) | set(draft))
        if include_replacements
        else []
    )
    records_in_order = [*draft_records, *replacements]
    tokens = generate_tokens(len(records_in_order), token_source=token_source)
    candidates = tuple(_candidate(token, item) for token, item in zip(tokens, records_in_order, strict=True))
    split = len(draft_records)
    return ImprovementCandidateSet(
        draft_tokens=tokens[:split],
        replacement_tokens=tokens[split:],
        candidates=candidates,
    )


def validate_improvement_proposal(
    source: Sequence[str],
    authorized_tokens: Mapping[str, str],
    ordered: Sequence[str],
    *,
    max_total: int = MAX_DRAFT_TRACKS,
    max_additions: int = MAX_REPLACEMENT_CANDIDATES,
) -> tuple[str, ...]:
    """Validate an untrusted token-only order and resolve it to local paths.

    ``source`` is the ordered draft tokens, ``authorized_tokens`` is the local
    token-to-path map for this request, and ``ordered`` is the provider's proposed
    order. Every token must belong to the authorized set; duplicates, unknown or
    out-of-scope tokens, oversized lists, too many additions, and a result below
    ``MIN_IMPROVEMENT_TRACKS`` are all rejected. Returns the resolved ordered paths.
    """
    if not isinstance(authorized_tokens, Mapping):
        raise ImprovementError("invalid_improvement", "The authorized candidate set is missing.")
    if not source:
        raise ImprovementError("invalid_improvement", "The draft has no authorized candidates.")
    if not ordered:
        raise ImprovementError(
            "invalid_improvement",
            f"An improvement must keep at least {MIN_IMPROVEMENT_TRACKS} tracks.",
        )
    if len(source) > max_total or len(ordered) > max_total:
        raise ImprovementError("ai_context_too_large", f"A proposal cannot exceed {max_total} tracks.")
    for item in (*source, *ordered):
        if not _is_token(item):
            raise ImprovementError("invalid_improvement", "Only request-scoped tokens are accepted.")
    if len(set(ordered)) != len(ordered):
        raise ImprovementError("invalid_improvement", "The proposal repeats a track.")
    if len(set(source)) != len(source):
        raise ImprovementError("invalid_improvement", "The draft repeats a track.")
    if any(token not in authorized_tokens for token in source):
        raise ImprovementError("invalid_improvement", "The draft references a track outside this request.")
    if any(token not in authorized_tokens for token in ordered):
        raise ImprovementError(
            "invalid_improvement", "The proposal references a track outside the authorized candidates."
        )
    additions = [token for token in ordered if token not in set(source)]
    if len(additions) > max_additions:
        raise ImprovementError("invalid_improvement", f"At most {max_additions} replacement tracks are allowed.")
    if len(ordered) < MIN_IMPROVEMENT_TRACKS:
        raise ImprovementError(
            "invalid_improvement",
            f"An improvement must keep at least {MIN_IMPROVEMENT_TRACKS} tracks.",
        )
    return tuple(authorized_tokens[token] for token in ordered)


def track_id(path: str) -> str:
    """The renderer's public 64-hex track identity, derived from the path exactly like `_public_track`."""
    return hashlib.sha256(path.encode("utf-8")).hexdigest()


def draft_fingerprint(edit_id: str, source_revision: str, draft_ids: Sequence[str]) -> str:
    """Fingerprint one exact renderer draft order for a saved revision."""
    snapshot = [edit_id, source_revision, list(draft_ids)]
    return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False).encode()).hexdigest()


def proposal_digest(
    edit_id: str,
    source_revision: str,
    fingerprint: str,
    before_paths: Sequence[str],
    after_paths: Sequence[str],
    candidates_by_token: Mapping[str, str],
) -> str:
    """Digest every binding of an improvement proposal, including the sorted token map."""
    pairs = sorted((token, path) for token, path in candidates_by_token.items())
    snapshot = [
        edit_id,
        source_revision,
        fingerprint,
        list(before_paths),
        list(after_paths),
        [list(pair) for pair in pairs],
    ]
    return hashlib.sha256(json.dumps(snapshot, ensure_ascii=False).encode()).hexdigest()


def build_improvement_proposal(
    *,
    edit_id: str,
    source_revision: str,
    before_paths: Sequence[str],
    candidate_set: ImprovementCandidateSet,
    ordered_tokens: Sequence[str],
    proposal_id: str | None = None,
) -> ImprovementProposal:
    """Validate an untrusted token order and bind it to a session, draft, and digest.

    Only the request-scoped candidate set may resolve tokens to paths. The applied order
    fingerprint is derived from the resolved paths, so a later save can prove the renderer
    still holds exactly the order this proposal authorized.
    """
    ordered = validate_improvement_proposal(candidate_set.draft_tokens, candidate_set.paths_by_token, ordered_tokens)
    after_paths = tuple(ordered)
    candidates = candidate_set.paths_by_token
    fingerprint = draft_fingerprint(edit_id, source_revision, [track_id(path) for path in after_paths])
    digest = proposal_digest(edit_id, source_revision, fingerprint, before_paths, after_paths, candidates)
    return ImprovementProposal(
        proposal_id=str(uuid4()) if proposal_id is None else proposal_id,
        edit_id=edit_id,
        source_revision=source_revision,
        draft_fingerprint=fingerprint,
        before_paths=tuple(before_paths),
        after_paths=after_paths,
        source_tokens=tuple(candidate_set.draft_tokens),
        order_tokens=tuple(ordered_tokens),
        candidates_by_token=candidates,
        digest=digest,
    )


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


def _validated_draft(draft_paths: Sequence[str]) -> list[str]:
    if isinstance(draft_paths, (str, bytes)) or not isinstance(draft_paths, Sequence):
        raise ImprovementError("invalid_improvement", "Invalid draft track identities.")
    draft = list(draft_paths)
    if not draft:
        raise ImprovementError("invalid_improvement", "Open a saved playlist before requesting an improvement.")
    if len(draft) > MAX_DRAFT_TRACKS:
        raise ImprovementError(
            "ai_context_too_large",
            f"This draft has more than {MAX_DRAFT_TRACKS} tracks; no request was prepared.",
        )
    if any(not isinstance(path, str) or not path for path in draft):
        raise ImprovementError("invalid_improvement", "Invalid draft track identities.")
    if len(set(draft)) != len(draft):
        raise ImprovementError("invalid_improvement", "The draft contains duplicate tracks.")
    return draft


def _draft_record(path: str, by_path: Mapping[str, TrackRecord]) -> TrackRecord:
    record = by_path.get(path)
    if record is None:
        raise ImprovementError(
            "invalid_improvement", "Every draft track needs local metadata before requesting an improvement."
        )
    return record


def is_eligible_replacement(record: TrackRecord) -> bool:
    """A pool candidate must have complete, assessment-safe metadata. Incomplete ones are excluded."""
    if not isinstance(record.path, str) or not record.path:
        return False
    if not is_valid_bpm(record.bpm):
        return False
    if not isinstance(record.energy_level, int) or isinstance(record.energy_level, bool):
        return False
    if not 1 <= record.energy_level <= 10:
        return False
    if record.duration is None or not math.isfinite(record.duration) or record.duration <= 0:
        return False
    if not _key(record.camelot_key):
        return False
    return bool(record.title and record.title.strip()) and bool(record.artist and record.artist.strip())


def _key(value: str | None) -> CamelotKey | None:
    try:
        return parse_camelot_key(value or "")
    except (ValueError, AttributeError):
        return None


def _select_replacements(
    records: Sequence[TrackRecord],
    draft_records: Sequence[TrackRecord],
    *,
    excluded: Collection[str],
) -> list[TrackRecord]:
    eligible = [record for record in records if record.path not in excluded and is_eligible_replacement(record)]
    eligible.sort(key=lambda record: _replacement_key(record, draft_records))
    unique: dict[str, TrackRecord] = {}
    for record in eligible:
        unique.setdefault(record.path, record)
    return list(unique.values())[:MAX_REPLACEMENT_CANDIDATES]


def _replacement_key(record: TrackRecord, draft_records: Sequence[TrackRecord]) -> tuple[float, tuple[int, int], str]:
    """Deterministic proximity to the draft: tempo first, then harmonic distance, then path."""
    bpm_gap = _bpm_gap(record, draft_records)
    record_key = _key(record.camelot_key)
    gaps = [
        _harmonic_gap(record_key, draft_key)
        for draft in draft_records
        if (draft_key := _key(draft.camelot_key)) is not None and record_key is not None
    ]
    return (bpm_gap, min(gaps, default=(2, 0)), record.path)


def _bpm_gap(record: TrackRecord, draft_records: Sequence[TrackRecord]) -> float:
    """Smallest tempo distance to a draft with valid BPM; ``inf`` when none is usable."""
    if record.bpm is None or not is_valid_bpm(record.bpm):
        return math.inf
    gaps = [abs(record.bpm - draft.bpm) for draft in draft_records if draft.bpm is not None and is_valid_bpm(draft.bpm)]
    return min(gaps, default=math.inf)


def _harmonic_gap(left: CamelotKey, right: CamelotKey) -> tuple[int, int]:
    distance = min((left.number - right.number) % 12, (right.number - left.number) % 12)
    return (0 if left.letter == right.letter else 1, distance)


def _candidate(token: str, record: TrackRecord) -> ImprovementCandidate:
    return ImprovementCandidate(
        token=token,
        path=record.path,
        title=record.title or "",
        artist=record.artist or "",
        genre=record.genre or "",
        bpm=record.bpm,
        camelot_key=record.camelot_key,
        energy_level=record.energy_level,
        duration=record.duration,
        metadata_status=record.metadata_status,
        missing_fields=tuple(record.missing_required_fields),
    )
