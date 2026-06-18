# Apply Progress: Runtime Genre Providers (User-Keyed)

Status: all PRs complete; verified; ready to archive.

| PR | Slice | Status | Notes |
|---|---|---|---|
| PR1 | Settings extension + license posture docs | done | 8 new tests; GenreEnrichmentSettings + NOTICE.md |
| PR2 | Last.fm runtime provider | done | 11 new tests; pylast 5.5.0 dep |
| PR3 | Spotify runtime provider | done | 12 new tests; spotipy 2.26.0 dep |
| PR4 | Deezer runtime provider | done | 12 new tests; stdlib urllib (no new dep) |
| PR5 | UI for providers + LLM configuration | done | 7 new tests; SettingsDialog genre enrichment panel |
| PR6 | Local LLM tie-breaker (opt-in, default OFF) | done | 12 new tests; judge.decide_with_llm integration |

## TDD log

### PR1 (Tasks 1.1–1.3) — complete
- RED: `tests/genre/test_settings_extension.py` (6 tests) failed with missing attributes.
- GREEN:
  - `src/xfinaudio/genre/settings.py` — added `api_keys: dict[str, str]`, `llm_tiebreaker_enabled: bool = False`, `llm_tiebreaker_url: str` (default `http://localhost:11434/api/generate`), `llm_tiebreaker_model: str` (default `llama3`). Constants `DEFAULT_LLM_TIEBREAKER_URL` / `DEFAULT_LLM_TIEBREAKER_MODEL` exported.
  - `NOTICE.md` — documented runtime-only/user-keyed posture for Last.fm, Spotify, Deezer; opt-in/default-OFF for LLM tie-breaker.
- VERIFY: 8 new tests green (settings extension + license posture); full suite 995; coverage 89.89%; slice ruff/format/pyright clean.

### PR2 (Tasks 2.1–2.2) — complete
- RED: `tests/genre/test_lastfm_provider.py` (11 tests) failed with ModuleNotFoundError.
- GREEN: `src/xfinaudio/genre/providers/lastfm.py` — `LastfmProvider` with name="lastfm", per-user SQLite cache, graceful no-op without API key, top-tags denoised via `_TAG_STOPLIST`, injected `fetcher` callable for tests, import-guarded `pylast` for live mode.
- Dependency: `pylast >=5.2,<6.0` (5.5.0 installed).
- VERIFY: 11 new tests green; full suite 1006; coverage 89.85%; slice clean.

### PR3 (Tasks 3.1–3.2) — complete
- RED: `tests/genre/test_spotify_provider.py` (12 tests) failed.
- GREEN: `src/xfinaudio/genre/providers/spotify.py` — `SpotifyProvider` with name="spotify", per-user SQLite cache, even confidence split across N genres (no per-genre weight from Spotify), graceful no-op without credentials, Client Credentials flow via `spotipy` (import-guarded).
- Dependency: `spotipy >=2.23,<3.0` (2.26.0 installed).
- VERIFY: 12 new tests green; full suite 1018; coverage 89.85%; slice clean.

### PR4 (Tasks 4.1–4.2) — complete
- RED: `tests/genre/test_deezer_provider.py` (12 tests) failed.
- GREEN: `src/xfinaudio/genre/providers/deezer.py` — `DeezerProvider` with name="deezer", per-user SQLite cache, stdlib `urllib.request` (no new dependency), coarse top-level genre buckets mapped via crosswalk.
- Crosswalk: added `"dance": "Dance-Pop"` so Deezer's coarse "Dance" bucket collapses sensibly.
- VERIFY: 12 new tests green; full suite 1030; coverage 89.65%; slice clean.

### PR5 (Tasks 5.1–5.2) — complete
- RED: extended `tests/test_settings_dialog.py` (7 new tests) failed.
- GREEN:
  - `src/xfinaudio/desktop/settings_dialog.py` — `_build_genre_enrichment_group()` adds a QGroupBox with master enable, per-provider rows (toggle + QLineEdit with Password echo for API key), and an LLM sub-group (enable + URL + model).
  - `accept()` now emits updated `genre_enrichment` settings along with export and UI settings.
  - `_current_genre_settings()` reads widget state back into a `GenreEnrichmentSettings`.
- VERIFY: 7 new tests green; full suite 1037; coverage 89.76%; slice clean.

### PR6 (Tasks 6.1–6.3) — complete
- RED: `tests/genre/test_llm_tiebreaker.py` (12 tests) failed with ModuleNotFoundError on `llm_judge`.
- GREEN:
  - `src/xfinaudio/genre/llm_judge.py` — `LocalLlmTieBreaker` with stdlib `urllib.request` POST to Ollama-compatible `/api/generate`; `temperature=0`; response restricted to `top_n` (exact match + casefold fallback); in-memory + per-user SQLite cache keyed by SHA-256 of `(model, top_n)`.
  - `src/xfinaudio/genre/judge.py` — added `decide_with_llm(decision, tie_breaker)` helper. The deterministic judge remains the system of record; the LLM is invoked only when `low_confidence=True` and `top_n` is non-empty. On a valid pick, the decision's `primary` is replaced and `low_confidence` is cleared. On any failure/invalid response, the input decision is returned unchanged.
- VERIFY: 12 new tests green; full suite 1049; coverage 89.81%; slice ruff/format/pyright clean.

## SLICE SIZES

| PR | Lines (prod + test, approx) |
|---|---|
| PR1 | ~200 (settings + notice + 8 tests) |
| PR2 | ~400 (provider + 11 tests) |
| PR3 | ~350 (provider + 12 tests) |
| PR4 | ~350 (provider + 12 tests) |
| PR5 | ~250 (panel + 7 tests) |
| PR6 | ~400 (llm + 12 tests) |
| **Total** | **~1950** |

PR2/3/4/6 slightly over the soft 400-line budget; each is a self-contained provider/module. Cohesive slices.

## KEY DECISIONS

- **Inert by default**: every new feature (`api_keys`, LLM fields, providers) has a safe default. The app works with **no** provider and **no** LLM, identical to the previous change.
- **Per-user API keys**: stored in the user's `AppSettings` (JSON in app data dir, never in the repo). UI uses password-style inputs.
- **Per-user cache only**: provider responses live in per-user SQLite caches; the existing `test_genre_license_assets.py` was extended to assert no provider-derived data is committed.
- **LLM is opt-in**: `llm_tiebreaker_enabled = False` by default; the LLM is never invoked unless the user explicitly enables it. Even when enabled, it's restricted to the already-normalized `top_n` (never invents genres).
- **Local-only LLM**: default URL is `http://localhost:11434/api/generate` (Ollama). No cloud endpoint is ever contacted. Users can override the URL but the responsibility for the endpoint being local is theirs.
- **Deterministic judge stays the system of record**: `decide_with_llm` only *upgrades* a `low_confidence` decision; any failure (invalid response, network error, exception) leaves the deterministic decision in place.

## GOTCHAS

- The LLM tie-breaker needs **both** an in-memory cache and a disk cache. Tests pass `cache_path=None` to exercise the in-memory path; the disk path is exercised separately.
- The judge integration uses `TYPE_CHECKING` to avoid a runtime import cycle between `judge.py` and `llm_judge.py`.
- `decide_with_llm` is a separate function from `decide` to keep `decide` pure (no network side effects, fully deterministic). The enrichment service is the only caller that wires them together (in a follow-up; this change does not modify the enrichment service).
- Deezer's `genre_id_list` returns numeric ids; without a name lookup we accept the numeric form. The crosswalk + canonical taxonomy handle the rest. Coarse-genre mapping for "Dance" → "Dance-Pop" was added in this PR.
