# XfinAudio Canonical SDD/TDD Plan

**Change name:** `xfinaudio-mixedinkey-playlist-recommender`  
**Official product statement:** XfinAudio is a metadata-driven playlist recommender, not an audio mixing engine.  
**Primary data source:** Audio files already processed by Mixed In Key.  
**CLI vocabulary:** `scan`, `recommend`, `export`.  
**CLI framework:** Typer.  
**Testing mode:** Strict TDD.

## Purpose

Build an offline CLI that reads Mixed In Key metadata from local audio files, normalizes track features, recommends useful playlists, and exports deterministic outputs.

Product excludes DSP, waveform analysis, beatmatching, crossfades, EQ, stems, and audio rendering.

---

## Validated Instruction

Document and build XfinAudio as a metadata-driven playlist recommender. First discover the real Mixed In Key tag contract from actual files, then implement a tolerant parser, cache, recommendation algorithms, and exports.

---

# Proposal

## In Scope

- Inspect 5–10 real Mixed In Key processed files.
- Document where BPM, Camelot key, energy, title, artist, genre/tags live.
- Build a tolerant metadata parser using `mutagen`.
- Normalize metadata into versioned cache records.
- Recommend playlists using configurable harmonic/BPM/energy/tag scoring.
- Export JSON, CSV, M3U.
- Validate recommendation quality against manual playlists/setlists.

## Out of Scope

- Native DSP: Essentia, librosa, madmom — excluded from product roadmap unless product scope changes explicitly.
- Audio rendering/mixing.
- Crossfade, EQ automation, beatmatching.
- Phrase/downbeat detection unless metadata already exists.
- Real-time DJ control.
- UI.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Mixed In Key tag layout varies | High | Stage 1 tag discovery on real files before parser implementation |
| Energy has no universal standard field | High | Parser supports grouping/comment/comment2/text variants |
| Key may be Camelot or musical notation | Medium | Normalize accepted variants; mark unknown/incomplete |
| Tags/vibe may be inconsistent | Medium | Make tag score optional and configurable |
| Recommendation weights are arbitrary | Medium | Configurable weights + validation against manual playlists |

---

# Specification

## Requirement: Mixed In Key Metadata Contract Discovery

The system MUST discover and document the real tag layout before implementing the parser.

### Scenario: Inspect real files

- GIVEN 5–10 real audio files already processed by Mixed In Key
- WHEN tag inspection runs
- THEN the system MUST output raw tags per file
- AND identify candidate fields for BPM, Camelot key, energy, title, artist, genre, and comments

### Scenario: Contract documented

- GIVEN inspected tags
- WHEN Stage 1 completes
- THEN the project MUST document accepted field names and parsing patterns
- AND create test fixtures for observed variants

## Requirement: Metadata Scan

The system MUST scan a folder and normalize Mixed In Key metadata.

### Scenario: Complete track

- GIVEN a track with BPM, Camelot key, and energy
- WHEN `xfinaudio scan <folder>` runs
- THEN the cache MUST contain a complete normalized track record

### Scenario: Incomplete track

- GIVEN a track missing key, BPM, or energy
- WHEN scan runs
- THEN the track MUST be marked incomplete
- AND recommendation MUST exclude or degrade it according to strategy configuration

## Requirement: Configurable Recommendation Scoring

The system MUST use configurable scoring weights.

### Scenario: Default fuzzy score

- GIVEN complete tracks
- WHEN scoring runs with default config
- THEN it MUST combine harmonic, BPM, energy, and tag scores

### Scenario: Missing tags

- GIVEN tracks without reliable tags
- WHEN tag score is unavailable
- THEN tag weight MUST be ignored or redistributed deterministically

## Requirement: Playlist Recommendation

The system MUST recommend deterministic playlists.

### Scenario: Harmonic strategy

- GIVEN cached tracks with Camelot keys
- WHEN `xfinaudio recommend <folder> --strategy harmonic` runs
- THEN adjacent tracks SHOULD prefer same, neighbor, or relative Camelot keys

### Scenario: Energy build strategy

- GIVEN cached tracks with energy values
- WHEN `--strategy energy-build` runs
- THEN the playlist SHOULD generally move from lower to higher energy

## Requirement: Recommendation Quality Validation

The system SHOULD define a repeatable evaluation method.

### Scenario: Manual playlist comparison

- GIVEN one or more manually curated playlists
- WHEN generated playlists are compared
- THEN the evaluation SHOULD report average transition score, BPM jumps, energy jumps, and manual review notes

---

# Design

## Architecture

```text
Audio folder
  → metadata/tag_inspector.py
  → metadata/mixedinkey_reader.py
  → feature normalizer
  → versioned cache
  → scoring engine
  → playlist strategies
  → exporters
```

## Stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| Package manager | uv |
| CLI | Typer |
| Metadata | mutagen |
| Cache MVP | JSON |
| Tests | pytest |
| Lint/format | ruff |
| Export | JSON, CSV, M3U |

## Cache schema v1

```json
{
  "schema_version": 1,
  "source_fingerprint": "...",
  "source_path": "track.flac",
  "metadata_source": "mixed-in-key-tags",
  "raw_tags": {},
  "normalized_features": {
    "title": null,
    "artist": null,
    "bpm": 124.0,
    "camelot_key": "8A",
    "energy": 7,
    "genre": null,
    "tags": []
  },
  "metadata_status": "complete"
}
```

## Default scoring config

```json
{
  "weights": {
    "harmonic": 0.40,
    "bpm": 0.25,
    "energy": 0.25,
    "tags": 0.10
  }
}
```

Weights are defaults, not constants. They must be configurable and validated.

---

# Tasks / Stages

## Stage 0 — Scope realignment

- [ ] Confirm official statement: metadata-driven playlist recommender, not mixing engine.
- [ ] Retire old `analyze/plan-set` vocabulary.
- [ ] Use `scan/recommend/export` everywhere.
- [ ] Confirm Typer as CLI framework.

## Stage 1 — Mixed In Key metadata contract discovery

- [ ] Select 5–10 real processed audio files.
- [ ] Write tag inspection script/test harness.
- [ ] Dump raw tags with secrets/path safety.
- [ ] Document observed BPM/key/energy fields.
- [ ] Define tolerant parsing patterns.
- [ ] Create fixtures for observed variants.

## Stage 2 — Metadata walking skeleton

- [ ] Create package skeleton.
- [ ] Write failing CLI test for `xfinaudio scan <folder>`.
- [ ] Implement Typer command.
- [ ] Implement `mixedinkey_reader.py` with fixtures.
- [ ] Write cache schema v1 tests.
- [ ] Implement JSON cache.

## Stage 3 — First recommendation

- [ ] Write Camelot compatibility tests.
- [ ] Implement harmonic scoring.
- [ ] Write BPM/energy score tests.
- [ ] Implement configurable fuzzy scoring.
- [ ] Implement `xfinaudio recommend --strategy harmonic`.

## Stage 4 — Playlist strategies

- [ ] Implement `energy-build`.
- [ ] Implement `warmup`.
- [ ] Implement `peak-time`.
- [ ] Implement `same-energy`.
- [ ] Make tag-based strategy optional.

## Stage 5 — Export formats

- [ ] Implement stable JSON export.
- [ ] Implement CSV export.
- [ ] Implement M3U export.
- [ ] Test deterministic repeated output.

## Stage 6 — Quality validation and hardening

- [ ] Add manual playlist comparison report.
- [ ] Reject unknown cache schema.
- [ ] Detect fingerprint mismatch.
- [ ] Report incomplete tracks clearly.
- [ ] Run verification commands.

## Stage 7 — Future backlog

- [ ] Alternative metadata importers only if Mixed In Key tags are unavailable.
- [ ] Rekordbox/Serato export.
- [ ] UI dashboard.
- [ ] Mood/style embeddings.

---

## Verification Commands

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

---

# Algorithm Coverage Addendum

## Additional MVP Requirements

### Requirement: Fuzzy Keymixing

The system MUST support configurable Camelot compatibility beyond same, adjacent, and relative keys.

#### Scenario: Diagonal Camelot move

- GIVEN a track in `2A`
- WHEN harmonic scoring evaluates `1B` or `3B`
- THEN the transition SHOULD receive a configurable fuzzy-keymixing score
- AND this score MUST be distinct from weighted multi-feature fuzzy scoring

#### Scenario: Controlled energy boost

- GIVEN a configured energy boost rule such as `8A → 10A`
- WHEN harmonic scoring evaluates that transition
- THEN it SHOULD apply the configured boost score

### Requirement: Sequence Optimization

The system MUST convert pairwise transition scores into a full ordered playlist.

#### Scenario: Small playlist exact optimizer

- GIVEN 20 or fewer candidate tracks
- WHEN recommendation runs
- THEN the system SHOULD use Held-Karp or equivalent exact dynamic programming optimizer

#### Scenario: Large playlist heuristic optimizer

- GIVEN more than 20 candidate tracks
- WHEN recommendation runs
- THEN the system SHOULD use greedy initialization plus 2-opt refinement or equivalent documented heuristic

### Requirement: Playlist Strategy Scenarios

#### Scenario: Warmup strategy

- GIVEN tracks with BPM, Camelot key, and energy
- WHEN `--strategy warmup` runs
- THEN the playlist SHOULD prefer low-to-mid energy tracks with smooth harmonic/BPM transitions

#### Scenario: Peak-time strategy

- GIVEN tracks with energy values
- WHEN `--strategy peak-time` runs
- THEN the playlist SHOULD prefer high-energy tracks while preserving compatibility

#### Scenario: Same-energy strategy

- GIVEN tracks with energy values
- WHEN `--strategy same-energy` runs
- THEN adjacent tracks SHOULD stay within a configured energy tolerance

#### Scenario: Same-vibe strategy

- GIVEN reliable genre/tags/grouping metadata
- WHEN `--strategy same-vibe` runs
- THEN the playlist SHOULD group tracks by compatible tags/vibe
- AND if tags are unreliable, the strategy MUST degrade gracefully or be unavailable

## Future Explicitly Deferred

- Tonnetz / Lerdahl TPS tonal distance: future harmonic model, no DSP required but not MVP.

## Explicit OUT Inventory

- key detection;
- BPM/beat tracking;
- downbeat tracking;
- cue point detection;
- phrase/structural segmentation;
- timbre similarity;
- vocal clash detection;
- mashability beat-synchronous;
- contrastive embeddings;
- GAN transitions;
- crossfade/EQ/render/time-stretch/pitch-shift.

---

# Serato Export Requirement Addendum

## Requirement: Serato Crate Export

The system SHOULD export a recommended playlist to Serato as a crate/export artifact.

### Scenario: Create Serato crate export

- GIVEN a recommended playlist
- WHEN the user selects `Export to Serato Crate`
- THEN the system SHOULD create a Serato-compatible crate with the playlist order
- AND SHOULD NOT modify audio files

### Scenario: Safe write policy

- GIVEN export requires writing into Serato library files/folders
- WHEN the user confirms export
- THEN the system MUST show a dry-run preview
- AND MUST create a backup before writing
- AND MUST provide rollback instructions

## Stage impact

Add to Stage 5 — Export and quality validation:

- [ ] Research Serato crate format and write locations.
- [ ] Add Serato crate exporter behind an exporter interface.
- [ ] Add dry-run and backup flow before any Serato library write.
- [ ] Test export with fixture paths and deterministic crate ordering.

---

# DJ Assistant Addendum

## Requirement: Explainable Recommendations

The system MUST explain playlist recommendations to the DJ.

### Scenario: Transition explanation

- GIVEN two adjacent recommended tracks
- WHEN the playlist is displayed
- THEN the UI MUST show harmonic, BPM, energy, tag, and final score reasons

## Requirement: DJ Intent Modes

The system MUST let the DJ choose playlist intent.

### Scenario: Select intent mode

- GIVEN a scanned library
- WHEN the DJ selects warmup, build, peak-time, chill, same-energy, same-vibe, or harmonic journey
- THEN recommendation rules MUST adapt to that intent

## Requirement: Manual DJ Control

The system MUST allow the DJ to direct the recommendation.

### Scenario: Lock and regenerate

- GIVEN a generated playlist
- WHEN the DJ locks selected tracks and regenerates
- THEN locked tracks MUST remain in place or within configured constraints

### Scenario: Exclude tracks

- GIVEN tracks the DJ does not want
- WHEN the DJ excludes them
- THEN the recommender MUST not include them in generated playlists

### Scenario: Set start/end track

- GIVEN a desired opening or closing track
- WHEN the DJ sets start or end constraints
- THEN the sequence optimizer MUST respect those constraints when feasible

## Requirement: Product Persistence

The system SHOULD use SQLite for product persistence and versioned settings for configuration.

### Scenario: Persist library scan

- GIVEN a completed scan
- WHEN the app restarts
- THEN scanned tracks and normalized metadata SHOULD remain available

### Scenario: Versioned settings

- GIVEN scoring weights and UI/export preferences
- WHEN settings are saved
- THEN they MUST include schema version and support explicit migration or rejection

## Requirement: Serato Crate Validation Spike

The system MUST validate Serato crate behavior before shipping write support.

### Scenario: Serato dry-run

- GIVEN a recommended playlist
- WHEN the DJ chooses Serato export
- THEN the app MUST show a dry-run preview before writing

### Scenario: Backup before write

- GIVEN Serato export writes to Serato library structure
- WHEN the user confirms
- THEN the app MUST back up affected files before writing
