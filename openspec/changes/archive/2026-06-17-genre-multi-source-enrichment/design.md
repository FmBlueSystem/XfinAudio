# Design: Genre Multi-Source Enrichment with a Consensus Judge

## Architecture overview

New capability lives in a dedicated package `src/xfinaudio/genre/`, sitting between `metadata`
(acquisition) and `library` (persistence), consumed by `recommendation` and `desktop`. It mirrors the
existing layered/screaming architecture and reuses the registry pattern from
`recommendation/strategies.py`.

```
metadata ──┐
           ▼
        genre/                      (NEW capability)
        ├── taxonomy.py             canonical taxonomy + crosswalk loader
        ├── normalizer.py           raw label -> canonical genre | unmapped
        ├── models.py               GenreCandidate, GenreDecision, GenreProvenance (frozen Pydantic)
        ├── providers/
        │   ├── base.py             GenreProvider protocol + registry
        │   ├── discogs.py          Discogs CC0-dump provider (offline)
        │   └── musicbrainz.py      MusicBrainz CC0 provider (throttled + cached)
        ├── judge.py                deterministic weighted-vote consensus
        ├── enrichment_service.py   orchestrates providers -> judge -> decision
        └── (optional) llm_judge.py local-LLM tie-breaker (PR7, deferred)
           ▼
        library/  (persist decision + provenance in SQLite; TrackRecord extended)
           ▼
   recommendation/ + library_health  (consume canonical genre)
           ▼
        desktop/  (surface canonical genre + confidence + sources)
```

Data assets (JSON, in-package so they ship in the wheel; loaded via `importlib.resources`; no PyYAML
dependency added):
```
src/xfinaudio/genre/data/
├── taxonomy.json      canonical genres + parent hierarchy (CC0)
└── crosswalk.json     {source_label -> canonical_genre} + aliases (CC0)
```
Rationale: hatch packages `src/xfinaudio`, so in-package JSON is guaranteed in the wheel; JSON is stdlib
(no new dependency); `importlib.resources.files("xfinaudio.genre")` is the robust load path.
Per-user cache (NOT in repo): app data dir, e.g. `discogs_dump.sqlite`, `musicbrainz_cache.sqlite`.

## Data model changes

All models frozen Pydantic v2 (`ConfigDict(frozen=True)`), honoring immutability.

New models in `genre/models.py`:

```python
class GenreCandidate(BaseModel):       # one source's vote
    canonical_genre: str               # canonical label or "unmapped"
    raw_label: str                     # original source label
    source: str                        # "discogs" | "musicbrainz" | ...
    confidence: float                  # [0, 1] source-internal certainty

class GenreProvenance(BaseModel):      # audit trail for a decision
    candidates: tuple[GenreCandidate, ...]
    source_trust: dict[str, float]     # trust prior per source used
    scores: dict[str, float]           # canonical_genre -> weighted score

class GenreDecision(BaseModel):
    primary: str | None                # decided canonical genre (None if no signal)
    top_n: tuple[str, ...]             # ranked canonical candidates above threshold
    confidence: float                  # [0, 1]
    low_confidence: bool
    provenance: GenreProvenance
```

`TrackRecord` (`library/models.py`) gains one optional field:
```python
genre_decision: GenreDecision | None = None   # canonical enrichment; raw `genre` stays untouched
```
Rationale: keep raw `genre` (file tag) authoritative-as-source; canonical lives separately so rollback
is trivial and original tags are never lost.

## SQLite persistence

`library/track_repository.py`: bump `SCHEMA_VERSION`, add one nullable column
`genre_decision_json TEXT`, serialize `GenreDecision` to JSON on upsert, deserialize on read.
Migration adds the column if absent (mirrors the spectral-profile migration pattern). Keyed by
absolute path, same as existing rows. No change to the `genre` column.

## Provider abstraction

`genre/providers/base.py`:
```python
class GenreProvider(Protocol):
    name: str
    def fetch(self, track: TrackRecord) -> list[GenreCandidate]: ...

# module-level registry mirroring recommendation/strategies.py
def register_provider(provider: GenreProvider) -> None: ...
def enabled_providers(settings: Settings) -> list[GenreProvider]: ...
```
Providers are constructed with their cache/config and registered. `enrichment_service` queries only
enabled providers, wraps each `fetch` in try/except (failure → empty list, logged), and feeds the
union of candidates to the judge.

### Discogs provider (CC0 dumps)

- Ingestion script/module parses the Discogs monthly XML dump, extracting per-release `artist`,
  `title`, and `styles` (the useful field; `genres` is coarse). Stream-parse (iterparse) to bound memory.
- Stores a compact lookup in the per-user cache `discogs_dump.sqlite`: index by normalized
  `(artist, title)` → list of canonical styles (crosswalk-resolved at ingestion time).
- `fetch()` looks up the track by normalized artist+title and returns canonical candidates,
  `source="discogs"`, confidence from style frequency/agreement within matched releases.
- Fully offline after ingestion. No live API in the core; if a live-API path is added later it writes
  only to the per-user cache, never repo assets (License posture).

### MusicBrainz provider (CC0)

- Queries `ws/2` with `inc=genres+tags`, `User-Agent` set, **hard 1 req/s throttle** (token-bucket),
  results cached in per-user `musicbrainz_cache.sqlite` keyed by entity/MBID or artist+title.
- Maps MB genres (curated) and selected tags (folksonomy, denoised via crosswalk whitelist + stoplist)
  to canonical candidates; confidence from MB vote ratio / tag count.
- Repeated lookups hit cache (Scenario 4.2). Network failure → empty candidates (isolated).

## Consensus judge

`genre/judge.py`, pure function, deterministic:

```
score(g) = Σ_source ( source_trust[source] × candidate.confidence )   for candidates with canonical_genre == g
```
- `source_trust` priors (config, defaults): `discogs_styles=1.0`, `musicbrainz_genres=0.9`,
  `musicbrainz_tags=0.5`. Tunable; later optionally replaced by Dawid–Skene estimates (PR8, deferred).
- `unmapped` candidates are excluded from scoring (tracked in provenance only).
- Rank canonical genres by score; `primary` = argmax; `top_n` = those above `min_score_threshold`.
- `confidence` = normalized top score (e.g., `top_score / Σ scores`), clamped to `[0, 1]`.
- `low_confidence = (top_score - second_score) < margin_threshold` OR total mass below a floor.
- Determinism: stable sort by `(-score, canonical_genre)`; no time/random/dict-order dependence.

Tie-break and thresholds are config constants so behavior is explicit and testable.

## Configuration

Extend `config/settings.py` with a `genre_enrichment` block (defaults conservative):
```
enabled: bool = False                 # whole feature opt-in
providers: {discogs: bool, musicbrainz: bool}
source_trust: {discogs_styles, musicbrainz_genres, musicbrainz_tags}
min_score_threshold: float
margin_threshold: float
llm_tiebreaker_enabled: bool = False  # PR7, deferred
```
Feature stays inert (no behavior change) until `enabled=True`, satisfying rollback simplicity.

## Integration points

- `recommendation/playlist_service.py` `_resolve_anchor_genre` / `_apply_genre_filter`: prefer
  `track.genre_decision.primary` when present, else fall back to raw `genre`. Single helper
  `effective_genre(track) -> str | None` to centralize the precedence.
- `recommendation/scoring.py`: tag-overlap genre component uses `effective_genre`.
- `library/library_health.py`: variant grouping operates on `effective_genre`.
- `desktop/`: library/review tables show canonical genre + a confidence/low-confidence badge and a
  sources tooltip (reuse `recommendation_presenter` + `table_populators` patterns).

## Affected files

| File | Change |
|---|---|
| `src/xfinaudio/genre/**` | NEW package (taxonomy, normalizer, models, providers, judge, enrichment service) |
| `src/xfinaudio/genre/data/taxonomy.json`, `crosswalk.json` | NEW CC0 data assets (in-package) |
| `src/xfinaudio/library/models.py` | Add `genre_decision` field to `TrackRecord` |
| `src/xfinaudio/library/track_repository.py` | Schema bump, `genre_decision_json` column, (de)serialize |
| `src/xfinaudio/library/scan_service.py` | Optional enrichment hook after metadata parse |
| `src/xfinaudio/config/settings.py` + repository | `genre_enrichment` settings block |
| `src/xfinaudio/recommendation/playlist_service.py`, `scoring.py` | `effective_genre` precedence |
| `src/xfinaudio/library/library_health.py` | variant grouping on canonical genre |
| `src/xfinaudio/desktop/**` | surface canonical genre + confidence + sources |
| `pyproject.toml`, `uv.lock` | pinned `musicbrainzngs`, `python3-discogs-client` (optional-import) |
| `NOTICE.md`, `docs/open-source-license.md` | document CC0 sources + license posture |

## Safety considerations

- **No audio mutation / no DSP / no fingerprinting**: enrichment is text-metadata only; track identity
  uses tags / artist+title / ISRC, never audio analysis.
- **GPL-3.0 license posture**: only CC0 assets shipped; restrictive-ToU data confined to per-user cache.
- **Immutable state**: all new models frozen; updates via `model_copy(update=...)`.
- **Optional deps**: providers import-guarded; missing `musicbrainzngs`/`discogs_client` → provider
  disabled, app still runs (mirrors librosa optionality).
- **Network discipline**: offline-first; MB throttled + cached; failures isolated per provider.
- **Determinism**: judge is pure and stable-sorted; no LLM in the default path.

## Rejected alternatives

- **Last.fm / Spotify / Deezer as data sources** — license-incompatible with GPL-3.0 redistribution
  (Last.fm NC + no-sublicense; Spotify/Deezer no-redistribution) and/or low granularity. Excluded.
- **AcoustID/Chromaprint fingerprinting** — runs an FFT (DSP); violates the no-DSP charter. Deferred to
  a separate governance decision.
- **LLM-as-primary judge** — non-deterministic and online; conflicts with offline/deterministic charter.
  Kept only as an opt-in local tie-breaker (PR7, deferred).
- **Overwriting raw `genre`** — would lose source-of-truth and complicate rollback; canonical is stored
  in a separate field instead.

## Deferred (documented, not in core delivery)

- **PR7 — local-LLM tie-breaker** (`genre/llm_judge.py`): only for `low_confidence`, local (Ollama/
  llama.cpp), `temperature=0`, cached by input hash, candidate-restricted, default off.
- **PR8 — Dawid–Skene trust calibration**: replace hand-tuned `source_trust` priors with EM estimates
  from a gold-labeled set; deterministic; default off until a gold set exists.
