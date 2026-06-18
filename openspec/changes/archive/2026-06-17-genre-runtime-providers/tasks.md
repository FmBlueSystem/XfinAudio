# Tasks: Runtime Genre Providers (User-Keyed)

Ships as chained PRs. Each PR slice stays within the 400-line review budget
(or just over for cohesion) and is independently green. Strict TDD:
RED → GREEN → REFACTOR → VERIFY per behavior-changing task. The whole
feature is **inert by default** — providers and LLM are off until the user
explicitly enables them.

---

## PR1 — Settings extension + license posture docs

### Task 1.1 — Settings extension
- [x] RED: `tests/genre/test_settings_extension.py` covers Scenarios 1.1-1.3
      (per-provider enable flag, per-provider API key, default-inert state).
- [x] GREEN: extend `GenreEnrichmentSettings` with `api_keys`, `llm_tiebreaker_enabled`,
      `llm_tiebreaker_url`, `llm_tiebreaker_model`. All defaults inert.
- [x] REFACTOR: docstrings explaining license posture per field.
- [x] VERIFY: settings tests pass; existing settings_repository round-trips
      without a schema bump (Pydantic auto-handles new optional fields).

### Task 1.2 — NOTICE.md update
- [x] RED: extend `test_genre_license_assets.py` to assert NOTICE.md mentions
      each new provider (Last.fm, Spotify, Deezer) and the LLM as
      runtime-only/user-keyed/opt-in.
- [x] GREEN: update `NOTICE.md` with the runtime-only posture for each new
      provider and the LLM opt-in.
- [x] VERIFY: license test passes.

### Task 1.3 — PR1 gate
- [x] VERIFY: full suite + pyright + ruff + coverage on touched modules.
- [x] Slice ≤ 400 changed lines.

---

## PR2 — Last.fm runtime provider

### Task 2.1 — Provider skeleton + cache
- [x] RED: `tests/genre/test_lastfm_provider.py` covers Scenarios 2.1-2.3
      (canonical candidates from top tags, cached second lookup, missing key
      returns no candidates without raising).
- [x] GREEN: `src/xfinaudio/genre/providers/lastfm.py` — `LastfmProvider` with
      `name = "lastfm"`, per-user SQLite cache (mirroring `MusicBrainzProvider`),
      throttle, graceful no-op when no key.
- [x] GREEN: parse `track.getTopTags(artist, title)` response into canonical
      candidates via `GenreNormalizer`; denoise via `_TAG_STOPLIST`.
- [x] REFACTOR: share denoise/stoplist with normalizer (same as MB).
- [x] VERIFY: provider tests pass.

### Task 2.2 — Dependency + PR2 gate
- [x] Add pinned `pylast >=lower,<upper` to `pyproject.toml`; `uv lock`.
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR3 — Spotify runtime provider

### Task 3.1 — Provider + cache
- [x] RED: `tests/genre/test_spotify_provider.py` covers Scenarios 3.1-3.2
      (canonical candidates from artist genres, missing credentials return
      no candidates without raising).
- [x] GREEN: `src/xfinaudio/genre/providers/spotify.py` — `SpotifyProvider`
      with `name = "spotify"`, per-user SQLite cache, Client Credentials
      flow via `spotipy` (import-guarded), search artist → fetch genres.
- [x] GREEN: graceful no-op when no client credentials.
- [x] VERIFY: provider tests pass with mocked spotipy.

### Task 3.2 — Dependency + PR3 gate
- [x] Add pinned `spotipy >=lower,<upper` to `pyproject.toml`; `uv lock`.
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR4 — Deezer runtime provider

### Task 4.1 — Provider + cache
- [x] RED: `tests/genre/test_deezer_provider.py` covers Scenarios 4.1-4.2
      (coarse top-level genre maps to canonical, coarse "Dance" collapses
      sensibly).
- [x] GREEN: `src/xfinaudio/genre/providers/deezer.py` — `DeezerProvider`
      with `name = "deezer"`, per-user SQLite cache, stdlib `urllib.request`
      against `api.deezer.com` (no new dependency), graceful no-op.
- [x] VERIFY: provider tests pass with mocked urllib.

### Task 4.2 — PR4 gate
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR5 — UI for providers + LLM configuration

### Task 5.1 — Settings dialog panel
- [x] RED: tests for the settings dialog's genre enrichment panel
      (per-provider toggles, password-style API key fields, LLM block).
- [x] GREEN: extend `desktop/settings_dialog.py` with a "Genre enrichment"
      group: per-provider toggle + API key input, LLM enable toggle + URL
      + model name. Default-inert.
- [x] VERIFY: UI tests pass (PySide6 offscreen) or documented manual QA.

### Task 5.2 — PR5 gate
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR6 — Local LLM tie-breaker (opt-in, default OFF)

### Task 6.1 — LLM client
- [x] RED: `tests/genre/test_llm_tiebreaker.py` covers Scenarios 6.1-6.4
      (off by default, restricted to taxonomy, deterministic + cached,
      targets local endpoint only).
- [x] GREEN: `src/xfinaudio/genre/llm_judge.py` — `LocalLlmTieBreaker` with
      stdlib `urllib.request` POST to the configured URL, `temperature=0`,
      response parsed as JSON, validated against `top_n` (exact match
      required), result cached by `(top_n, model)` hash.
- [x] GREEN: extend `judge.decide()` to call the tie-breaker when
      `settings.llm_tiebreaker_enabled` is `True` and the decision is
      `low_confidence` AND `top_n` is non-empty.
- [x] VERIFY: tie-breaker tests pass; deterministic judge behavior is
      preserved when the tie-breaker is disabled or absent.

### Task 6.2 — Protocol check
- [x] RED: provider protocol conformance test (Scenario 5.1) — all three
      new providers pass `isinstance(p, GenreProvider)`.
- [x] GREEN: confirmed in each provider's test file.
- [x] VERIFY: protocol test passes.

### Task 6.3 — License posture + PR6 gate
- [x] RED: extend `test_genre_license_assets.py` suspect patterns to include
      Last.fm/Spotify/Deezer indicators.
- [x] GREEN: ensure no provider-derived data is committed.
- [x] VERIFY: full suite + pyright + ruff + coverage + `release_gate_check.py`.
- [x] Slice ≤ 400 lines.

---

## Final verification (per PR and at chain completion)

- [x] `uv run pytest -q`
- [x] `uv run pyright src tests`
- [x] `uv run pytest --cov --cov-fail-under=70 -q`
- [x] `uv run ruff check .` and `uv run ruff format --check .`
- [x] `uv run python scripts/release_gate_check.py --run`
- [x] Confirm: no audio mutation, no DSP/fingerprinting, no Serato V2 writes,
      only CC0 assets shipped, providers and LLM all default OFF.
- [x] Update `apply-progress.md` and `verify-report.md`.
