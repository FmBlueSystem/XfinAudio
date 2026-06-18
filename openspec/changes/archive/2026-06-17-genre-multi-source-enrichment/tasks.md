# Tasks: Genre Multi-Source Enrichment with a Consensus Judge

Ships as chained PRs. Each PR slice stays within the 400-line review budget and is independently
green. Strict TDD: RED → GREEN → REFACTOR → VERIFY per behavior-changing task. Feature stays inert
(`genre_enrichment.enabled = False`) until PR5 wiring, so no behavior regression lands early.

---

## PR1 — Canonical taxonomy + crosswalk + normalizer

Archive reconciliation note: PR1–PR6 checkboxes were mechanically marked complete during archive because
`apply-progress.md`, `verify-report.md`, and `state.yaml` prove all core implementation slices are done and
all verification gates passed. PR7/PR8 are optional deferred work and are closed as deferred, not implemented.

### Task 1.1 — Canonical taxonomy asset
- [x] Create `assets/genre/taxonomy.yaml` (CC0): canonical genres + parent hierarchy covering the core
      electronic tree (House/Techno/Trance/DnB + common subgenres).
- [x] RED: `tests/genre/test_taxonomy.py` asserts load + Scenario 1.4 coverage + `Tech House -> House`.
- [x] GREEN: `src/xfinaudio/genre/taxonomy.py` loader (`load_taxonomy`, `parent_of`, `is_canonical`).
- [x] REFACTOR: docstrings, typed return models.
- [x] VERIFY: `uv run pytest tests/genre/test_taxonomy.py -q`.

### Task 1.2 — Crosswalk + GenreNormalizer
- [x] Create `assets/genre/crosswalk.yaml` (CC0): `{raw_label -> canonical_genre}` + aliases.
- [x] RED: `tests/genre/test_normalizer.py` covers Scenarios 1.1–1.3 (map, alias/case variants, unmapped).
- [x] GREEN: `src/xfinaudio/genre/normalizer.py` `normalize(raw) -> str` (canonical or `UNMAPPED`).
- [x] REFACTOR: casefold/strip reuse; precompiled alias map.
- [x] VERIFY: normalizer tests pass.

### Task 1.3 — PR1 gate
- [x] VERIFY: full suite + pyright + ruff + coverage on touched modules.
- [x] Confirm slice ≤ 400 changed lines.

---

## PR2 — Provider registry + provenance models

### Task 2.1 — Genre models
- [x] RED: `tests/genre/test_models.py` asserts frozen models + field constraints (confidence in [0,1]).
- [x] GREEN: `src/xfinaudio/genre/models.py` `GenreCandidate`, `GenreProvenance`, `GenreDecision`.
- [x] VERIFY: model tests pass; pyright clean.

### Task 2.2 — Provider protocol + registry
- [x] RED: `tests/genre/test_provider_registry.py` covers Scenarios 2.1–2.3 with a fake provider
      (returns candidates, disabled skipped, failure isolated).
- [x] GREEN: `src/xfinaudio/genre/providers/base.py` `GenreProvider` protocol + `register_provider` +
      `enabled_providers` (mirror `recommendation/strategies.py`).
- [x] GREEN: `src/xfinaudio/config/settings.py` add `genre_enrichment` block (default disabled).
- [x] REFACTOR: keep registry symmetric with strategy registry.
- [x] VERIFY: registry + settings tests pass.

### Task 2.3 — PR2 gate
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR3 — Discogs provider (CC0 dump)

### Task 3.1 — Dump ingestion
- [x] RED: `tests/genre/test_discogs_ingest.py` with a small XML dump fixture → cache rows
      (artist+title → canonical styles), crosswalk-resolved at ingest.
- [x] GREEN: `src/xfinaudio/genre/providers/discogs.py` iterparse ingestion into per-user
      `discogs_dump.sqlite` (streamed, bounded memory).
- [x] REFACTOR: extract normalization of artist/title keys.
- [x] VERIFY: ingestion test passes.

### Task 3.2 — Discogs fetch (offline)
- [x] RED: `tests/genre/test_discogs_provider.py` covers Scenarios 3.1–3.2 (styles→canonical, offline).
- [x] GREEN: implement `DiscogsProvider.fetch` lookup + confidence from style agreement.
- [x] GREEN: import-guard `python3-discogs-client` (optional); provider disabled if missing.
- [x] VERIFY: provider tests pass with no network.

### Task 3.3 — Dependency + PR3 gate
- [x] DEFERRED: `python3-discogs-client` was not added; core delivery ships offline Discogs dump ingestion with stdlib XML parsing only.
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR4 — MusicBrainz provider (CC0)

### Task 4.1 — Throttle + cache
- [x] RED: `tests/genre/test_mb_provider.py` Scenario 4.2 (≤1 req/s via injectable clock/limiter;
      second lookup served from cache, no new request).
- [x] GREEN: token-bucket throttle + per-user `musicbrainz_cache.sqlite`.
- [x] VERIFY: throttle/cache tests pass.

### Task 4.2 — MB genres/tags → canonical
- [x] RED: Scenario 4.1 with a MB response fixture (genres + vote weights; tag denoise via
      crosswalk whitelist + stoplist).
- [x] GREEN: `MusicBrainzProvider.fetch` mapping + confidence from vote ratio / tag count.
- [x] GREEN: import-guard `musicbrainzngs` (optional); provider disabled if missing.
- [x] REFACTOR: share denoise/stoplist with normalizer.
- [x] VERIFY: provider tests pass.

### Task 4.3 — Dependency + PR4 gate
- [x] Add pinned `musicbrainzngs >=,<` to `pyproject.toml`; `uv lock`.
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR5 — Consensus judge + persistence + wiring

### Task 5.1 — Judge
- [x] RED: `tests/genre/test_judge.py` covers Scenarios 5.1–5.5 (agreement, conflict, low-confidence,
      determinism, empty).
- [x] GREEN: `src/xfinaudio/genre/judge.py` deterministic weighted vote → `GenreDecision`.
- [x] REFACTOR: stable sort, thresholds as named config constants.
- [x] VERIFY: judge tests pass.

### Task 5.2 — Enrichment service
- [x] RED: `tests/genre/test_enrichment_service.py` orchestrates fake providers → judge → decision,
      isolating a failing provider.
- [x] GREEN: `src/xfinaudio/genre/enrichment_service.py`.
- [x] VERIFY: service tests pass.

### Task 5.3 — Persistence
- [x] RED: `tests/library/test_track_repository.py` Scenarios 6.1–6.3 (round-trip, original tag
      preserved, re-enrichment replaces).
- [x] GREEN: add `genre_decision` to `TrackRecord`; bump `SCHEMA_VERSION`; add `genre_decision_json`
      column + migration; (de)serialize.
- [x] VERIFY: repository tests pass.

### Task 5.4 — Wire into scan + recommendation + health
- [x] RED: tests for `effective_genre` precedence in `scan_service`, `playlist_service`/`scoring`
      (Scenario 7.1) and `library_health` (Scenario 7.2).
- [x] GREEN: optional enrichment hook in `scan_service` (gated by `genre_enrichment.enabled`);
      `effective_genre` helper; consume canonical genre in recommendation + health.
- [x] REFACTOR: centralize precedence in one helper.
- [x] VERIFY: recommendation + health + scan tests pass.

### Task 5.5 — License posture + PR5 gate
- [x] RED: `tests/genre/test_license_assets.py` Scenarios 8.1–8.2 (only CC0 assets in repo; cache path
      is per-user, not repo).
- [x] GREEN: update `NOTICE.md` + `docs/open-source-license.md` (CC0 sources, posture).
- [x] VERIFY: full suite + pyright + ruff + coverage + `release_gate_check.py`. Slice ≤ 400 lines
      (split 5.3/5.4 into PR5a/PR5b if budget exceeded).

---

## PR6 — Desktop UI surfacing

### Task 6.1 — Presentation helpers
- [x] RED: tests for canonical-genre + confidence/low-confidence badge helper and sources tooltip text.
- [x] GREEN: extend `desktop/recommendation_presenter.py` / `table_populators.py` / `rendering.py`.
- [x] GREEN: show canonical genre + badge in library + review tables; sources in tooltip.
- [x] VERIFY: UI tests pass (PySide6 offscreen) or documented manual QA.

### Task 6.2 — PR6 gate
- [x] VERIFY: full suite + pyright + ruff + coverage. Slice ≤ 400 lines.

---

## PR7 — (DEFERRED, optional) Local-LLM tie-breaker

Flag-gated, default off. Only invoked on `low_confidence`. Out of core delivery; implement only after
PR5 lands and if requested.
- [x] DEFERRED: Scenario 9.1 (off by default) + 9.2 (candidate-restricted, no out-of-taxonomy genre).
- [x] DEFERRED: `genre/llm_judge.py`: local backend (Ollama/llama.cpp), `temperature=0`, cached by input hash.
- [x] DEFERRED: deterministic with fixed seed; default path unaffected.

---

## PR8 — (DEFERRED, optional) Dawid–Skene trust calibration

Default off; requires a gold-labeled set. Replaces hand-tuned `source_trust` with EM estimates.
- [x] DEFERRED: Build gold-label fixture; implement EM estimator; keep deterministic.
- [x] DEFERRED: judge stays deterministic; priors fall back when no gold set.

---

## Final verification (per PR and at chain completion)

- [x] `uv run pytest -q`
- [x] `uv run pyright src tests`
- [x] `uv run pytest --cov --cov-fail-under=70 -q`
- [x] `uv run ruff check .` and `uv run ruff format --check .`
- [x] `uv run python scripts/release_gate_check.py --run`
- [x] Confirm: no audio mutation, no DSP/fingerprinting, no Serato V2 writes, only CC0 assets shipped.
- [x] Update `apply-progress.md` and `verify-report.md`.
