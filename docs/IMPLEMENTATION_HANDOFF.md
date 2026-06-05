# XfinAudio — Implementation Handoff

## Product definition

XfinAudio is a **GPL-3.0-only full open-source desktop DJ playlist assistant**.

It helps DJs generate explainable playlists from audio files already processed by **Mixed In Key**. Binary/app bundle redistribution, PySide6/Qt, mutagen, signing/notarization/DMG, and third-party dependencies still require release-specific legal review. No legal clearance is implied.

It is **not**:

- a mixer;
- a DSP app;
- an audio renderer;
- a C++ audio engine;
- a waveform analyzer.

## Core product rules

- Desktop-first app.
- No CLI-first product UX.
- No C++.
- No DSP.
- No audio rendering/mixing.
- Never modify audio files.
- App writes only its own DB/settings/export files.
- Recommendations must be explainable.
- DJ must keep manual control.

## Open-source application stack

| Layer | Decision |
|---|---|
| Language | Python 3.11+ |
| Desktop UI | PySide6 |
| Metadata | mutagen |
| Persistence | SQLite |
| Settings | versioned settings schema |
| Validation/config models | pydantic |
| Tests | pytest |
| Lint/format | ruff |
| Package manager | uv |
| Exports | JSON, CSV, M3U, Serato crate |

## Jira source of truth

Project: `HELP` / XfinAudio

| Issue | Stage |
|---|---|
| HELP-1 | GPLv3 full open-source desktop DJ playlist assistant |
| HELP-2 | Scope realignment and desktop source of truth |
| HELP-3 | Mixed In Key metadata contract discovery |
| HELP-4 | Desktop metadata walking skeleton (implemented in `docs/help-4-desktop-metadata-walking-skeleton.md`) |
| HELP-5 | Scoring and sequence optimizer |
| HELP-6 | Desktop playlist strategies and DJ controls |
| HELP-7 | Explainability, export, Serato crate, quality validation |
| HELP-8 | Release hardening and product-aligned backlog |

## Implementation order

### 1. HELP-3 — Metadata contract discovery

Goal: inspect 5–10 real Mixed In Key processed files.

Deliverables:

- raw tag report;
- identified fields for BPM, Camelot key, energy, title, artist, genre/tags;
- parser rules;
- fixtures for observed variants.

Do this before UI, scoring, or exports.

### 2. HELP-4 — Desktop metadata walking skeleton

Goal: first desktop app slice.

Deliverables:

- PySide6 window;
- folder picker;
- metadata scan action;
- tracks table;
- complete/incomplete status;
- SQLite persistence;
- no audio file writes.

### 3. HELP-5 — Scoring and sequence optimizer

Algorithms:

- Camelot rigid compatibility;
- fuzzy keymixing / Camelot diagonals;
- controlled energy boost;
- BPM compatibility;
- energy compatibility;
- weighted fuzzy scoring;
- Held-Karp exact optimizer for `<=20` tracks;
- greedy + 2-opt for `>20` tracks.

### 4. HELP-6 — Strategies and DJ controls

Strategies:

- harmonic journey;
- warmup;
- build;
- peak-time;
- chill;
- same-energy;
- same-vibe.

Manual controls:

- lock tracks;
- exclude tracks;
- set start track;
- set end track;
- reorder manually;
- regenerate around locked choices;
- adjust weights.

### 5. HELP-7 — Explainability and exports

Every transition must show:

- key score;
- BPM score;
- energy score;
- tag/vibe score;
- final score;
- warnings.

Exports:

- JSON;
- CSV;
- M3U;
- Serato crate.

Serato safety:

```text
research → dry-run → backup → confirm → create → validate → rollback path
```

### 6. HELP-8 — Release hardening

- versioned settings;
- schema migrations/rejections;
- logs/errors;
- quality reports;
- no hardcoded weights;
- no UI business logic;
- strategy/exporter registries.

## Algorithm coverage

In MVP:

1. Harmonic / Camelot scoring.
2. Fuzzy keymixing / diagonals.
3. Controlled energy boost.
4. BPM compatibility.
5. Energy scoring.
6. Weighted fuzzy scoring.
7. Tag/vibe grouping when reliable.
8. Sequence optimization: Held-Karp / greedy + 2-opt.

Future, explicit:

- Tonnetz / TPS tonal distance.

Out of product:

- DSP;
- key detection;
- BPM/beat tracking;
- downbeat tracking;
- cue point detection;
- phrase detection;
- vocal clash;
- timbre similarity;
- embeddings;
- mashability;
- GAN transitions;
- crossfade/render/time-stretch/pitch-shift.

## Files already updated

- `docs/xfinaudio-stack-and-scope-decision.md`
- `docs/plans/2026-06-03-xfinaudio-mvp-sdd-tdd-plan.md`
- `HARMONIC_MIXING.md`
- `docs/IMPLEMENTATION_HANDOFF.md`

## Restart prompt

Use this after restarting:

```text
Continue XfinAudio implementation from docs/IMPLEMENTATION_HANDOFF.md.
Start with HELP-3: Mixed In Key metadata contract discovery.
Use Python 3.11+, PySide6, mutagen, SQLite, pydantic, pytest, ruff, uv.
Do not implement DSP, C++, audio rendering, or audio file mutation.
First inspect 5–10 real Mixed In Key processed audio files, document raw tags, define parser contract, and create fixtures.
Keep responses concise.
```
