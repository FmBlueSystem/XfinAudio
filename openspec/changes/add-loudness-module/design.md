# Design: add-loudness-module

Status: APPROVED v2 — product-owner approval recorded 2026-08-22.
Provenance tags: [OPUS] / [GROK] / [CODEX] = finding origin; [OWNER] = product-owner decision.

## 1. Engine (WU1)

Pinned, bundled **FFmpeg CLI executable** behind a `LoudnessAnalyzer` port. [OPUS+GROK consensus]

- Command contract per invocation:
  `ffmpeg -nostdin -hide_banner -i <path> -map 0:a:0 -vn -af ebur128=peak=true -f null -`
  (`-map 0:a:0` pins the first audio stream — embedded cover art otherwise makes stream
  selection a coin flip. [GROK B5/F7])
- `stdin=DEVNULL`; shell-free argument tokens only. [OPUS F7]
- Explicit timeout with kill-on-timeout; result classified as *transient failure*, not
  *unmeasurable*. [OPUS F7]
- The adapter holds the `Popen` handle and kills the process group on cancel/teardown —
  first analyzer in this codebase with real mid-file cancellation (librosa cancellation is
  cooperative-only per `spectral_completion_worker.py:218-221`). Orphan reaping on
  shutdown tracks live handles. [OPUS/GROK R2]
- Capability preflight at startup: executable present at bundled absolute path,
  `ebur128` filter present, true-peak mode supported. Never resolve via `PATH` in the
  frozen app; PATH is a developer fallback only. [GROK R14]
- Stderr parser pinned to the shipped FFmpeg build version, with fixture-based regression
  tests rejecting malformed output instead of silently returning None. [CODEX/OPUS]
- Conformance fixtures: golden stderr outputs for known WAV inputs; pyloudnorm used as
  LUFS-I sanity oracle only (epsilon-tolerant), never as the true-peak contract. [GROK R8]

Rejected alternatives: pyloudnorm as engine (no compliant true peak — OPUS/CODEX agree);
pure-Python meter (rebuilds a standard for no gain); libebur128 binding (accepts PCM, not
files — would still require building a decode layer; deferred until profiling justifies).

## 2. Data model and persistence (WU2)

Single versioned Pydantic model serialized to one nullable JSON column:

```
LoudnessProfile:
  lufs_integrated: float
  loudness_range_lra: float | None      # None below minimum duration
  true_peak_dbtp: float | None          # None below minimum duration
  status: enum(measured, unmeasurable, transient_failure, unsupported, too_short)
  analysis_version: int
  engine_fingerprint: str               # e.g. "ffmpeg-7.1.1-ebr128"
  source_mtime_ns: int                  # captured AFTER any tag write [OPUS F5]
  source_size_bytes: int                # captured AFTER any tag write [OPUS F5]
  source_audio_md5: str | None          # FLAC only when available [OPUS F1]
```

- Column: `loudness_profile_json`, added to `save_scan_results` INSERT/CASE explicitly —
  a new column omitted from that CASE is wiped by the next scan. [GROK B7]
- Cache validity consults **identity stored inside the profile**, never the shared
  `tracks.file_mtime_ns/file_size_bytes` columns. This decouples loudness from the shared
  identity pair entirely. [OPUS F1 fix #1 — adopted over flat scalar columns]
- Tag-write ordering: measure → write tags → restat → stamp identity → persist. Capturing
  identity before the write costs one full spurious re-analysis of the library (converges,
  but re-decodes everything once). [OPUS F5]
- After write-back, call the **shared identity helper** from
  `fix-derived-profile-cache-identity` so sibling profiles are atomically preserved across
  the mtime/size change on all formats. [GROK R12 + OPUS F1]
- Typed failure statuses persist so corrupt files are not retried every scan; retry only on
  version/fingerprint bump or explicit user reanalyze. [GROK N1]
- Minimum duration floor: EBU gating is statistically meaningless on very short material —
  LRA/true peak return `None` below it (integrated LUFS still measured). Edge spectral
  already uses a typed skip precedent. [OPUS + GROK N2]
- No SCHEMA_VERSION bump required if added via the existing nullable-column pattern;
  verify against migration tests either way. [CODEX precedent]

## 3. Analysis pipeline (WU2)

- Integrate into the existing lazy completion lifecycle, **serialized** with the current
  analyzer chain — no fourth copy-paste Qt worker. Generalizing the three ~279-line
  workers is tracked as separate follow-up debt. [OPUS/GROK R1 compromise]
- Concurrency cap is **disk-bound (2–3), not `cpu_count − 1`**: each FFmpeg process does
  native decode work and this library lives on external drives. [GROK R5]
- Priority order: selected tracks → recommendation candidates → visible folder → rest.
  Persist each result immediately (crash loses at most in-flight tracks). [CODEX]
- First activation runs a full-library analysis pass (analyze in place; metadata rescan
  follows the existing scan flow, now safe post-cache-fix). Incremental cached rescans
  after. [OWNER decision R6, safety shape per GROK B6]

## 4. Product semantics: target-band filter (WU3)

Owner-selected LUFS target (e.g. warmup −14, peak-time −9) with a hard tolerance band,
implemented as a **pool filter beside `energy_range` in `_apply_strategy_filters`,
returning `(filtered, warnings)`** — NOT a pairwise transition score. [OPUS F6 + GROK B4,
independent double confirmation]

Rationale: under absolute whole-set semantics, adjacent pairwise deltas are bounded by the
band itself; a scoring component would double-count it and sit in a bucket contradicting
its own justification. `ScoringWeights.loudness` does not exist in v1.

- Unmeasured tracks **stay in the pool, exempt from the band**, while coverage is
  incomplete — mirroring the `_weighted_total` neutral lesson on the filter side, where
  dropping missing values systematically starved pools during progressive analysis.
  Warnings carry coverage numbers: "Loudness band applied to N of M tracks; K not yet
  measured and left in." [OPUS F4; GROK R3 adds: do not label such a set "loudness-matched"]
- Strategy registered through `StrategyName`/`_STRATEGIES`/strategy catalog so UI flows
  automatically. Target selection is an orthogonal loudness setting, not new catalog rows
  named Warmup/Peak (those mean energy strategies). [GROK R10]
- Whole-track integrated LUFS cannot see intro/outro jumps — documented v1 limitation;
  energy_in/energy_out exist for the same reason. [GROK R4]

## 5. Tag write-back (WU3) — CONTRACT EXCEPTION

**This feature makes XfinAudio write to audio files for the first time.** The read-only
guarantee in README (EN/ES), AGENTS.md and CONTRIBUTING.md is amended explicitly, with
tests pinning the new sentences. [GROK B9]

Per owner decisions ([OWNER], dissent registered in §14):

- Write-back is **always on** as part of analysis; values written only when changed
  (avoids touching files unnecessarily). [OWNER]
- COMMENT field is **overwritten** with the human-readable summary, frozen format:
  `{lufs:.1f} LUFS · {lra:.1f} LRA · {tp:.1f} dBTP`. Owner confirmed their library's
  comments hold no valued data. Reviewers' contrary evidence (28.1% populated comments
  historically, external tooling writes) recorded in §14.
- Structured custom tag `XFINAUDIO_LOUDNESS=lufs=…;lra=…;dbtp=…;v=1;engine=…` enables
  best-effort measurement recovery from tags if the DB is lost (no re-decode). DB remains
  source of truth; recovery completeness varies by format (strong: MP3 TXXX / FLAC Vorbis /
  M4A `----:com.bluesystemio.xfinaudio:XFINAUDIO_LOUDNESS`; weak: WAV/AIFF). [OWNER-approved dual write; GROK R13 limits]
- Round-trip stability: fixed decimal formatting prevents comment rewrite churn from
  float noise. [GROK N3]

## 6. Settings (WU4)

New `LoudnessSettings` (target LUFS, tolerance band, module toggle default ON) added
**without** bumping `CURRENT_SETTINGS_VERSION` (hard-equality rejection risk).
[GROK R9]

## 7. UI (WU4)

- Coverage/progress surface for the loudness stage (AppState currently models spectral
  completion only); immutable state transitions per existing pattern. [GROK R6]
- True-peak badge thresholds: warn `> −1.0 dBTP`, clip badge `>= 0.0 dBTP`. [GROK R11]
- Detail-pane display preferred over new library-table columns (table is a fixed
  12-column positional contract). If columns are added, `_TRACK_TABLE_COLUMN_WIDTHS`
  update is mandatory. [GROK N4]
- New UI strings require en/es translations like the rest of the desktop layer. [GROK N7]

## 8. Packaging (WU4)

- FFmpeg CLI binary added to `binaries=[]` in the PyInstaller spec — distinct from Qt
  Multimedia's bundled libav plugins, which are not invocable CLI executables. [GROK B5]
- Invoked by absolute bundle-relative path, never PATH. [GROK R14]
- Excluded from UPX processing. [GROK R15]
- Exact build (version/config/codecs/license) added to third-party license inventory
  before bundling. [GROK R16]
- Engine fingerprint changes force re-analysis by design; document the cost. [GROK R7]

## 9. Testing

- Unit: parser fixtures vs pinned build; command construction injectable (no real binary);
- Integration: RED-first regression for CASE inclusion (B7), identity-after-write (F5),
  sibling preservation via shared helper (F1/R12);
- Conformance: golden fixtures for LUFS/LRA/TP on synthetic WAVs;
- Governance: tests pinning amended read-only contract text (B9);
- Full suite green + coverage non-regression (baseline 91.14% post-prerequisite).

## 10. Future (explicitly out of scope v1)

Pairwise `|LUFS(A)−LUFS(B)|` handoff component (genuine mixability, orthogonal to band);
libebur128 binding behind profiling evidence; shared streaming decode fan-out; foreign
ReplayGain/R128 tag consumption.

## 14. Dissent log

| Decision | Owner choice | Reviewer position (recorded, not adopted) |
|---|---|---|
| COMMENT overwrite | Overwrite; library comments hold no valued data | OPUS F2 / GROK B3: repo measured 28.1% populated comments; external tools (/dj-metadata, /mik-analyze) write the field; proposed sentinel-delimited section preserving prior content |
| Toggle defaults | Analysis AND write-back always-on | OPUS F3 / GROK B8: split defaults — reading and writing are different risk classes; one confirmation dialog with real numbers |
| Scope shape | Single integrated module | GROK verdict: split into slices; measurement/filter core separated from write-back |
