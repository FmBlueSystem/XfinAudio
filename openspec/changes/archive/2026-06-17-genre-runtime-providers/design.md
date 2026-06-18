# Design: Runtime Genre Providers (User-Keyed)

## Architecture overview

The new providers slot into the existing `xfinaudio.genre` capability
without changing its public surface. The new LLM tie-breaker is a separate
module that the existing `decide()` judge calls only when configured and
the decision is `low_confidence`.

```
config/settings.py
    └── GenreEnrichmentSettings  (extended)
        ├── enabled, providers, source_trust (existing)
        ├── api_keys: dict[str, str]              (NEW)
        └── llm_tiebreaker_enabled, llm_tiebreaker_url, llm_tiebreaker_model  (NEW)

xfinaudio/genre/
    ├── providers/
    │   ├── lastfm.py           (NEW)  Last.fm runtime provider
    │   ├── spotify.py          (NEW)  Spotify runtime provider
    │   ├── deezer.py           (NEW)  Deezer runtime provider
    │   └── base.py             (unchanged)
    ├── llm_judge.py            (NEW)  Opt-in local LLM tie-breaker
    ├── judge.py                (extended to call llm_judge when configured)
    └── enrichment_service.py   (unchanged)
```

## Settings extension

`GenreEnrichmentSettings` gains three new fields, all default-inert:

```python
class GenreEnrichmentSettings(BaseModel):
    # ... existing fields ...
    api_keys: dict[str, str] = Field(default_factory=dict)
    llm_tiebreaker_enabled: bool = False
    llm_tiebreaker_url: str = "http://localhost:11434/api/generate"
    llm_tiebreaker_model: str = "llama3"
```

The settings_repository (JSON persistence) handles the new fields via
the existing `model_validate` / `model_dump(mode="json")` round-trip — no
schema bump required.

## Provider pattern (Last.fm / Spotify / Deezer)

All three follow the same skeleton, mirrored from the existing
`MusicBrainzProvider`:

- `name = "lastfm" | "spotify" | "deezer"`
- Constructor takes the API key (or empty) and a `cache_path: Path | None`.
- `fetch(track)`:
  1. If no API key → return `[]` (graceful no-op).
  2. Check per-user SQLite cache by `(artist_norm, title_norm)`; if hit, return cached.
  3. Call the provider API (import-guarded library), throttled.
  4. Parse the response into `GenreCandidate` objects, mapping raw labels
     through the existing `GenreNormalizer` (which already runs against the
     canonical taxonomy and crosswalk).
  5. Store in the cache.
  6. Return the candidates.

### Last.fm

- Library: `pylast` (BSD-3) — `LastFMNetwork` with the user's API key.
- Endpoint used: `track.getTopTags(artist, title)` returns a list of
  `(tag_name, count)` tuples (count 0–100).
- Throttle: 1 req/s (Last.fm public service default).
- Stoplist: reuse the existing `_TAG_STOPLIST` from the MB provider.
- Source name: `"lastfm"`.

### Spotify

- Library: `spotipy` (BSD-3) — `SpotifyClientCredentials` flow (no user
  OAuth required for read-only catalog access).
- Endpoint used: `sp.search(q=artist+title, type="track", limit=1)` →
  `track["artists"][0]["id"]` → `sp.artist(artist_id)["genres"]`.
- Throttle: Spotify rate limits are generous; respect the client's
  built-in `requests_timeout` and retry policy; mirror the cache-first
  pattern.
- Source name: `"spotify"`.

### Deezer

- Library: stdlib `urllib.request` (no new dependency).
- Endpoint used: `https://api.deezer.com/search?q=artist+title` →
  first result's `artist.id` → `https://api.deezer.com/artist/{id}` →
  top-level `name` of the first genre in the artist's `genre_id` chain.
- No auth needed for catalog search.
- Throttle: Deezer allows 50 req / 5s; cache-first makes this comfortable.
- Source name: `"deezer"`.

## LLM tie-breaker

```python
class LocalLlmTieBreaker:
    def __init__(self, *, url: str, model: str, cache_path: Path | None = None):
        ...
    def break_tie(self, decision: GenreDecision, top_n: tuple[str, ...]) -> str | None:
        """Return one of top_n chosen by the local model, or None on failure.
        
        The model is prompted with the top_n candidates and asked to pick one.
        The response is validated: it must be an exact match in top_n.
        Result is cached by (top_n, model) hash for determinism.
        """
        ...
```

Integration with the judge:

```python
def decide(candidates, settings) -> GenreDecision:
    decision = _core_decide(candidates, settings)
    if (
        decision.low_confidence
        and settings.llm_tiebreaker_enabled
        and decision.top_n
    ):
        chosen = _llm_tiebreaker.break_tie(decision, decision.top_n)
        if chosen is not None:
            decision = decision.model_copy(update={"primary": chosen, "low_confidence": False})
    return decision
```

This keeps the deterministic judge as the source of truth and only
**upgrades** the decision when the user opts in AND the model returns a
valid choice. The LLM is never required for the app to function.

### Safety

- `temperature=0` in the request payload.
- Response is parsed as JSON, validated against `top_n` (must be exact match).
- Any parse error, validation error, or HTTP error → return `None` →
  the deterministic decision stands.
- The model is **never** asked to invent genres; it's asked to pick from
  the already-normalized `top_n` list.
- No cloud endpoint is ever contacted; the URL is user-configured and
  defaults to local Ollama.

## Affected files

| File | Change |
|---|---|
| `src/xfinaudio/genre/settings.py` | Add `api_keys`, LLM fields |
| `src/xfinaudio/genre/providers/lastfm.py` | NEW |
| `src/xfinaudio/genre/providers/spotify.py` | NEW |
| `src/xfinaudio/genre/providers/deezer.py` | NEW |
| `src/xfinaudio/genre/llm_judge.py` | NEW |
| `src/xfinaudio/genre/judge.py` | Optional LLM tie-break branch |
| `src/xfinaudio/desktop/settings_dialog.py` | Genre enrichment panel (UI) |
| `src/xfinaudio/desktop/rendering.py` | None (no display change in this change) |
| `pyproject.toml`, `uv.lock` | Pin `pylast`, `spotipy` |
| `NOTICE.md` | License posture update |
| `tests/genre/test_settings_extension.py` | NEW |
| `tests/genre/test_lastfm_provider.py` | NEW |
| `tests/genre/test_spotify_provider.py` | NEW |
| `tests/genre/test_deezer_provider.py` | NEW |
| `tests/genre/test_llm_tiebreaker.py` | NEW |
| `tests/genre/test_genre_license_assets.py` | Extend with Last.fm/Spotify/Deezer patterns |

## Safety considerations

- **No audio mutation / no DSP** — enrichment remains text-metadata only.
- **GPL-3.0 posture** — no provider data ever ships in repo assets; runtime
  data lives in per-user cache; API keys are stored in the user's local
  settings JSON (not in the repo).
- **LLM opt-in** — `llm_tiebreaker_enabled = False` by default; app works
  perfectly without it.
- **Determinism** — judge is pure; LLM tie-breaker is cached; same inputs
  → same outputs.
- **Optional deps** — `pylast` and `spotipy` are pinned with upper bounds;
  providers are import-guarded; missing deps → provider disabled (matches
  the existing `DiscogsProvider` and `MusicBrainzProvider` patterns).
- **Per-provider isolation** — provider exceptions are caught by the
  existing `EnrichmentService` (no change needed).
- **API key handling** — keys live in `AppSettings` which is persisted to
  the user's app data dir (not the repo). UI uses password-style inputs.

## Rejected alternatives

- **Cloud LLM providers (OpenAI, Anthropic)** — rejected for online
  dependency and ToS friction. Local only.
- **LLM-as-primary judge** — rejected for non-determinism. Tie-breaker only.
- **Last.fm / Spotify / Deezer data embedded in repo** — rejected for
  license incompatibility. Runtime + user key only.
- **Live Discogs API** — rejected for marginal benefit over the CC0 dump;
  deferred.
- **Automatic key acquisition** — out of scope; user must bring their key.

## Chained PRs

| PR | Slice | Lines (est.) |
|---|---|---|
| PR1 | Settings extension + license posture | ~150 |
| PR2 | Last.fm provider | ~350 |
| PR3 | Spotify provider | ~300 |
| PR4 | Deezer provider | ~250 |
| PR5 | UI for providers + LLM configuration | ~300 |
| PR6 | Local LLM tie-breaker (opt-in) | ~300 |

Each PR stays within the 400-line soft budget (or just over for cohesion,
matching the pattern from the previous change).
