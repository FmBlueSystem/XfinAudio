# Proposal: add-loudness-module

## Why

XfinAudio reads BPM/key/energy metadata but never measures what actually breaks a DJ
transition between formats: **loudness inconsistency**. An MP3 master at −6 LUFS next to a
FLAC master at −10 produces audible volume jumps on the dancefloor. The library currently
has no way to detect this, and the recommendation engine cannot reason about it.

## What Changes

Add an EBU R128 loudness measurement module (integrated LUFS, LRA, true peak dBTP) to
XfinAudio:

1. A `LoudnessAnalyzer` port with a pinned, bundled FFmpeg adapter (`ebur128=peak=true`)
2. A versioned `LoudnessProfile` persisted per track alongside existing analyzer profiles
3. A user-selectable LUFS target band implemented as a pool filter for playlist strategies
4. Always-on tag write-back: human-readable summary in COMMENT plus a structured custom tag
   (`XFINAUDIO_LOUDNESS`) enabling measurement recovery from tags alone
5. Coverage/progress UI surfaces and a true-peak clipping badge

## Capabilities

### New: loudness-analysis

Measurement, persistence, target-band filtering, and tag write-back for EBU R128 metrics.

## Impact

- **Modified contract**: this is the first XfinAudio feature that writes to audio files.
  The documented read-only scanning guarantee (README lines 74/126/495/728/779,
  AGENTS.md, CONTRIBUTING.md) must be amended explicitly, with tests pinning the new text.
- **Prerequisite**: `fix-derived-profile-cache-identity` (landed, verified: 1,691 tests,
  Pyright clean, 91.14% coverage). Loudness persistence must reuse its shared identity
  helper — not introduce a fourth `SET file_mtime_ns` copy.
- **Packaging**: `packaging/pyinstaller/xfinaudio.spec` gains its first external binary
  (FFmpeg CLI), with UPX exclusion and third-party license inventory updates.
- **Out of scope (v1)**: pairwise LUFS transition scoring component, libebur128 in-process
  binding, shared streaming decode layer, ReplayGain/R128 foreign-tag consumption.

## Decision provenance

Design decisions were debated across three independent reviews (Claude Opus, Codex
gpt-5.6-sol, Cursor Grok 4.6-high) against locked product-owner choices. Divergences
between reviewer recommendations and owner decisions are recorded in `design.md` §14
(dissent log).
