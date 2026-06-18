# Proposal: Genre Multi-Source Enrichment with a Consensus Judge

## Intent

Replace XfinAudio's single-source, free-text genre (read only from local Mixed In Key / ID3 tags)
with a **multi-source genre enrichment pipeline** that normalizes labels onto a **canonical
DJ-oriented taxonomy** and resolves conflicts with a **deterministic consensus judge**.

The pipeline reads genre/style signals from external metadata providers, maps every raw label
onto a single canonical vocabulary, and a weighted-vote judge decides the canonical genre(s) per
track with an explicit confidence and full provenance (which source said what).

This is a **metadata-enrichment** feature only. It does **not** mutate audio, does **not** do DSP,
and keeps all redistributable data under licenses compatible with the project's GPL-3.0-only charter.

## Motivation

- Today genre is `genre: str | None` read only from file tags (`metadata/mixedinkey_contract.py`),
  stored as free text (`library/models.py:26`). Quality depends entirely on how the user tagged files.
- Untagged or inconsistently tagged libraries get no genre signal, which weakens the `same_genre`
  recommendation strategy (`recommendation/playlist_service.py`) and `library_health` variant detection.
- The archived `genre-stability-routing` change explicitly deferred **"genre category vs specific
  genre disambiguation"** — that gap is exactly what a canonical taxonomy + judge closes.
- DJs think in Beatport-style genres (Tech House, Melodic House & Techno, Peak Time Techno...).
  A canonical taxonomy lets the app speak the DJ's language regardless of how the source labeled it.

## Scope

### In scope

- **Canonical taxonomy** (Beatport-style DJ vocabulary) as a versioned in-repo asset, with a hierarchy
  (`Tech House -> House`) and a **crosswalk** table mapping raw source labels onto canonical genres.
- **Genre normalization**: deterministic mapping of any raw label (casefold, alias, crosswalk) to a
  canonical genre or `unmapped`.
- **Provider abstraction**: a registry-based `GenreProvider` interface (mirrors the existing
  `recommendation/strategies.py` registry pattern). Providers are opt-in and individually toggleable.
- **Discogs provider** sourced from the **CC0 monthly data dumps** (offline ingestion) — primary
  electronic-subgenre signal. Live API lookups, if added, are runtime-only and never redistributed.
- **MusicBrainz provider** using CC0 core genre/tag data (API with 1 req/s throttle and local cache,
  or local mirror) — structured, weighted cross-validation signal.
- **Consensus judge**: deterministic weighted vote per canonical genre,
  `score(g) = Σ_source (source_trust × source_confidence × present)`, emitting top-N genres above a
  threshold plus a `low_confidence` flag when the #1/#2 margin is thin.
- **Provenance**: persist per-source candidate sets and the judge decision (evolve the existing
  `source_fields` primitive in `library/models.py:30`).
- **Persistence**: store enriched canonical genre, confidence, and provenance in the app-owned SQLite
  DB (`library/track_repository.py`), keyed by absolute path. Original file tags are never overwritten.
- **Integration**: feed canonical genre into `recommendation` (`same_genre`, scoring) and
  `library_health` variant detection; surface canonical genre + confidence + sources in the desktop UI.
- **Optional local LLM tie-breaker** (behind a flag, default off): only for `low_confidence` cases,
  run locally (Ollama/llama.cpp), `temperature=0` + cached, choosing only among already-normalized
  candidates — never inventing genres outside the canonical taxonomy.

### Out of scope

- Any audio mutation, audio rendering, mixing, time-stretching, pitch-shifting.
- Any DSP / waveform analysis for genre (no genre-from-audio inference, no BPM/key/beat detection).
- Audio **fingerprinting** (AcoustID/Chromaprint) — it runs an FFT (DSP) and needs a separate
  governance decision; track identity uses existing tags / artist+title / ISRC heuristics instead.
- Last.fm, Spotify, Deezer as **redistributed** data sources (license-incompatible with GPL-3.0;
  see License posture). They may be revisited later strictly as runtime-only, user-keyed signals.
- Writing genre back to audio files or to Serato Database V2.
- Bulk shipping of any provider dataset inside the app binary beyond CC0-licensed crosswalk assets.

## License posture (decisive constraint)

The project is **GPL-3.0-only**, which forbids field-of-use restrictions on redistributed data.

| Source | Redistributable under GPL-3.0? | Use |
|---|---|---|
| Discogs **monthly dumps** | Yes — CC0 | Primary provider (offline ingestion) |
| Discogs **API** | No — restrictive ToU | Runtime-only lookups, never cached into shipped data |
| MusicBrainz **core** genre/tags | Yes — CC0 | Secondary provider (API + cache or local mirror) |
| MB Live Data Feed / supplementary | No — CC BY-NC-SA | Not used |
| Last.fm / Spotify / Deezer | No — NC / no-redistribution | Excluded from scope |

Rule: anything embedded in the distributed app/dataset must be CC0 (or otherwise GPL-3.0 compatible).
Provider responses under restrictive ToU stay in a per-user local cache, never in repo assets.

## Arbor analysis

Treat the design as a hypothesis tree and refine toward the best route.

### Hypothesis branches

| Branch | Route | Impact | Risk | Cost | License |
|---|---|---|---|---|---|
| S1 | Single best source (Discogs only) | Medium | Low | Low | Clean (CC0 dumps) |
| S2 | Multi-source + canonical taxonomy + judge | High | Medium | High | Clean if CC0-only |
| S3 | Multi-source incl. Last.fm/Spotify for richness | High | High | High | **Incompatible** |
| J1 | Deterministic weighted vote | High | Low | Low | n/a |
| J2 | Dawid–Skene EM trust calibration | High | Medium | Medium | n/a (needs gold set) |
| J3 | LLM-as-judge as primary | Medium | High (non-determinism, online) | High | n/a |
| T1 | Free-text genre (status quo) | Low | Low | Low | n/a |
| T2 | Canonical taxonomy + crosswalk asset | High | Low | Medium | Clean (CC0 asset) |

### Refinement

- Eliminate **S3** and **J3-as-primary**: license incompatibility and non-determinism/online dependency
  conflict with the GPL-3.0 + offline charter.
- Eliminate **T1**: free-text is the problem we are solving.
- Adopt **S2 + J1 + T2** as the spine. Keep **J2** as an optional, deterministic calibration once a
  gold-labeled set exists. Keep an LLM only as an **opt-in local tie-breaker** for low-confidence cases.

### Best route: S2 + T2 + J1 (+ optional J2, optional local-LLM tie-breaker)

1. Canonical taxonomy + crosswalk asset (T2).
2. Provider abstraction + Discogs (CC0 dumps) + MusicBrainz (CC0) providers (S2).
3. Deterministic weighted-vote judge with provenance + confidence (J1).
4. Optional EM trust calibration (J2) and optional local-LLM tie-breaker — both deferred, flag-gated.

## Delivery: chained PRs

Estimated total well exceeds the 400-line review budget, so this ships as **chained PRs** on a
feature-branch chain. Each slice is independently reviewable, tested (strict TDD), and behavior-safe
(enrichment stays inert until wired in PR5).

| PR | Slice | Approx lines | Depends on |
|---|---|---|---|
| PR1 | Canonical taxonomy + crosswalk asset + `GenreNormalizer` | ~250 (prod+test) | — |
| PR2 | `GenreProvider` registry + provenance models (no network) | ~200 | PR1 |
| PR3 | Discogs CC0-dump provider (offline ingestion + lookup) | ~350 | PR2 |
| PR4 | MusicBrainz provider (throttled API + local cache) | ~300 | PR2 |
| PR5 | Consensus judge + persistence + wire into scan/recommendation | ~380 | PR3, PR4 |
| PR6 | Desktop UI surfacing (canonical genre, confidence, sources) | ~300 | PR5 |
| PR7 | Optional: local-LLM tie-breaker (flag, default off) | ~250 | PR5 |
| PR8 | Optional: Dawid–Skene trust calibration | ~250 | PR5 |

Each PR keeps its own slice within the 400-line budget. PR7/PR8 are optional and gated.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| License contamination (restrictive data in repo) | High | CC0-only in shipped assets; provider ToU data stays in per-user cache; document in `NOTICE.md`. |
| New network dependencies / flakiness | Medium | Providers opt-in, cached, offline-first; Discogs via local dump; MB throttled 1 req/s with cache; graceful fallback to file tags. |
| Discogs dump size / ingestion cost | Medium | Ingest only needed fields (artist/release -> styles); stream-parse; store compact crosswalk-resolved cache. |
| Taxonomy drift / unmapped labels | Medium | `unmapped` bucket + health metric; crosswalk is versioned and extensible; tests assert coverage of common electronic styles. |
| Scope creep into DSP/fingerprinting | High | Explicitly out of scope; track identity via tags/artist+title/ISRC only. |
| Dependency without upper bound | Medium | Pin `>=lower,<upper` in `pyproject.toml`; update `uv.lock`; keep providers importable-optional. |
| Judge opacity ("why this genre?") | Medium | Persist full provenance + per-source contribution; expose in UI; deterministic and explainable. |
| LLM non-determinism (PR7) | Medium | Local model, `temperature=0`, cached by input hash, candidate-restricted, default off. |

## Rollback plan

1. Disable all providers via config (feature flag) — app reverts to file-tag genre.
2. Remove the enrichment columns/cache table from SQLite (nullable, ignored) or drop them.
3. Detach the canonical genre from recommendation/health (fall back to raw `genre`).
4. Remove provider modules, judge, and taxonomy asset.
5. Drop added dependencies from `pyproject.toml` and re-lock.

Because enrichment is additive and original tags are never overwritten, rollback is non-destructive.

## Success criteria

- [ ] Canonical taxonomy + crosswalk asset exists and covers common electronic styles (House/Techno tree).
- [ ] `GenreNormalizer` deterministically maps known raw labels (Discogs styles, MB genres) to canonical genres.
- [ ] Discogs CC0-dump provider yields candidate genres offline for fixture tracks.
- [ ] MusicBrainz provider yields candidate genres with throttling + cache for fixture tracks.
- [ ] Consensus judge produces a canonical decision with confidence and full provenance from multiple sources.
- [ ] Conflicting source labels are resolved deterministically and explainably (weighted vote).
- [ ] Enriched genre persists in SQLite, survives restart, and never overwrites file tags.
- [ ] Recommendation `same_genre` and `library_health` consume canonical genre.
- [ ] Desktop UI shows canonical genre, confidence, and contributing sources.
- [ ] Only CC0 data is embedded in shipped assets; restrictive-ToU data stays in per-user cache.
- [ ] All verification commands pass; no audio files mutated; no DSP/fingerprinting added.
