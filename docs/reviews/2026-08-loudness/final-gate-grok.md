# Final merge gate — `add-loudness-module` (Grok)

Reviewed committed HEAD `2e3ac26` (`fix(loudness): remediate WU2 gate findings`) in sibling worktree `/Users/freddymolina/orca/workspaces/xfinaudio-local-main/loudness-review-codex`. This worktree was not modified except for this file. Tests were not executed here; `IMPLEMENTATION-NOTES.md` was scored for credibility against the code.

Owner overrides (COMMENT overwrite, always-on write-back, single integrated module) are accepted and not re-argued. They are recorded in `openspec/changes/add-loudness-module/design.md` §14.

## Verdict

**Historical at `2e3ac26`: BLOCKERS.** Current re-check of `e9e5802` / `a12dac8` / `fc8972e` / `54e2600`: see **[N1 Re-check](#n1-re-check)** — **MERGE-READY**.

Checklist items 1–4 and most of 5 are implemented. Merge was blocked by a new product hole: the library scans `.m4a` as a first-class format, but the pinned bundled FFmpeg cannot demux or decode it, and the tag writer has no MP4 family. That combination leaves Apple/iTunes libraries unmeasured (and untagged) in the frozen app.

## Checklist

| Item | Finding | Status | Evidence |
|---|---|---|---|
| 1a | B5 — FFmpeg CLI bundled as a binary distinct from Qt libav | **fixed** | `packaging/pyinstaller/xfinaudio.spec:10`, `:57`, `:78` (`binaries=[(str(bundled_ffmpeg), ".")]`); Qt Multimedia remains a separate hiddenimport (`:94`). Spec validates a standalone executable (`validate_ffmpeg_bundle`, `:22-37`) with ebur128 true-peak help text, not libav dylibs. |
| 1b | R14 — frozen invocation is bundle-absolute, never `PATH` | **fixed** | `src/xfinaudio/audio/loudness_runtime.py:20-28`: if `frozen`, resolve `(Path(_MEIPASS) / "ffmpeg").resolve()` and never call `which`. `tests/test_loudness_runtime.py:21-25` asserts the `which` callback is not used. Unfrozen PATH fallback is explicit and documented as unsupported. Adapter argv starts with that absolute executable (`src/xfinaudio/audio/loudness.py:130-146`, `shell=False`). |
| 1c | R15 — UPX exclusion of `ffmpeg` | **fixed** | `packaging/pyinstaller/xfinaudio.spec:135` `upx_exclude=["ffmpeg"]` on `COLLECT` (the step that holds the CLI; `EXE` is `exclude_binaries=True`). `tests/test_pyinstaller_packaging.py:357-366` pins the exclude string. |
| 1d | R16 — license inventory entry | **fixed** | `docs/third-party-license-inventory.md:22-53` (FFmpeg 7.1.1, SHA-256, LGPL-2.1-or-later, `--disable-gpl`/`--disable-nonfree`, exact enable flags, `_MEIPASS/ffmpeg`, corresponding-source offer). Same strings asserted in `tests/test_pyinstaller_packaging.py:371-384`. |
| 2 | B7 — `loudness_profile_json` inside `save_scan_results` CASE | **fixed** | `src/xfinaudio/library/track_repository.py:70`, `:121-124`. CASE keeps an existing payload (`WHEN tracks.loudness_profile_json IS NULL THEN excluded… ELSE tracks…`). `tests/test_track_repository.py:1246` (`test_save_scan_results_preserves_existing_loudness_profile_json_on_ordinary_rescan`). Shape differs from spectral (no md5/mtime clause); that is a residual, not a wipe-on-scan bug. See new defects. |
| 3 | `2e3ac26` — `.m4a` in `_METADATA_REFRESH_SUFFIXES` + parametrized test | **fixed** (narrow) | `src/xfinaudio/library/track_repository.py:32`; `tests/test_track_repository.py:1380` parametrize includes `.m4a`. Commit `2e3ac26` is exactly that plus display-read/reanalyze wiring. **Not sufficient** for `.m4a` as a loudness format — see N1. |
| 4a | N4 — detail pane, no new table columns | **fixed** | Library column tuple still 12 entries (`src/xfinaudio/desktop/screens/library_screen.py:25-38`). Pane + badge built in `library_screen_builder.py:161+`; renderer `library_screen_rendering.py:123-176`. |
| 4b | N7 — en/es translations | **fixed** | `translations/xfinaudio_en.ts` / `xfinaudio_es.ts` (e.g. es `:247-261`, `:1144`). `tests/test_loudness_translations.py` requires finished translations and QM load. `2e3ac26` adds “Reanalyze loudness” / “Volver a analizar sonoridad”. |
| 4c | R11 — true-peak badge `> -1.0` warn, `>= 0.0` clip | **fixed** | `library_screen_rendering.py:169-176`; `tests/test_library_screen.py:209-221` matrix `(0.0, clip), (-0.5, warning), (-1.0, ""), (-1.1, "")`. |
| 5 | B9 — governance amendment pinned by tests | **partial** | Exception sentence is in `AGENTS.md:28`, `CONTRIBUTING.md:48`, `README.md:126` and pinned by `tests/test_public_open_source_docs.py:88-105`. Gaps: (a) sentence says writes happen “only through its explicit setting”, but `LoudnessSettings.enabled` (`src/xfinaudio/config/settings.py:73-78`) only gates **scheduling**; `LoudnessCompletionService` always calls `write_loudness_tags` (`loudness_completion.py:52-53`, `:109`). (b) `SECURITY.md:27` still says “XfinAudio does not mutate audio files.” and that fragment is still required (`test_public_open_source_docs.py:116`). (c) GitHub templates still require unqualified “No audio mutation” (`tests/test_github_community_templates.py:42`, `:61`, `:81`). |

## New defects (not in the original B/R/N list)

| ID | Sev | Defect | Evidence |
|---|---|---|---|
| N1 | **BLOCKER** | Bundled FFmpeg cannot open `.m4a`, which is a scanned library format. Configure is `--disable-everything` plus demuxers `aiff,flac,mp3,wav` and decoders `flac,mp3,pcm_*` only. No `mov`/`mp4` demuxer, no `aac`/`alac`. Frozen analysis of iTunes/Apple Music files will fail. Tag writer also has no MP4 family (`loudness_tags.py:18-19`, `:47-48`), so always-on write-back is a no-op for `.m4a`. Adding `.m4a` to `_METADATA_REFRESH_SUFFIXES` does not close this. | `scripts/build_ffmpeg_universal.py:36-68`; `src/xfinaudio/library/scan_planning.py:8`; `src/xfinaudio/audio/loudness_tags.py:18-48` |
| N2 | RISK | `save_scan_results` loudness CASE never drops JSON on audio replacement (unlike spectral, which NULLs on md5/mtime mismatch). Display reads deserialize that JSON with no identity check (`track_repository.py:672`, `:696`). Cache loader *does* check profile-owned mtime/size (`:486-487`). After a replaced file is rescanned, the detail pane can show the previous file’s LUFS until completion rewrites it. | `track_repository.py:89-124` vs `:459-487` vs `:675-696` |
| N3 | RISK | Completion always invokes the tag writer after `analyze()`, with no cancelled-run guard in the `as_completed` loop. Cancel marks FFmpeg PIDs and returns `TRANSIENT_FAILURE` (`loudness.py:183-185`); writer then no-ops for incomplete profiles (`loudness_tags.py:47-48`). Safe for MEASURED-only writes, but a late `analyze()` that still returns MEASURED after cancel would write. No test covers “cancel then no tag save”. | `loudness_completion.py:96-124`; `loudness.py:199-204` |
| N4 | NIT | `IMPLEMENTATION-NOTES.md` WU2 citations are *mostly* right after `2e3ac26` (`library_controller.py:262-269`, `:753-761`, `library_screen_rendering.py:109-176`) but `window_factory.py:226-238` is `with_defaults` / `restore_persisted_tracks`, not a dedicated loudness delivery function. Full-suite “1802 passed / 91.14% coverage” is not in-repo log evidence. | `IMPLEMENTATION-NOTES.md:199-203`; `window_factory.py:226-239` |

## Owner overrides (not re-opened)

| Override | Observed in code |
|---|---|
| COMMENT overwrite | `loudness_tags.py:175-176`, `:185-188` (`COMM` delall + rewrite; FLAC `COMMENT`) |
| Write-back always on | Default `tag_writer=write_loudness_tags`; no settings flag on the writer |
| Single integrated module | One change (`openspec/changes/add-loudness-module/`) covering engine through UI |

Scoring still has no `loudness` weight (`src/xfinaudio/recommendation/scoring.py:20-31`). Pool filter is fail-open for unmeasured tracks (`playlist_service.py:678-687`), matching locked R3.

## `IMPLEMENTATION-NOTES.md` credibility

| Claim class | Credibility |
|---|---|
| Packaging contract (bundle dest `.`, UPX exclude, inventory strings, preflight) | **High** — mirrored by `tests/test_pyinstaller_packaging.py` and the spec/runtime files above. This reviewer did not rebuild FFmpeg or the `.app`. |
| WU2 display-path + `.m4a` suffix + reanalyze | **High** — matches `2e3ac26` diff and current line ranges for controller/renderer/repository. |
| Full pytest 1802 / coverage 91.14% / “release gate passed” | **Unverified here** (instruction: do not run tests). No captured stdout/junit in the tree. Treat as author report, not gate evidence. |
| Real universal2 FFmpeg + temp PyInstaller bundle | **Plausible** (scripts and validators exist: `scripts/build_ffmpeg_universal.py`, `scripts/pyinstaller_build_smoke.py:204-226`) but not independently reproduced in this review. |

## Merge condition

Unblock when bundled FFmpeg can actually decode every `SUPPORTED_AUDIO_EXTENSIONS` entry (at minimum `mov`/`mp4` demux + `aac`/`alac`), with a frozen-path test that a fixture `.m4a` yields `MEASURED` or a typed `UNSUPPORTED` that the UI does not present as a generic failure — and when tag write-back for `.m4a` is either implemented or explicitly listed as unsupported in the user-facing coverage copy.

Optional before merge (not sufficient alone): align `SECURITY.md` / GitHub templates with the loudness write exception; identity-gate the loudness CASE or display path the same way cache loads already do.

## N1 Re-check

Read-only verification of Codex sibling HEAD `54e2600` (`docs(sdd): record N1 gate remediation`) against the original N1 merge condition and N3 race. Commits on top of reviewed `2e3ac26`: `e9e5802`, `a12dac8`, `fc8972e`, `54e2600`. This worktree was not modified except for this file. Tests were not executed here. Owner overrides are not re-opened.

### 1. N1 decode — unblocked (`e9e5802`)

**Status: closed.** Bundled FFmpeg can now decode every `SUPPORTED_AUDIO_EXTENSIONS` entry (`.aif`, `.aiff`, `.flac`, `.m4a`, `.mp3`, `.wav`).

| Extension | Demuxer / decoder surface |
|---|---|
| `.aif` / `.aiff` | `--enable-demuxer=aiff` (pre-existing) |
| `.flac` | `--enable-demuxer=flac` / `--enable-decoder=flac` (pre-existing) |
| `.mp3` | `--enable-demuxer=mp3` / `--enable-decoder=mp3` (pre-existing) |
| `.wav` | `--enable-demuxer=wav` / `pcm_s16*` / `pcm_s24*` / `pcm_s32*` (pre-existing) |
| `.m4a` | `--enable-demuxer=mov` + `--enable-decoder=aac` + `--enable-decoder=alac` (**new**) |

Build script `scripts/build_ffmpeg_universal.py` `CONFIGURE_FLAGS` (`:50-64`) includes those three M4A flags. `_validate_binary` / `_has_m4a_decode_capabilities` (`:137-146`) fail closed unless `-demuxers` shows `mov` and `-decoders` shows `aac` and `alac`. The same probe is in `packaging/pyinstaller/xfinaudio.spec:37-49` and `scripts/pyinstaller_build_smoke.py`. Tests pin the flags in `tests/test_ffmpeg_build.py` and `tests/test_pyinstaller_packaging.py`.

Real fixtures exist: `tests/fixtures/loudness/synthetic_tone_1khz_aac.m4a` and `synthetic_tone_1khz_alac.m4a`. Frozen-path test `tests/audio/test_loudness.py::test_frozen_resolved_ffmpeg_measures_real_synthetic_m4a` (`:405-429`) resolves via `resolve_ffmpeg(frozen=True, bundle_dir=...)` and asserts `MEASURED` on both fixtures.

Residual (not a reopen of N1): that frozen test **skips** if neither `XFINAUDIO_FFMPEG_BINARY` nor `PATH` ffmpeg is present, and when it runs it uses that developer binary (symlinked into a fake bundle), not necessarily the pinned 7.1.1 artifact. Packaging validators still fail closed on the actual bundled binary’s demuxer/decoder list. HE-AAC / xHE-AAC / unusual codecs inside `.m4a` are outside the stated AAC-LC + ALAC contract.

### 2. M4A tag writer — correct (`a12dac8`)

**Status: closed.** Writer uses mutagen MP4 family for `.m4a` only.

- Overwrites iTunes comment `©cmt` with the human LUFS/LRA/dBTP string (`loudness_tags.py:201-206`). This is the owner-approved COMMENT overwrite, not a foreign-atom wipe.
- Writes the app-owned freeform atom `----:com.bluesystemio.xfinaudio:XFINAUDIO_LOUDNESS` as a single `MP4FreeForm` UTF-8 value (`AtomDataType.UTF8`).
- Does **not** `delall` other MP4 atoms. Unrelated `©nam` and `----:com.example:UNRELATED` survive (`tests/audio/test_loudness_tags.py:150-172`); a second write is idempotent (no save).
- Recovery is exact-key, UTF-8, single-value (`_matches_loudness_key` is case-sensitive for MP4; `_mp4_utf8_text` rejects non-UTF-8 / binary / multi-value). Foreign comment text and foreign freeform atoms do not recover (`tests/test_loudness_tag_recovery.py:107-131`).

No foreign-data loss beyond the approved `©cmt` overwrite.

### 3. N3 cancel/commit race — closed (`fc8972e`)

**Status: closed.** Late `MEASURED` results cannot start a tag write after cancel.

`LoudnessCompletionService` now has a per-run token, `_cancelled_runs`, and `_commit_run`. `cancel()` marks the run cancelled, cancels the analyzer, then **waits while `_commit_run is run`**. The `as_completed` loop breaks if cancelled (`loudness_completion.py:117-119`). `_begin_commit` returns `False` if the run is cancelled (`:170-175`), so a late `analyze()` that still returns `MEASURED` cannot enter `_commit_profile` (no tag write, no refresh, no persist, no callbacks). An already-started commit is allowed to finish; later records are skipped.

Tests:

- `test_cancel_wins_before_late_measurement_commit_and_service_can_be_reused` — late MEASURED after cancel: no write/persist/callbacks; service reusable.
- `test_cancel_waits_for_active_tag_commit_then_skips_remaining_records` — in-flight commit completes; remaining records do not commit.

That is the original N3 hole.

### Residuals not in this re-check

Unchanged from the `2e3ac26` gate: **N2** (loudness CASE never drops JSON on file replace) remains RISK; **B9** (SECURITY.md / GitHub templates / “explicit setting” wording vs always-on writes) remains partial. Neither was the stated merge condition.

### Final verdict

**MERGE-READY**

N1 is unblocked, M4A write-back is implemented with the approved COMMENT overwrite and no extra foreign-atom loss, and N3 is closed. Optional residuals N2 and B9 may still be tracked after merge.
