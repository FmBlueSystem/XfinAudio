# Specification: Runtime Genre Providers (User-Keyed)

Observable behavior only. No implementation details.

## Requirement 1: Settings extension

The system SHALL accept per-provider enable flags, per-provider API keys, and
an opt-in LLM tie-breaker block, all defaulting to inert.

### Scenario 1.1: Per-provider enable flag

- **GIVEN** a settings block with `providers: {"lastfm": True, "spotify": False, "deezer": True}`
- **WHEN** the enrichment service is constructed
- **THEN** the enabled providers SHALL be Last.fm and Deezer; Spotify SHALL NOT be queried

### Scenario 1.2: Per-provider API key storage

- **GIVEN** a settings block with `api_keys: {"lastfm": "sk-abc", "spotify": "client-id:client-secret"}`
- **THEN** the keys SHALL be accessible to the corresponding providers only
- **AND** providers without a key SHALL return no candidates and SHALL NOT raise

### Scenario 1.3: Default-inert state

- **GIVEN** a default `GenreEnrichmentSettings` instance
- **THEN** `enabled` SHALL be `False`
- **AND** `providers` SHALL be empty
- **AND** `api_keys` SHALL be empty
- **AND** `llm_tiebreaker_enabled` SHALL be `False`
- **AND** `llm_tiebreaker_url` SHALL default to a local Ollama endpoint
- **AND** `llm_tiebreaker_model` SHALL default to a sensible local model name

## Requirement 2: Last.fm provider (runtime, user-keyed)

### Scenario 2.1: Last.fm returns canonical candidates

- **GIVEN** a Last.fm response fixture with top tags `[("tech house", 100), ("seen live", 50)]`
- **WHEN** the Last.fm provider processes it
- **THEN** it SHALL return a canonical candidate `"Tech House"` from source `"lastfm"`
- **AND** the `"seen live"` tag SHALL be filtered out

### Scenario 2.2: Last.fm works without network when cached

- **GIVEN** a Last.fm provider whose per-user cache has a prior result
- **WHEN** the provider is queried
- **THEN** it SHALL return the cached candidates without making a network call

### Scenario 2.3: Last.fm missing key yields no candidates

- **GIVEN** a Last.fm provider with no API key configured
- **WHEN** the provider is queried
- **THEN** it SHALL return `[]`
- **AND** it SHALL NOT raise

## Requirement 3: Spotify provider (runtime, user-keyed)

### Scenario 3.1: Spotify returns artist-level genres

- **GIVEN** a Spotify response fixture with artist genres `["tech house", "house"]`
- **WHEN** the Spotify provider processes it
- **THEN** it SHALL return canonical candidates `"Tech House"` and `"House"` from source `"spotify"`

### Scenario 3.2: Spotify missing credentials yields no candidates

- **GIVEN** a Spotify provider with no client credentials configured
- **WHEN** the provider is queried
- **THEN** it SHALL return `[]`
- **AND** it SHALL NOT raise

## Requirement 4: Deezer provider (runtime, no key required for catalog)

### Scenario 4.1: Deezer returns coarse top-level genre

- **GIVEN** a Deezer response fixture with artist top genre `"Electronic"`
- **WHEN** the Deezer provider processes it
- **THEN** it SHALL return a canonical candidate mapped from `"Electronic"`
- **AND** the candidate source SHALL be `"deezer"`

### Scenario 4.2: Deezer coarse genres collapse to canonical

- **GIVEN** Deezer top-level genre `"Dance"`
- **WHEN** the Deezer provider processes it
- **THEN** it SHALL map to a canonical genre (e.g. `"Dance-Pop"` or another Dance subgenre in the canonical taxonomy)

## Requirement 5: Provider protocol conformance

All three new providers SHALL satisfy the `GenreProvider` protocol from the
core change (i.e. `name: str` + `fetch(track) -> list[GenreCandidate]`).

### Scenario 5.1: All providers are GenreProvider instances

- **GIVEN** a `LastfmProvider`, a `SpotifyProvider`, and a `DeezerProvider`
- **THEN** each SHALL be a `GenreProvider` instance per `isinstance(..., GenreProvider)`

## Requirement 6: LLM tie-breaker (opt-in, default OFF)

The system SHALL provide a local-LLM tie-breaker that is OFF by default and
SHALL NEVER be invoked unless the user explicitly enables it.

### Scenario 6.1: LLM is OFF by default

- **GIVEN** a default `GenreEnrichmentSettings` instance
- **WHEN** the judge produces a `low_confidence` decision
- **THEN** the LLM SHALL NOT be invoked
- **AND** the deterministic decision SHALL stand

### Scenario 6.2: LLM tie-breaker restricts to taxonomy

- **GIVEN** the LLM tie-breaker explicitly enabled and a `low_confidence` decision
- **WHEN** the tie-breaker runs against a local model
- **THEN** the model's response SHALL be validated against the canonical taxonomy
- **AND** any output outside the taxonomy SHALL be rejected
- **AND** the tie-breaker SHALL choose only among the already-normalized `top_n` candidates

### Scenario 6.3: LLM tie-breaker is deterministic + cached

- **GIVEN** the LLM tie-breaker enabled and a fixed `low_confidence` decision
- **WHEN** the tie-breaker runs twice with the same inputs
- **THEN** it SHALL return the same chosen candidate (cache hit on second call)
- **AND** it SHALL issue exactly one HTTP call to the local model (verified by call counter)

### Scenario 6.4: LLM tie-breaker targets a local endpoint

- **GIVEN** `llm_tiebreaker_url = "http://localhost:11434/api/generate"`
- **WHEN** the tie-breaker runs
- **THEN** the HTTP call SHALL target the configured URL
- **AND** no cloud endpoint SHALL be contacted

## Requirement 7: License posture remains CC0-shipped, runtime-only

### Scenario 7.1: No provider-derived data in repo

- **GIVEN** the repository tree
- **THEN** no Last.fm, Spotify, or Deezer response data SHALL be present in shipped assets
- **AND** the existing `test_genre_license_assets.py` scan SHALL pass

### Scenario 7.2: NOTICE.md documents runtime-only/user-keyed posture

- **GIVEN** the updated `NOTICE.md`
- **THEN** it SHALL mention each new provider and the LLM as runtime-only/user-keyed/opt-in
- **AND** it SHALL NOT promise any provider is on by default

## Requirement 8: Backward compatibility with core enrichment

The new providers and the LLM tie-breaker SHALL NOT change the behavior of
the core enrichment pipeline when they are disabled.

### Scenario 8.1: Core pipeline unaffected when no new providers are enabled

- **GIVEN** default settings (`enabled=False`, all providers off, LLM off)
- **WHEN** the enrichment service runs against the existing providers
- **THEN** the behavior SHALL be identical to the previous change

### Scenario 8.2: Provider failures are still isolated

- **GIVEN** any of the new providers configured but currently failing (network, auth, parse)
- **WHEN** enrichment runs alongside a healthy provider
- **THEN** the failing provider SHALL NOT propagate an exception
- **AND** the healthy provider's candidates SHALL still be judged
