# HELP-7 Explainability, Exports, Serato Crate, and Quality Validation

HELP-7 adds pure-Python reporting and export helpers for XfinAudio playlist recommendations. The business logic lives outside the desktop UI under `src/xfinaudio/exporting/` and `src/xfinaudio/quality/`.

## Explainability

`build_playlist_explanation(recommendation)` returns a deterministic pydantic report with:

- playlist strategy, optimizer, track count, transition count, total score, and recommendation warnings;
- one transition explanation per adjacent track pair;
- left/right track context;
- harmonic/key, BPM, energy, tag, component, and final scores;
- scoring explanations and warnings from the recommendation engine.

## Playlist exporters

`playlist_exporters` returns strings for safe caller-managed output:

- `export_playlist_json()` includes ordered tracks and the explainability report;
- `export_playlist_csv()` emits stable columns: `order`, `path`, `title`, `artist`, `bpm`, `camelot_key`, `energy_level`, `status`;
- `export_playlist_m3u()` preserves track order using file paths.

`write_playlist_json()`, `write_playlist_csv()`, and `write_playlist_m3u()` write only to caller-provided target files.

## Serato crate artifact spike

Serato crate support is intentionally limited to deterministic artifact generation and an explicit safety wrapper.

Research basis used for this spike:

- crates live under `_Serato_/Subcrates/` and use a `.crate` extension;
- records are TLV encoded: 4-byte ASCII tag, 4-byte big-endian length, payload bytes;
- `vrsn` stores UTF-16BE text such as `1.0/Serato ScratchLive Crate`;
- track entries are `otrk` records containing nested `ptrk` UTF-16BE relative paths.

Implemented functions:

- `build_serato_crate_bytes(relative_paths)` validates safe relative paths and returns crate bytes;
- `plan_serato_crate_export(crate_name, relative_paths, serato_root)` returns a dry-run plan and preview;
- `write_serato_crate(plan, confirm=True)` writes only when explicitly confirmed, backs up an existing target first, validates the written crate bytes, and returns rollback metadata;
- `rollback_serato_crate_write(result)` restores the backup for overwritten crates or deletes the newly created crate when no backup existed.

No live Serato library discovery or automatic writes are performed.

## Quality validation

`build_quality_report(recommendation, manual_paths=None)` reports:

- track count and transition count;
- average transition score;
- BPM and energy jumps between adjacent tracks;
- warning count;
- optional manual playlist comparison via overlap ratio and order-match prefix count.

## Desktop integration

The desktop table remains thin UI wiring. After recommendation it stores the latest recommendation/explanation and displays transition final score and warnings beside recommended tracks.

## Non-goals and limitations

- No DSP, key/BPM detection, beat tracking, audio rendering, mixing, or audio mutation.
- No Serato database V2 mutation.
- No live Serato library writes without explicit caller confirmation, backup handling, post-write validation, and rollback metadata.
- Serato support is a crate artifact spike only; compatibility should be validated against fixture files before any production workflow.
