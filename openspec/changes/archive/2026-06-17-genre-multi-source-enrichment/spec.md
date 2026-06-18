# Specification: Genre Multi-Source Enrichment with a Consensus Judge

Observable behavior only. No implementation details.

## Requirement 1: Canonical genre taxonomy and crosswalk

The system SHALL provide a versioned canonical genre taxonomy (DJ/Beatport-style vocabulary) with a
hierarchy and a crosswalk that maps raw source labels onto canonical genres.

### Scenario 1.1: Known style maps to canonical genre

- **GIVEN** the raw label `"Tech House"` from a source
- **WHEN** the normalizer resolves it against the crosswalk
- **THEN** it SHALL return the canonical genre `"Tech House"`
- **AND** the canonical genre SHALL have parent `"House"` in the taxonomy hierarchy

### Scenario 1.2: Spelling/alias variant maps to the same canonical genre

- **GIVEN** the raw labels `"tech-house"`, `"Tech-House"`, and `"TECH HOUSE"`
- **WHEN** each is normalized
- **THEN** all SHALL resolve to the same canonical genre `"Tech House"`

### Scenario 1.3: Unknown label is reported as unmapped

- **GIVEN** a raw label with no crosswalk entry (e.g., `"qwerty noise"`)
- **WHEN** it is normalized
- **THEN** it SHALL resolve to the `unmapped` sentinel
- **AND** it SHALL NOT raise an exception

### Scenario 1.4: Taxonomy covers the core electronic tree

- **GIVEN** the canonical taxonomy asset
- **WHEN** it is loaded
- **THEN** it SHALL contain at least House, Techno, Trance, Drum & Bass, and their common subgenres
  (Deep House, Tech House, Melodic House & Techno, Peak Time Techno, Progressive House)

## Requirement 2: Genre provider abstraction

The system SHALL expose a provider registry where each genre provider is independently registered,
toggleable, and returns normalized candidate genres with a per-source confidence.

### Scenario 2.1: Provider returns normalized candidates

- **GIVEN** a registered provider and a track with artist/title (or release identifier)
- **WHEN** the provider is queried
- **THEN** it SHALL return zero or more candidate genres already mapped to the canonical taxonomy
- **AND** each candidate SHALL carry a source name and a confidence in `[0, 1]`

### Scenario 2.2: Disabled provider is not queried

- **GIVEN** a provider disabled via configuration
- **WHEN** enrichment runs
- **THEN** the disabled provider SHALL NOT be queried
- **AND** its absence SHALL NOT raise an error

### Scenario 2.3: Provider failure is isolated

- **GIVEN** a provider that raises or times out
- **WHEN** enrichment runs with other healthy providers
- **THEN** the failing provider SHALL contribute no candidates
- **AND** enrichment SHALL still produce a decision from the remaining providers
- **AND** no unhandled exception SHALL propagate

## Requirement 3: Discogs provider (CC0 dump)

The system SHALL derive candidate genres from Discogs CC0 monthly-dump data offline.

### Scenario 3.1: Discogs styles become canonical candidates

- **GIVEN** an ingested Discogs dump fixture where a release has styles `["Tech House", "Deep House"]`
- **WHEN** the Discogs provider is queried for a matching track
- **THEN** it SHALL return canonical candidates including `"Tech House"` and `"Deep House"`
- **AND** the candidate source SHALL be `"discogs"`

### Scenario 3.2: Offline operation

- **GIVEN** no network connectivity
- **WHEN** the Discogs provider is queried against the ingested dump cache
- **THEN** it SHALL still return candidates without any network call

## Requirement 4: MusicBrainz provider (CC0)

The system SHALL derive candidate genres from MusicBrainz CC0 genre/tag data, respecting rate limits.

### Scenario 4.1: MB genres become canonical candidates

- **GIVEN** a MusicBrainz response fixture exposing genres `["techno"]` with vote weights
- **WHEN** the MusicBrainz provider processes it
- **THEN** it SHALL return a canonical candidate `"Techno"` from source `"musicbrainz"`
- **AND** the candidate confidence SHALL reflect the relative vote weight

### Scenario 4.2: Rate limit and cache

- **GIVEN** the MusicBrainz provider configured against the public service
- **WHEN** it issues requests
- **THEN** it SHALL not exceed 1 request per second
- **AND** a repeated lookup for the same entity SHALL be served from cache without a new request

## Requirement 5: Consensus judge

The system SHALL resolve candidates from all sources into a canonical decision via a deterministic
weighted vote, emitting top-N genres, a confidence, and full provenance.

### Scenario 5.1: Agreement reinforces a single genre

- **GIVEN** Discogs and MusicBrainz both yield `"Techno"` for a track
- **WHEN** the judge runs
- **THEN** the decided primary genre SHALL be `"Techno"`
- **AND** the decision confidence SHALL be higher than from a single source alone

### Scenario 5.2: Conflict resolved by weighted vote

- **GIVEN** Discogs yields `"Tech House"` (trust 1.0) and MusicBrainz yields `"House"` (trust 0.9)
- **WHEN** the judge runs
- **THEN** the decided primary genre SHALL be `"Tech House"` (higher weighted score)
- **AND** the provenance SHALL record both candidates and their per-source contributions

### Scenario 5.3: Low-confidence flag on thin margin

- **GIVEN** two canonical genres with nearly equal weighted scores (margin below the threshold)
- **WHEN** the judge runs
- **THEN** the decision SHALL be flagged `low_confidence`
- **AND** both genres SHALL be retained in the top-N candidate list

### Scenario 5.4: Determinism

- **GIVEN** the same set of source candidates
- **WHEN** the judge runs multiple times
- **THEN** it SHALL produce identical decisions, ordering, and confidence values

### Scenario 5.5: No sources yields no decision, not an error

- **GIVEN** a track for which no provider returns candidates
- **WHEN** the judge runs
- **THEN** it SHALL return an empty/`None` decision
- **AND** the track SHALL retain its original file-tag genre

## Requirement 6: Persistence and provenance

The system SHALL persist the canonical decision, confidence, and provenance in the app-owned SQLite
database without overwriting original file tags.

### Scenario 6.1: Decision survives restart

- **GIVEN** a track enriched with a canonical genre decision and provenance
- **WHEN** the application restarts and loads the library
- **THEN** the loaded record SHALL include the canonical genre, confidence, and per-source provenance

### Scenario 6.2: Original tag is preserved

- **GIVEN** a track with file-tag genre `"Electronica"` enriched to canonical `"Tech House"`
- **WHEN** the record is persisted and reloaded
- **THEN** the original file-tag genre SHALL remain available and unchanged
- **AND** no audio file SHALL be mutated

### Scenario 6.3: Re-enrichment updates the decision

- **GIVEN** a track with an existing canonical decision
- **WHEN** enrichment runs again with new candidates
- **THEN** the stored decision and provenance SHALL be replaced with the new result

## Requirement 7: Integration with recommendation and health

The system SHALL allow recommendation and library-health features to consume the canonical genre.

### Scenario 7.1: same_genre uses canonical genre

- **GIVEN** tracks enriched with canonical genres and the `same_genre` strategy selected
- **WHEN** a playlist is built
- **THEN** candidate filtering SHALL use the canonical genre when present
- **AND** SHALL fall back to the raw file-tag genre when no canonical decision exists

### Scenario 7.2: Health variant detection prefers canonical genre

- **GIVEN** a library where canonical genres are available
- **WHEN** the health report is computed
- **THEN** genre variant grouping SHALL operate on canonical genres, reducing false variant groups

## Requirement 8: License posture

The system SHALL embed only CC0-licensed data in shipped assets and keep restrictive-ToU provider
data in per-user local caches.

### Scenario 8.1: Shipped assets are CC0

- **GIVEN** the repository's in-repo data assets for this feature
- **WHEN** they are inspected
- **THEN** they SHALL contain only the canonical taxonomy/crosswalk (CC0) and no Discogs-API,
  Last.fm, Spotify, or Deezer-derived datasets

### Scenario 8.2: Provider ToU data stays local

- **GIVEN** data fetched from a restrictive-ToU endpoint (e.g., Discogs live API, if enabled)
- **WHEN** it is cached
- **THEN** it SHALL be written only to the per-user app cache, never to repository assets

## Requirement 9: Optional features (deferred, flag-gated)

The system MAY provide an optional local-LLM tie-breaker and an optional Dawid–Skene trust calibration,
both disabled by default and out of the core delivery.

### Scenario 9.1: LLM tie-breaker is off by default

- **GIVEN** default configuration
- **WHEN** the judge encounters a `low_confidence` decision
- **THEN** no LLM SHALL be invoked
- **AND** the deterministic decision SHALL stand

### Scenario 9.2: LLM tie-breaker stays within the taxonomy

- **GIVEN** the LLM tie-breaker explicitly enabled and a `low_confidence` decision
- **WHEN** it runs locally
- **THEN** it SHALL choose only among the already-normalized candidate genres
- **AND** it SHALL NOT introduce any genre outside the canonical taxonomy
