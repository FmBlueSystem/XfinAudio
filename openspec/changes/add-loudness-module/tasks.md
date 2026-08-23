# Tasks: add-loudness-module

## WU1 — Port and FFmpeg adapter

- [x] 1.1 Define `LoudnessAnalyzer` port + `LoudnessProfile` Pydantic model (status enum,
      analysis_version, engine_fingerprint, post-write source identity fields)
- [x] 1.2 Implement FFmpeg adapter: pinned command contract (`-nostdin`, `-map 0:a:0`,
      `-vn`, `stdin=DEVNULL`), injectable command construction
- [x] 1.3 Stderr parser with typed outcomes; fixture-based regression tests against the
      pinned build's output format
- [x] 1.4 Capability preflight (binary present, filter present, true-peak supported)
- [x] 1.5 Timeout + kill-on-timeout classified as transient failure; process-group kill on
      cancel; orphan reaping on shutdown
- [x] 1.6 Conformance fixtures: golden LUFS/LRA/TP on synthetic WAVs; pyloudnorm as
      epsilon-tolerant LUFS-I sanity oracle only
- [x] 1.7 Minimum-duration floor: LRA/TP None below floor, typed too_short status

## WU2 — Persistence and pipeline integration

- [x] 2.1 Add `loudness_profile_json` column; include explicitly in `save_scan_results`
      INSERT/CASE (regression test first: column omitted → wiped)
- [x] 2.2 Cache validity from identity stored inside the profile, captured AFTER tag write;
      never consult shared tracks identity columns for loudness
- [ ] 2.3 Post-write sibling preservation via shared identity helper from
      fix-derived-profile-cache-identity (RED regression: tag write must not wipe
      spectral/danceability/edge on any format)
- [x] 2.4 Persist typed failures; retry only on version/fingerprint bump or explicit
      reanalyze
- [ ] 2.5 Serialize into existing lazy completion lifecycle; disk-bound concurrency cap
      (2–3); priority queue (selected → candidates → visible folder → rest); per-result
      immediate persistence

## WU3 — Target-band filter, strategy, tag write-back

- [ ] 3.1 Hard LUFS target band as pool filter in `_apply_strategy_filters`, returning
      `(filtered, warnings)`; unmeasured stay in pool exempt while coverage incomplete,
      warning carries coverage numbers ("N of M applied; K left in")
- [ ] 3.2 Register "Consistent Loudness" strategy via StrategyName/_STRATEGIES/catalog;
      orthogonal target setting (no Warmup/Peak catalog rows); partial-coverage honesty in
      strategy output
- [ ] 3.3 Tag write-back: COMMENT summary (frozen `{:.1f}` format, write only on changed
      values) + structured `XFINAUDIO_LOUDNESS` custom tag (v1 payload schema)
- [ ] 3.4 Write ordering: measure → write tags → restat → stamp profile identity → persist;
      shared identity helper call after write
- [ ] 3.5 Best-effort recovery-from-tags on scan when DB row absent (per-format capability
      map; DB remains source of truth)

## WU4 — Settings, UI surface, packaging, governance

- [ ] 4.1 `LoudnessSettings` without CURRENT_SETTINGS_VERSION bump; module toggle default ON
- [ ] 4.2 AppState + progress surface for loudness stage (immutable transitions pattern)
- [ ] 4.3 True-peak badge (warn > −1.0 dBTP, clip ≥ 0.0 dBTP) + LUFS/LRA/dBTP detail pane
- [ ] 4.4 en/es translations for all new UI strings
- [ ] 4.5 Packaging: FFmpeg CLI in binaries=[], bundle-absolute invocation, UPX exclusion,
      license inventory entry
- [x] 4.6 Governance: amend read-only contract text in README (EN/ES), AGENTS.md,
      CONTRIBUTING.md + tests pinning the amended sentences
- [ ] 4.7 Full suite green; coverage ≥ baseline 91.14%; release gate pass
