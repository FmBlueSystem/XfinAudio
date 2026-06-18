"""Local LLM tie-breaker for the genre enrichment pipeline.

The tie-breaker is invoked only when:
  1. The user has explicitly enabled ``llm_tiebreaker_enabled`` in settings.
  2. The deterministic judge produced a ``low_confidence`` decision.
  3. ``top_n`` is non-empty.

It targets a local Ollama-compatible endpoint. The model's response is
restricted to the already-normalized ``top_n`` candidates; any output
outside the canonical taxonomy is rejected. ``temperature=0`` is set in
the request; the response is cached by the prompt hash for determinism
and offline-repeatability.

No cloud endpoint is ever contacted. The default URL is the local Ollama
default (``http://localhost:11434/api/generate``); users may override it
in settings but the responsibility for the endpoint being local is theirs.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from xfinaudio.genre.models import GenreDecision

DEFAULT_LLM_TIMEOUT_SEC = 10.0
_LLM_TEMPERATURE = 0.0

# A fetcher takes the prompt and returns the parsed JSON body.
LlmFetcher = Callable[[str], dict[str, Any]]


def _prompt_for(top_n: tuple[str, ...], model: str) -> str:
    candidates_text = "\n".join(f"- {g}" for g in top_n)
    return (
        "You are a music-genre tie-breaker. Pick the single best genre for a track "
        "from this candidate list. Reply with a JSON object with key 'response' whose "
        "value is EXACTLY one of the candidate strings (no extra text, no quotes inside).\n"
        f"Model: {model}\n"
        "Candidates:\n"
        f"{candidates_text}"
    )


def _cache_key(top_n: tuple[str, ...], model: str) -> str:
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    h.update(b"\x00")
    h.update("\x00".join(top_n).encode("utf-8"))
    return h.hexdigest()


def _parse_choice(body: dict[str, Any]) -> str | None:
    """Extract the model's choice from an Ollama response body.

    Ollama's ``/api/generate`` returns ``{"response": "..."}``. We accept the
    value as a string (after stripping quotes/whitespace) and return it.
    """
    raw = body.get("response")
    if raw is None:
        return None
    text = str(raw).strip()
    # Strip surrounding quotes if any
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        text = text[1:-1].strip()
    return text or None


class LocalLlmTieBreaker:
    """Local LLM tie-breaker for ``low_confidence`` genre decisions."""

    def __init__(
        self,
        *,
        url: str = "http://localhost:11434/api/generate",
        model: str = "llama3",
        fetcher: LlmFetcher | None = None,
        cache_path: Path | None = None,
        timeout_sec: float = DEFAULT_LLM_TIMEOUT_SEC,
    ) -> None:
        self._url = url
        self._model = model
        self._fetcher = fetcher
        self._cache_path = cache_path
        self._timeout = timeout_sec
        self._memory_cache: dict[str, str] = {}

    def break_tie(self, *, decision: GenreDecision) -> str | None:
        """Return the model's chosen canonical genre, or None on failure.

        The choice MUST be one of ``decision.top_n``; any other value is
        rejected. Results are cached on disk (when ``cache_path`` is set)
        and in memory for the lifetime of this instance.
        """
        if not decision.top_n:
            return None
        prompt = _prompt_for(decision.top_n, self._model)
        cache_key = _cache_key(decision.top_n, self._model)

        if cache_key in self._memory_cache:
            return self._validate(self._memory_cache[cache_key], decision.top_n)

        cached = self._cache_get(cache_key)
        if cached is not None:
            self._memory_cache[cache_key] = cached
            return self._validate(cached, decision.top_n)

        try:
            body = self._call(prompt)
        except Exception:
            return None
        chosen = _parse_choice(body)
        if chosen is None:
            return None
        validated = self._validate(chosen, decision.top_n)
        if validated is not None:
            self._memory_cache[cache_key] = validated
            self._cache_put(cache_key, validated)
        return validated

    # -- internals --------------------------------------------------------

    def _call(self, prompt: str) -> dict[str, Any]:
        if self._fetcher is not None:
            return self._fetcher(prompt)
        payload = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": _LLM_TEMPERATURE},
            }
        )
        req = urllib.request.Request(
            self._url,
            data=payload.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    @staticmethod
    def _validate(choice: str, top_n: tuple[str, ...]) -> str | None:
        """Accept the choice only if it is an exact match for one of top_n."""
        if choice in top_n:
            return choice
        # Casefold match as a fallback for lenient models
        lowered = choice.casefold()
        for candidate in top_n:
            if candidate.casefold() == lowered:
                return candidate
        return None

    # -- cache ------------------------------------------------------------

    _CACHE_SCHEMA = """
    CREATE TABLE IF NOT EXISTS llm_tiebreaker_cache (
        cache_key TEXT PRIMARY KEY,
        choice    TEXT NOT NULL,
        cached_at REAL NOT NULL
    )
    """

    def _open_cache(self) -> sqlite3.Connection:
        assert self._cache_path is not None
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._cache_path)
        conn.execute(self._CACHE_SCHEMA)
        return conn

    def _cache_get(self, cache_key: str) -> str | None:
        if self._cache_path is None:
            return None
        with self._open_cache() as conn:
            row = conn.execute(
                "SELECT choice FROM llm_tiebreaker_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
        return None if row is None else str(row[0])

    def _cache_put(self, cache_key: str, choice: str) -> None:
        if self._cache_path is None:
            return
        with self._open_cache() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO llm_tiebreaker_cache (cache_key, choice, cached_at) VALUES (?, ?, ?)",
                (cache_key, choice, time.time()),
            )
            conn.commit()


__all__ = [
    "DEFAULT_LLM_TIMEOUT_SEC",
    "LlmFetcher",
    "LocalLlmTieBreaker",
]
