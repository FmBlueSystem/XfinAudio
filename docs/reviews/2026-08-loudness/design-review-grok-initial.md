# Loudness module — final design critique (locked v2)

Last-pass review before the formal design document. Two prior reviewers locked the v2 decisions listed in the task prompt. This pass inspects the current tree and asks what still breaks, contradicts repo law, or should be simplified.

**Verdict:** Do not write the design as a single feature. Split it. The measurement/persistence/filter core can fit the existing architecture. Tag write-back, default-on full-library decode, and a pairwise loudness score cannot ship in the same slice without violating current safety rules or recreating bugs this codebase already paid to fix.

**Highest-leverage simplification:** v1 = bundled FFmpeg EBU R128 → DB profile → coverage UI → hard target-band pool filter. Defer COMMENT/custom-tag write-back. Do not add `ScoringWeights.loudness` until a weight is actually used.

---

## Ranked findings

Severity: **BUG** = wrong or self-contradictory against this repo today. **RISK** = will break under a normal library, upgrade, cancel, or packaging path. **NIT** = tighten in the design doc.

| ID | Sev | Finding | Concrete fix in the formal design |
|---|---|---|---|
| B1 | BUG | Dual tag write-back is currently illegal | Treat write-back as a separate, explicitly excepted change — or cut it from v1 |
| B2 | BUG | `audio_md5` does not protect MP3/M4A/WAV/AIFF after a tag write | Stop claiming tag writes never invalidate caches; persist identity without relying on FLAC-only MD5 |
| B3 | BUG | Overwriting COMMENT collides with Mixed In Key and is format-ambiguous | Do not overwrite COMM/©cmt/Vorbis `comment`. If tags are written at all, use only the structured custom field |
| B4 | BUG | Pairwise loudness scoring fights the locked whole-set semantics | v1 = pool filter + reporting only. Keep `loudness` out of `score_transition` |
| B5 | BUG | FFmpeg CLI is not what PyInstaller bundles today | Specify a pinned CLI binary in `binaries=[]`, distinct from Qt's libav plugins |
| B6 | BUG | First-enable full rescan + tag write races the preserve CASE | Do not rescan metadata on enable. Analyze in place. If tags are ever written, restat after write using the shared identity helper |
| B7 | BUG | A new JSON column that is omitted from `save_scan_results` is wiped on the next scan | Name the exact INSERT/CASE/ALTER sites; copy the spectral preserve pattern |
| B8 | BUG | Default-on full-file EBU R128 is not the same class of work as spectral | Default the toggle **off** for existing libraries; decode-whole-file must be opt-in with pause/ETA |
| B9 | BUG | Governance docs still forbid this work's two new behaviors | Design must include the AGENTS/CONTRIBUTING/README exception text and the tests that pin those sentences |

| ID | Sev | Finding | Concrete fix in the formal design |
|---|---|---|---|
| R1 | RISK | Fourth copy-paste worker vs 400-line budget | Chain: extract shared runner **or** accept a dedicated worker PR after measurement lands. Do not bolt loudness onto the spectral runner |
| R2 | RISK | Cancel does not kill child processes | FFmpeg must be a killable subprocess group; cancel must not allow a later tag write |
| R3 | RISK | Not-measured fail-open disagrees with energy filters | Keep the locked rule, but report coverage as a first-class warning and do not call the set "loudness-matched" |
| R4 | RISK | Whole-track integrated LUFS ignores intro/outro jumps | Document as v1 limit; energy already has `energy_in`/`energy_out` for this reason |
| R5 | RISK | `cpu_count-1` thread pools will thrash external drives | Separate disk-bound cap (2–3), not the librosa CPU default |
| R6 | RISK | Progress UI only covers spectral today | Add AppState + status-bar fields for the active completion stage before loudness can be seen |
| R7 | RISK | Engine fingerprint bump re-analyzes the whole library | Define when fingerprint changes force rebuild vs trust-and-display |
| R8 | RISK | `pyloudnorm` as oracle will disagree on true peak / gating | Golden FFmpeg stderr fixtures are the contract; pyloudnorm is LUFS-I sanity only, with epsilon |
| R9 | RISK | Settings version is a hard equality | Add `LoudnessSettings` **without** bumping `CURRENT_SETTINGS_VERSION` |
| R10 | RISK | Warmup/peak names already mean energy strategies | LUFS target is an orthogonal setting (or optional fields on existing strategies), not new catalog rows named Warmup/Peak |
| R11 | RISK | True-peak badge threshold is unspecified | Pick a number (recommend warn at `> -1.0 dBTP`, clip badge at `>= 0.0 dBTP`) |
| R12 | RISK | Cache-identity fix is a hard prerequisite | Loudness `update_*` must call the **shared** identity helper from that fix, not a fourth `SET file_mtime_ns` copy |
| R13 | RISK | WAV/AIFF custom tags are weak; recovery-from-tags is incomplete | Recovery is best-effort per format; DB remains source of truth |
| R14 | RISK | Two FFmpeg stacks in one app | Frozen app must invoke the bundled CLI by absolute path, never `PATH` |
| R15 | RISK | UPX is enabled in the spec | Exclude the FFmpeg binary from UPX |
| R16 | RISK | License inventory does not mention FFmpeg | Add the exact build (version, license, codecs) to `docs/third-party-license-inventory.md` before bundling |

| ID | Sev | Finding | Concrete fix in the formal design |
|---|---|---|---|
| N1 | NIT | Persist typed failures so corrupt files are not retried every scan | Status enum on the profile, retry only on version/fingerprint bump or explicit reanalyze |
| N2 | NIT | Minimum duration is unspecified | Spec it (EBU gating is meaningless on loops of a few hundred ms). Edge spectral already uses 65s as a typed skip |
| N3 | NIT | COMMENT summary rounding will rewrite tags | If write-back survives, freeze format (`{lufs:.1f}`, `{lra:.1f}`, `{tp:.1f}`) and write only on delta |
| N4 | NIT | Library table is already 12 columns with positional widths | Prefer detail pane + one TP badge over three new columns. Updating `_TRACK_TABLE_COLUMN_WIDTHS` is mandatory if columns are added |
| N5 | NIT | `dj_readiness.py` has BPM/energy continuity, not loudness | If a hard band exists, add a readiness check that counts out-of-band / not-measured tracks — do not duplicate scoring |
| N6 | NIT | Existing ReplayGain / R128 tags | Out of scope for v1; do not silently trust foreign loudness tags |
| N7 | NIT | i18n | New UI strings need `en`/`es` like the rest of the desktop layer |
| N8 | NIT | `ScoringWeights` / `SCORED_COMPONENTS` / bucket tuples must stay in lockstep | If a weight is added later, update all three plus every `PlaylistStrategy(...)` construction that should stay at 0.0 |

---

## B1 — Tag write-back vs current safety law

Locked decision 7 writes COMMENT and `XFINAUDIO_LOUDNESS` into audio files.

This repo currently has **no mutagen save path**. `read_mutagen_tags` is explicit:

```363:364:src/xfinaudio/library/scan_service.py
def read_mutagen_tags(path: Path) -> dict[str, Any] | None:
    """Read tags and duration from an audio file with mutagen without saving or modifying it."""
```

Non-negotiables that tests pin:

- `AGENTS.md`: "No audio mutation"
- `CONTRIBUTING.md` lines 48–51: "App writes must stay limited to app-owned database, settings, and export files"
- `tests/test_public_open_source_docs.py` requires README to contain `"does not mutate audio files"` and CONTRIBUTING to contain `"No audio mutation"` and `"app-owned database, settings, and export files"`

An opt-out setting does not make this a small feature. Shipping write-back requires changing product law, the tests that freeze that law, and the threat model (partial writes, AppleDouble, cloud-synced libraries, files open in Serato).

**Fix:** v1 writes only SQLite. Optional later PR: structured tag only, default off, never COMMENT. Backup/export of measurements as JSON/CSV is enough for "DB was deleted."

---

## B2 — `audio_md5` is not a general cache key

Locked decision 9: "audio_md5-first caching so tag write-back never invalidates measurements."

`audio_md5` is filled only from mutagen `info.md5_signature`:

```371:376:src/xfinaudio/library/scan_service.py
        signature = getattr(audio.info, "md5_signature", 0)
        if signature:
            tags["__audio_md5__"] = format(signature, "032x")
```

That field is the FLAC STREAMINFO checksum. Tests around `test_read_mutagen_tags_omits_absent_audio_md5` already show a missing signature omits the key. MP3, M4A, WAV, and AIFF — the rest of `SUPPORTED_AUDIO_EXTENSIONS` in `src/xfinaudio/library/scan_planning.py:8` — typically have `audio_md5 is None`.

Preserve logic then falls through to mtime+size:

```87:95:src/xfinaudio/library/track_repository.py
                    spectral_profile_json = CASE
                        WHEN excluded.spectral_profile_json IS NOT NULL THEN excluded.spectral_profile_json
                        WHEN tracks.audio_md5 IS NOT NULL
                             AND tracks.audio_md5 = excluded.audio_md5
                            THEN tracks.spectral_profile_json
                        WHEN tracks.file_mtime_ns = excluded.file_mtime_ns
                             AND tracks.file_size_bytes = excluded.file_size_bytes
                            THEN tracks.spectral_profile_json
                        ELSE NULL
```

Tag writes change size and mtime. Next scan therefore **NULLs spectral, danceability, and edge profiles** for every non-FLAC track, then the serialized workers re-decode the library. Loudness would join that wipe unless its column has the same CASE **and** identity still matches — which it will not, for MP3.

`plan_analysis_paths` / `try_cached_profile` (`src/xfinaudio/audio/analysis_planning.py:55-71`) also keys cache hits on mtime+size, not MD5.

**Fix:** Drop the "never invalidates" claim. If write-back exists at all, restat once after a successful write and update the shared identity in the same transaction as the loudness JSON, using the cache-identity helper from the in-flight sibling-profile fix. Prefer not writing tags.

---

## B3 — COMMENT overwrite is unsafe even if this library "has no notes"

Locked decision 7 overwrites COMMENT with `-9.8 LUFS . LRA 4.2 . TP -0.8 dBTP`.

The Mixed In Key contract **stopped** trusting comment energy because it disagreed 28.1% of the time (`src/xfinaudio/metadata/mixedinkey_contract.py:244-246`). Tests now assert comments are *not* parsed as energy (`tests/test_mixedinkey_contract.py:74-79`), but the files still *contain* those comments. The library status line still advertises them:

```197:200:src/xfinaudio/desktop/library_view_model.py
            "Scan: {0} · BPM (TBPM), key (TKEY), energy (COMM:Songs-DB_Custom1/comments)",
```

"Overwrite comment" is also underspecified across formats this scanner already supports:

| Format | Ambiguity |
|---|---|
| MP3 | Multiple `COMM` frames (`Songs-DB_Custom1`, empty description, language `eng` vs `XXX`) |
| FLAC | Vorbis `COMMENT` vs `DESCRIPTION` |
| M4A | `©cmt` |
| WAV | INFO `ICMT` is lossy/optional |

One maintainer library with empty notes is not a product default for everyone else, Rekordbox/Serato comments, or cloud copies.

**Fix:** Never overwrite COMMENT. Structured `TXXX` / Vorbis `XFINAUDIO_LOUDNESS` only, default off. Document per-format mapping in the design, including "WAV: do not write."

---

## B4 — Pairwise score vs whole-set anchor (pending bucket is a smell)

Locked decision 4: whole-set anchor, avoid pairwise drift.
Locked decision 8: weight default 0.0, mixability bucket "pending confirmation", plus a **hard** band around the user target.

`score_transition` is pairwise and has no access to a user LUFS target (`src/xfinaudio/recommendation/scoring.py:116-123`). Putting "distance from -9 LUFS" into a left/right score requires plumbing the target through `TransitionScoringConfig`. Putting "LUFS jump between neighbours" into mixability recreates the energy-arc failure already documented in `src/xfinaudio/recommendation/energy_arc.py:1-16`: the optimizer maximizes adjacent similarity and the set never moves.

The working precedent for a hard band is **not** a scoring weight. It is a pool filter:

- `PlaylistStrategy.energy_range` / `energy_tolerance` (`src/xfinaudio/recommendation/strategies.py:36-38`, `same_energy` at line 92)
- Applied in `playlist_service._apply_strategy_filters` and `_apply_energy_tolerance` (lines 649-664 and 1052-1073)

Default weight 0.0 plus `_weighted_total` using `SCORED_COMPONENTS` (`scoring.py:99-100, 416-433`) means an unused component is a no-op **only if** it is omitted from `SCORED_COMPONENTS` or kept at weight 0. Adding it to the mixability tuple while leaving the bucket "pending" is unfinished design.

**Fix:** v1 does not add a `loudness` field to `ScoringWeights`. Filter with `loudness_target_lufs` + `loudness_tolerance` analog to `energy_range`. Keep loudness **out** of `required_fields` (locked, and correct: missing required fields zero the whole transition at `scoring.py:142-153`). Revisit a pairwise component only after the energy-arc lesson has an explicit answer.

---

## B5 — Engine: Qt's FFmpeg is not an EBU R128 CLI

Locked decision 1 needs a pinned, bundled FFmpeg **executable** with `ebur128=peak=true`.

```24:28:packaging/pyinstaller/xfinaudio.spec
analysis = Analysis(
    [str(project_root / "src/xfinaudio/desktop/app.py")],
    pathex=[str(project_root / "src")],
    binaries=[],
```

`binaries=[]` is empty. The README's "FFmpeg libraries for audio preview" are Qt Multimedia plugins collected by PyInstaller hooks — the same stack `tests/conftest.py` and `src/xfinaudio/desktop/audio_player.py` already fight at teardown. Those dylibs do not expose `ffmpeg -filter_complex ebur128`.

Dev `PATH` FFmpeg will not match the shipped build, which breaks the locked conformance-fixture story.

Also: `upx=True` (`xfinaudio.spec:67, 81`) has a history of breaking executables; the FFmpeg binary must be in `upx_exclude`. `codesign_identity=None` — a nested unsigned CLI inside an unsigned `.app` is a notarization problem later, not a v1 blocker, but the design should not pretend the binary is "just another Python package."

**Fix:** Pin version + exact configure flags. Ship one static (or well-rpathed) CLI. Preflight: exists, runs, `ebur128` filter present, version string matches fingerprint. Unit tests parse **checked-in stderr**; integration tests against that binary are opt-in. Keep `pyloudnorm` in a test extra, never a runtime dependency (`pyproject.toml` does not include it today — keep it that way).

Capability preflight must fail closed in the UI when the CLI is missing (dev checkout without Homebrew). Do not call `ffmpeg` from `PATH` in a frozen app.

---

## B6 — First activation full rescan is unjustified and dangerous

Locked decision 5: first enable → full rescan + analysis because "metadata may have changed."

Enabling a toggle does not change audio files. A full metadata rescan:

1. Re-stats every file (`_record_to_row` at `track_repository.py:459-466`)
2. Rewrites identity columns
3. Interacts with the still-open sibling-profile identity bug (`update_spectral_profile` at lines 168-196 blindly `SET file_mtime_ns, file_size_bytes`)
4. If tag write-back already ran, non-FLAC identity mismatches drop expensive profiles (B2)

Spectral/danceability/edge already **lazy-complete after scan** without a forced rescan (`library_controller.py:408-439`, then danceability, then edge).

**Fix:** First enable starts the loudness completion stage on current `TrackRecord`s. Incremental afterwards, keyed by `analysis_version` + engine fingerprint + typed failure status. Persist `loudness_analysis_enabled` and `loudness_initialized_at` in settings so re-enable is not a second "first activation." Deactivate = cancel worker, keep JSON.

---

## B7 — Persistence must copy the full preserve pattern

Locked decision 2 (one `loudness_profile_json` column + versioned Pydantic model) is the right shape. `SpectralProfile` already shows the pattern (`analysis_version` in `src/xfinaudio/audio/spectral_profile.py:56-68`).

The miss is operational. Adding a column requires **all** of:

1. `CREATE TABLE` / `ALTER TABLE` in `_ensure_schema` (`track_repository.py:429-449`)
2. INSERT column list and placeholders (`63-69`)
3. ON CONFLICT preserve CASE (`87-118`) — without this, the next scan sets the new column to NULL
4. `_record_to_row` / `_row_to_record` / display query (`145-161`)
5. `TrackRecord` field (`src/xfinaudio/library/models.py:15-39`)
6. A repository port like the three existing cache ports (`src/xfinaudio/library/ports.py:30-46`)
7. `app_state_transitions.apply_*_profile` analog

Do **not** overload `metadata_status` (`Literal["complete", "incomplete"]`, models.py:12). Loudness needs its own status on the profile: `measured | unsupported | corrupt | too_short | engine_failed`.

Failed runs must persist that status (N1). Spectral currently stores `None` and retries forever (`spectral_completion_worker.py:80`: any `None` or stale version is pending). That is painful once each attempt is a full-file FFmpeg decode.

---

## B8 — Whole-file decode is a different product from 30-second spectral

`analyze_spectral_profile` loads **30 seconds** of mono 22050 Hz (`spectral_profile.py:35-40, 108-122`). Edge spectral skips tracks under 65 seconds (`_MIN_EDGE_TRACK_SECONDS`, line 41, 202-203).

EBU R128 integrated loudness plus true peak requires decoding **the whole stream** at native rate. On a multi-thousand-track DJ library on USB HDD, default-enabled (decision 5) means hours, heat, and disk contention **after** three already-serialized librosa passes (`library_controller.py:537-538` comment: pools must not overlap).

`_default_max_workers_for_analysis` is `cpu_count-1` (`spectral_completion_worker.py:38-40`). That is a CPU default. FFmpeg is decode + disk. Eight concurrent whole-file reads on an external drive will serialize in hardware and look like a hang.

**Fix:** Default analysis **off** on upgrade. Cap loudness concurrency at 2 (maybe 1 if the folder is non-local). Pause/resume. ETA on the coverage surface. Do not start loudness until the librosa chain has finished (the existing serialized lifecycle is the right hook — R1).

---

## B9 — DSP/mutation exceptions must be written down

Read-only EBU R128 is the same *class* of work as librosa spectral/danceability (already in tree), not BPM detection. Tag write-back is not.

`docs/xfinaudio-stack-and-scope-decision.md` still says the product is metadata-driven and lists DSP as out of MVP. Spectral already expanded that in practice; loudness should not sneak through.

**Fix:** Formal design opens with two named exceptions:

1. Read-only loudness measurement via bundled FFmpeg (in-scope, like spectral).
2. Audio file tag writes (out of scope unless the maintainer amends AGENTS/CONTRIBUTING/README and the tests in `tests/test_public_open_source_docs.py` / `tests/test_github_community_templates.py`).

---

## R1 — Workers: serialize yes; copy-paste no; merge into spectral also no

The three ~279-line workers are already **serialized**, not parallel:

`start_spectral_completion_worker` → `on_spectral_completion_finished` → `start_danceability_completion_worker` → `on_danceability_completion_finished` → `start_edge_spectral_completion_worker` (`library_controller.py:410-586`).

Locked decision 9 matches that lifecycle. A fourth near-copy plus `shutdown()` (`451-475` currently names two workers in the docstring and three in the body) will blow the 400-line review budget by itself.

Bolting FFmpeg into `_SpectralCompletionRunner` couples disk-bound CLI work to librosa and makes cancellation/ Copied identity updates worse.

**Fix:** Chained PRs. Preferred: a tiny "generic completion runner" PR with no behavior change, then a loudness adapter. Acceptable: a fourth worker in its own PR after measurement+DB exist. Forbidden: loudness fields hidden inside the spectral worker.

`TrackRepositoryPort` is already split per profile; a fourth port is consistent. Do not invent a parallel `batch_analyzer.py` path — workers do not use `analyze_paths` today.

---

## R3 — Not-measured inclusion vs energy's fail-closed filters

Decision 6: typed not-measured tracks are **excluded from target filtering** (they stay in the pool) with a warning.

Energy range does the opposite — missing `energy_level` drops the track unless it is a preserved control:

```656:660:src/xfinaudio/recommendation/playlist_service.py
        filtered = [
            track
            for track in filtered
            if track.path in preserve_paths or (track.energy_level is not None and low <= track.energy_level <= high)
        ]
```

Same for `_apply_energy_tolerance` (lines 1063-1068).

Fail-open is the locked call. The design must then **forbid** copy like "this set is matched to -9 LUFS" whenever `not_measured > 0`. Surface `measured / out-of-band / not-measured` on the recommendation and readiness reports. `quality/dj_readiness.py` currently checks playlist size, metadata, BPM continuity, energy continuity, warnings, average score (lines 70-77) — add a loudness coverage check there, not a fake pairwise score.

---

## R4 — Whole-track I is a set-level knob, not a mix-point knob

MIK energy already split whole-track vs edges (`energy_level` vs `energy_in` / `energy_out`; scoring uses handoff when both exist, `scoring.py:328-334`). A track can be -9 LUFS integrated with a -18 LUFS intro. v1 will not see that. Say so. Do not schedule intro/outro ebur128 windows in the first design unless the chain explicitly budgets a later PR.

LRA as informational and true peak as a badge (decision 8) is correct — keep them out of the optimizer.

---

## R6 / N4 — UI surfaces that actually exist

Decision 10: reuse strategy catalog; add coverage/progress; LUFS/LRA/dBTP columns or detail; TP badge.

What exists:

- Strategy catalog is `PlaylistStrategy` + `StrategyRegistry` (`strategies.py`). LUFS target should be optional fields or a global `LoudnessSettings.target_lufs`, **not** new names `warmup` / `peak_time` (those already mean energy 1–6 and 7–10).
- Progress: `AppState.is_completing_spectral` + two counters (`app_state.py:79-81`). Danceability and edge have **no** progress fields and do not update the status line (`library_view_model.py:164-168` only mentions spectral). Loudness will be invisible unless this is generalized to "active completion stage."
- Library columns: 12 already (`library_screen.py:25-38`) with positional widths `_TRACK_TABLE_COLUMN_WIDTHS` (`theme.py:9`).
- Review recommendation table: `# Title Artist BPM Key Energy Color` (`review_screen.py:29`). Transition widths must stay aligned with `_TRANSITION_COLUMNS` (`theme.py:12-15`).
- Settings dialog has language, export folder, last-scan label only (`settings_dialog.py`). A default-enabled analysis toggle and tag opt-out have no home yet — they belong here, with `LoudnessSettings` on `AppSettings` (`settings.py:83-96`) **without** bumping `CURRENT_SETTINGS_VERSION` (validator rejects any other value, lines 98-103).

Prefer: one LUFS column, TP badge in Status/detail, LRA in the metadata/detail view. Do not add three columns to library, review, export, and metadata tables in one PR.

---

## R10 — Product semantics: target vs strategy vs energy arc

"User-selectable LUFS target (warmup -14, peak -9)" and "reuse existing strategy catalog" pull in opposite directions.

Recommended lock for the design doc:

- Global or per-strategy **numeric** target + tolerance (like `energy_range=(7,10)`), e.g. peak_time → target -9, warmup → target -14, others → unset (no loudness filter).
- Independent of `energy_arc.py` journey/peak/chill curves. Those shape MIK energy 1–10. LUFS is a measured floor. A peak-time energy set at streaming -14 LUFS is a valid DJ choice; do not hide it.

"Tracks outside target band excluded with clear reporting" maps to `_apply_strategy_filters` warnings (`Filtered N track(s) outside ... energy range`). Copy that, including the count.

---

## R12 — Do not start until the cache-identity fix lands — and do not fork its helper

Confirmed still present in this tree: each `update_*_profile` writes shared `file_mtime_ns` / `file_size_bytes` without checking sibling profiles (`track_repository.py:168-196`, `229-254`, `283-308`). That is the prerequisite bug.

Loudness must use the **post-fix** helper. A fourth copy of the broken UPDATE reintroduces the bug on day one.

---

## Engine / analyzer shape (keep)

`src/xfinaudio/audio/analyzer.py` is the right home: frozen dataclass adapters behind Protocols (`SpectralAnalyzer`, `DanceabilityAnalyzer`, `EdgeSpectralAnalyzer`). Add `LoudnessAnalyzer` with `analyze(path) -> LoudnessProfile` (profile includes status, never a silent `None` for corrupt/too-short). Adapter owns subprocess details; port does not mention FFmpeg so libebur128 can replace it later (decision 1).

CLI invocation must include `-nostdin`, a timeout, and process-group kill. Parse Integrated I, LRA, and true peak from stderr against fixtures captured from the **shipped** binary. `ebur128=peak=true` is the right filter flag for dBTP.

Too-short / unsupported / corrupt → typed status, not a simulated -14 LUFS or 0.5 score (decision 6). Good. Do not reuse spectral's `return None`.

Supported extensions stay `.aif .aiff .flac .m4a .mp3 .wav`. No extra formats in this change.

---

## Suggested chain (stay under 400 lines)

| PR | Scope | Notes |
|---|---|---|
| 0 | Cache-identity sibling invalidation | Already in flight. Hard gate. |
| 1 | `LoudnessAnalyzer` port + FFmpeg adapter + stderr fixtures + preflight | No DB, no UI |
| 2 | `LoudnessProfile` + column + preserve CASE + repository port + TrackRecord | No worker |
| 3 | Generic completion runner **or** fourth worker + AppState progress | Serialized after edge |
| 4 | `LoudnessSettings` (default **off**) + toggle pause/keep data | No tag writes |
| 5 | Pool filter + warnings + readiness coverage | No `ScoringWeights` field |
| 6 | LUFS column / detail / TP badge / strategy optional target | Width tuples + i18n |
| 7 (optional, separate exception) | Structured tag write, default off, never COMMENT | Only after B1/B2/B3 are closed in docs/tests |

Do not combine 1–6. Do not put 7 in the first design's "done" criteria.

---

## What checked out clean

These locked decisions match the tree and should survive into the design:

- Analyzer **port** next to `LibrosaSpectralAnalyzer` (`analyzer.py`).
- Single versioned Pydantic JSON column, same as `spectral_profile_json` / `danceability_profile_json` / `edge_spectral_profile_json`.
- `analysis_version` invalidation already used by workers (`CURRENT_ANALYSIS_VERSION` / `CURRENT_DANCEABILITY_VERSION` / `CURRENT_EDGE_ANALYSIS_VERSION`).
- Serialized completion lifecycle already in `LibraryController` (do not run a fourth CPU/disk pool beside librosa).
- Hard band precedent: `energy_tolerance` / `energy_range`, not a soft-only weight.
- Neutral 0.5 for unevaluable components (`NEUTRAL_COMPONENT_SCORE`, `scoring.py:109, 416-424`) — if a weight is added later.
- Keeping loudness **out** of `required_fields` (`camelot_key`, `bpm`, `energy_level` only, `scoring.py:93`).
- Immutable `TrackRecord` / `ScoringWeights` / `PlaylistStrategy` (`model_copy`, no in-place mutation).
- `AppState.model_copy(update=...)` already used by completion (`library_controller.py:634-636`).
- Cancellation tokens + `dispose_when_idle` (FFmpeg still needs a real kill — R2).
- libebur128 deferred; pyloudnorm not in runtime deps.
- LRA informational, true peak not in the optimizer.
- Deactivate-keeps-data is compatible with leaving JSON in SQLite.

---

## Files inspected

| Area | Paths |
|---|---|
| Analyzer ports | `src/xfinaudio/audio/analyzer.py`, `batch_analyzer.py`, `analysis_planning.py`, `spectral_profile.py` |
| Workers / UI lifecycle | `desktop/spectral_completion_worker.py`, `danceability_completion_worker.py`, `edge_spectral_completion_worker.py`, `library_controller.py`, `app_state.py`, `library_view_model.py`, `settings_dialog.py`, `settings.py` |
| Persistence | `library/track_repository.py`, `library/models.py`, `library/ports.py`, `library/scan_service.py`, `library/scan_planning.py` |
| Scoring / strategies | `recommendation/scoring.py`, `strategies.py`, `playlist_service.py`, `energy_arc.py`, `quality/dj_readiness.py` |
| Tags / MIK | `metadata/mixedinkey_contract.py`, `tests/test_mixedinkey_contract.py`, `tests/test_scan_service.py` |
| UI tables | `desktop/screens/library_screen.py`, `review_screen.py`, `theme.py` |
| Packaging / policy | `packaging/pyinstaller/xfinaudio.spec`, `pyproject.toml`, `AGENTS.md`, `CONTRIBUTING.md`, `docs/third-party-license-inventory.md`, `docs/xfinaudio-stack-and-scope-decision.md`, `tests/test_public_open_source_docs.py` |
| Cache-identity tests | `tests/test_track_repository.py` (md5 preserve vs mtime fallback) |

No source files were modified. This document is the only write for this review.
