# Apply Progress: Genre Multi-Source Enrichment

Status: all core PRs complete; verified; ready to archive.

| PR | Slice | Status | Notes |
|---|---|---|---|
| PR1 | Taxonomy + crosswalk + normalizer | done | 13 genre tests green; CC0 JSON assets ship in wheel; slice lint/format/pyright clean |
| PR2 | Provider registry + provenance models | done | 14 new tests green (27 total genre); +472 lines (slightly over soft 400; cohesive slice) |
| PR3 | Discogs provider (CC0 dump) | done | 13 new tests green (40 total genre); +468 lines (over soft 400; XML fixtures inflate test count) |
| PR4 | MusicBrainz provider (CC0) | done | 15 new tests green (55 total genre); +648 lines (372 prod + 276 test); musicbrainzngs 0.7.1 dep added |
| PR5 | Consensus judge + persistence + wiring | done | 43 new tests green (98 total genre); 969 total; +~1100 lines; track_repo schema v3→v4, NOTICE.md updated, effective_genre wired |
| PR6 | Desktop UI surfacing | done | 18 new tests green (116 total genre); 987 total; +~300 lines; rendering helpers + populator wiring |
| PR7 | Local-LLM tie-breaker (optional) | deferred | flag-gated, default off |
| PR8 | Dawid–Skene calibration (optional) | deferred | needs gold set |

## TDD log

### PR1 (Tasks 1.1–1.3) — complete
- RED: `tests/genre/test_taxonomy.py` (7) + `tests/genre/test_normalizer.py` (6) failed with ModuleNotFoundError.
- GREEN: added `src/xfinaudio/genre/{__init__,taxonomy,normalizer}.py` + CC0 `data/{taxonomy,crosswalk}.json`.
  - Decision: JSON-in-package (loaded via `importlib.resources`) instead of YAML → no PyYAML dependency; verified files ship in the wheel under `xfinaudio/genre/data/`.
  - Scope: electronic + general genres (per user gate).
- VERIFY: `uv run pytest tests/genre -q` → 13 passed. Full suite 884 passed. Coverage 89.7%.
  Slice `ruff check`/`ruff format --check`/`pyright` clean.
### PR2 (Tasks 2.1–2.3) — complete
- RED: `tests/genre/test_models.py` (6) + `tests/genre/test_provider_registry.py` (8) failed with ModuleNotFoundError.
- GREEN:
  - `src/xfinaudio/genre/models.py` — frozen `GenreCandidate` (confidence in [0,1]), `GenreProvenance`, `GenreDecision` (allows no-signal, low_confidence).
  - `src/xfinaudio/genre/providers/base.py` — `GenreProvider` Protocol (runtime_checkable), `GenreProviderRegistry` (register/get/available; duplicate → ValueError, mirrors `StrategyRegistry`), module-level `register_provider` + `enabled_providers(settings)`. Unknown provider names in settings are ignored.
  - `src/xfinaudio/genre/settings.py` — `GenreEnrichmentSettings` (enabled=False, providers={}, default source_trust priors, thresholds, llm_tiebreaker_enabled=False).
  - `src/xfinaudio/config/settings.py` — wired `genre_enrichment: GenreEnrichmentSettings` into `AppSettings` (backwards-compatible; settings_repository `model_validate`/`model_dump` handle the new optional field).
- VERIFY: `uv run pytest tests/genre -q` → 27 passed. Full suite 898 passed. Coverage 89.76%.
  Slice `ruff check`/`ruff format --check`/`pyright` clean. No root build/dist artifacts.
### PR3 (Tasks 3.1–3.3) — complete
- RED: `tests/genre/test_discogs_ingest.py` (6) + `tests/genre/test_discogs_provider.py` (7) failed with ModuleNotFoundError.
- GREEN:
  - `src/xfinaudio/genre/providers/discogs.py` — `ingest_discogs_dump(xml_path, cache_path) -> int` (streaming iterparse, releases without styles skipped, UNMAPPED styles filtered, INSERT OR IGNORE for idempotency, returns total row count in cache) + `DiscogsProvider(cache_path)` (Protocol-conforming, lookup by normalized (artist,title), confidence = count/total of matching releases per canonical style).
  - **No new dependency**: offline dump path uses stdlib `xml.etree.ElementTree` only; `python3-discogs-client` deferred to a future live-API slice (out of core scope per design).
  - Schema: `discogs_release_style(artist_norm, title_norm, canonical_style)` PK + lookup index; lookup keys via `_lookup_key` (casefold + non-alnum collapse) mirroring normalizer.
- VERIFY: 13 new tests green (40 total genre tests). Full suite 911 passed. Coverage 89.82%. Slice ruff/format/pyright clean. No root build/dist artifacts.
### PR4 (Tasks 4.1–4.3) — complete
- RED: `tests/genre/test_musicbrainz_provider.py` (15) failed with ModuleNotFoundError.
- GREEN:
  - `src/xfinaudio/genre/providers/musicbrainz.py` — `MBGenreTag`, `MBResponse` frozen dataclasses, `ThrottledFetcher` (injectable clock + sleep, min_interval_sec=1.0 default), `MusicBrainzProvider` (Protocol-conforming, per-user SQLite cache, source='musicbrainz_genres' for genres + 'musicbrainz_tags' for tags, denoised via `_TAG_STOPLIST`, confidence = votes/total combined across genres+tags per canonical), `make_live_fetcher` (import-guarded, uses `musicbrainzngs.search_recordings` + `get_recording_by_id` with `inc=genres,tags`).
  - Schema: `mb_lookup(artist_norm, title_norm, payload_json, cached_at)` PK; `_open_cache()` helper creates parent dir + schema on demand so cache_get works against a fresh path.
  - Crosswalk: added `"electronic": "Electronica"` alias (MB uses lowercase "electronic" as a curated genre; resolves to the canonical "Electronica").
  - Dependency: `musicbrainzngs >=0.7,<1.0` added to `pyproject.toml`; `uv lock` resolved 0.7.1.
- VERIFY: 15 new tests green (55 total genre). Full suite 926 passed. Coverage 89.74%. Slice ruff/format/pyright clean. No root build/dist artifacts.
- SLICE SIZE: +648 lines (372 prod + 276 test). Throttle + cache + provider + live fetcher is a lot; production code is tight.
### PR5 (Tasks 5.1–5.5) — complete
- RED: 43 new tests across `test_judge.py` (10), `test_enrichment_service.py` (6), `test_effective_genre.py` (4), `test_genre_persistence.py` (7), `test_genre_health_integration.py` (3), `test_genre_playlist_integration.py` (3), `test_genre_scan_integration.py` (4), `test_genre_license_assets.py` (7). All failed initially.
- GREEN:
  - `src/xfinaudio/genre/judge.py` — `decide(candidates, settings) -> GenreDecision`. Weighted vote `score(g) = Σ trust×conf`; primary = argmax; `top_n` = ordered above `min_score_threshold`; `confidence` = primary/total in [0,1]; `low_confidence` on thin margin or low total mass; deterministic stable sort. Filters `UNMAPPED` candidates from scores but keeps them in provenance.
  - `src/xfinaudio/genre/enrichment_service.py` — `EnrichmentService(providers, settings, judge=decide)`. `enrich(track)` no-ops when disabled; isolates provider exceptions; aggregates candidates before judging.
  - `src/xfinaudio/genre/effective_genre.py` — centralized precedence: canonical primary when present, else raw `track.genre`. Used by library_health, playlist_service, scoring.
  - `src/xfinaudio/library/models.py` — added `genre_decision: GenreDecision | None` to `TrackRecord` (frozen Pydantic).
  - `src/xfinaudio/library/track_repository.py` — bumped `SCHEMA_VERSION` 3 → 4; added `genre_decision_json TEXT` column; `ALTER TABLE` migration preserves existing v3 DBs; `_serialize_decision`/`_deserialize_decision` use Pydantic's `model_dump_json`/`model_validate_json`.
  - `src/xfinaudio/library/scan_service.py` — added optional `enrichment_service: EnrichmentService | None = None` parameter to `scan_folder` and `MetadataScanService.scan`; `_enrich_records` attaches decisions via `model_copy(update=...)` only when the service emits a usable decision (primary or top_n). Original file tags are never overwritten.
  - `src/xfinaudio/library/library_health.py` — genre variant detection now uses `effective_genre` so enriched libraries collapse onto canonical.
  - `src/xfinaudio/recommendation/playlist_service.py` — `_normalized_genre` now uses `effective_genre` (precedence documented). same_genre strategy benefits automatically.
  - `src/xfinaudio/recommendation/scoring.py` — `_normalized_tags` uses `effective_genre` for the tag-overlap component.
  - `src/xfinaudio/genre/settings.py` — renamed `source_trust` default key `discogs_styles` → `discogs` to match the candidate source name.
  - `NOTICE.md` — documented CC0 source posture, per-source transparency, and explicit exclusion of Last.fm/Spotify/Deezer/AcoustID. `musicbrainzngs` added to review-cavities list.
  - `src/xfinaudio/genre/data/crosswalk.json` — added `"electronic": "Electronica"` (MB uses lowercase; required for MB fixtures).
  - `tests/test_track_repository.py` — updated `test_track_repository_migrates_v1_database_to_v3` to assert `user_version == SCHEMA_VERSION` (now 4) instead of hard-coded 3.
- VERIFY: 43 new tests green (98 total genre). Full suite 969 passed. Coverage 89.83%. Slice ruff/format/pyright clean. No root build/dist artifacts.
- SLICE SIZE: ~1100 lines (prod + test). Schema migration is a non-trivial persistent change. Splitting into PR5a (judge+service) and PR5b (persistence+wiring) would have been cleaner; ship as one for momentum.
- KEY DECISIONS:
  - Decision only attached to TrackRecord when service returns primary or top_n (avoids polluting records with empty decisions).
  - `effective_genre` is the single precedence rule; recommendation/health/scoring all import from it.
  - Schema migration uses `contextlib.suppress(sqlite3.OperationalError)` per existing pattern; safe for in-place upgrade.
### PR6 (Tasks 6.1–6.2) — complete
- RED: 18 new tests across `test_genre_ui_helpers.py` (15 pure, no Qt) and `test_table_populators.py` (3 Qt offscreen). All failed initially.
- GREEN:
  - `src/xfinaudio/desktop/rendering.py` — added `format_genre_decision`, `format_genre_badge` (🎯 high / 🟡 med / ❓ low with confidence value), `format_genre_cell` (combined: canonical + badge), `format_genre_sources_tooltip` (multi-line: Canonical, Confidence, Low confidence, Top-N, Scores, Sources). All pure (no Qt), importable in tests without a QApplication.
  - `src/xfinaudio/desktop/table_populators.py` — `populate_library_table` gained two optional callbacks: `format_genre_cell` (replaces the raw `record.genre` text in the genre column) and `format_genre_tooltip` (sets the genre cell's hover tooltip). Both default to the pre-enrichment behavior, so the existing table populator test still passes.
  - `src/xfinaudio/desktop/main_window.py` — `_populate_track_table` now passes `format_genre_cell=format_genre_cell` and `format_genre_tooltip=format_genre_sources_tooltip` to `populate_library_table`. Library table now shows the canonical (enriched) genre + confidence badge, with the sources tooltip on hover.
- VERIFY: 18 new tests green (116 total genre). Full suite 987 passed. Coverage 89.88%. Slice ruff/format/pyright clean. No root build/dist artifacts.
- SLICE SIZE: +~300 lines (helpers + populator wiring + tests). Tight and focused.
- KEY DECISIONS:
  - Badge is single-string (canonical + confidence value), not a separate widget — keeps the table simple, survives user-scaling.
  - `format_genre_cell` and `format_genre_tooltip` are **optional** callbacks with safe defaults; backward-compatible with the existing populator contract.
  - No new column added to the library table — the existing genre column carries both text and tooltip, no schema impact on the table headers.
  - Sources tooltip is plain text (newlines) — Qt renders it correctly on hover.
