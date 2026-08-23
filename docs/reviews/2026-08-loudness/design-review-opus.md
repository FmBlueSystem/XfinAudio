# Loudness Module (EBU R128) — Design Review

Reviewer: independent design reviewer (Claude Sonnet 5)
Scope: proposed loudness measurement module (WU1–WU4) against the current codebase.

Files inspected: `src/xfinaudio/audio/analyzer.py`, `audio/batch_analyzer.py`,
`audio/analysis_planning.py`, `audio/spectral_profile.py`,
`library/models.py`, `library/track_repository.py`, `library/scan_service.py`,
`recommendation/scoring.py`, `recommendation/strategies.py`,
`desktop/spectral_completion_worker.py`, `packaging/pyinstaller/xfinaudio.spec`,
`pyproject.toml`.

---

## 1. Implementation verdict

| Option | R128 compliance | True peak | Speed | macOS/PyInstaller packaging |
|---|---|---|---|---|
| `ffmpeg -af ebur128=peak=true` subprocess | Good (ffmpeg's `ebur128` filter wraps libebur128) | Yes, but output must be scraped from **stderr text**, not a typed return value | Subprocess = no GIL contention at all (`Popen`/`waitpid` releases the GIL natively) — better concurrency than in-process librosa work | **No ffmpeg binary exists anywhere in this repo today.** `packaging/pyinstaller/xfinaudio.spec:27` has `binaries=[]` and no ffmpeg `hiddenimports`. This is a new, unbudgeted packaging problem: bundle a static universal2 (arm64+x86_64) ffmpeg binary, reference it via `sys._MEIPASS`-relative path (never assume a user's Mac has `ffmpeg` on `PATH`), and get it through notarization/codesigning like the rest of `XfinAudio.app`. |
| `libebur128` binding (cffi/ctypes over the reference C library) | Best — it *is* the reference implementation most tools (including ffmpeg) wrap | Yes, native, typed | Fast, no process-spawn overhead per file | Same class of problem as ffmpeg (a compiled `.dylib` needs `binaries=[]` → non-empty and correct rpath in the PyInstaller spec) but smaller surface: one shared library, no stderr parsing, no separate CLI process to launch per file. |
| `pyloudnorm` (pure Python + scipy) | Weaker — its gating/filtering deviates from the reference implementation on short or quiet material, and it does **not** implement compliant oversampled true-peak detection | No reliable true peak | Slowest (pure Python filtering over full-length arrays) | Easiest to package — no new binary, `scipy` is a plain wheel dependency. |

**Verdict:** the proposal explicitly asks for true-peak dB, which rules out `pyloudnorm` on correctness grounds alone — it's the wrong tool for what WU1 asked for, not just the slowest one. Between ffmpeg-subprocess and a `libebur128` binding, the binding is the technically better choice (typed output beats parsing ffmpeg's stderr log, no fork/exec overhead per track), **but only if a maintained macOS-arm64+x86_64 wheel actually exists** — that hasn't been verified in this review and should be an explicit spike before committing WU1. If no such wheel exists, ffmpeg subprocess is the fallback, but WU1's scope must include the binary-bundling/codesigning work, not just "port+adapter" — today that work doesn't exist in this codebase in any form.

One structural point that favors either external-process/native option over the current pattern: `desktop/spectral_completion_worker.py:218-221` documents that librosa cancellation is **cooperative only** — "librosa does not interrupt mid-file." A subprocess (`ffmpeg`) or a C-library call can actually be killed cleanly (`Popen.terminate()`), which is a genuine UX improvement over what exists today for cancel-mid-scan.

## 2. Performance at library scale (thousands of tracks)

**The core assumption to validate first:** every existing analyzer in this codebase deliberately narrows the file it reads. `audio/spectral_profile.py:98` analyzes a **fixed 30-second window centered at the track middle** — this was a considered, prior decision (kept without change per team history: fixed 30s window, no phase/section classification). EBU R128 *integrated* loudness, by definition, is measured over the **whole program duration** with gating — you cannot validly claim "integrated LUFS" from a 30-second slice. That means this feature is not "one more analyzer like the others" from a cost perspective: it is structurally more expensive per track than every current analyzer, because it requires a full decode+filter pass. This needs to be profiled against real files before assuming it fits inside the same interactive "scan returns tracks immediately, profiles fill in lazily" UX budget that spectral/danceability/edge analysis uses (see `library/scan_service.py:126-137`, `desktop/spectral_completion_worker.py`).

Concrete strategy, reusing what's already proven in this codebase:

- **Parallelism:** reuse the existing `ThreadPoolExecutor` pattern from `audio/batch_analyzer.py:135-164` and the `_default_max_workers_for_analysis()` (cpu_count − 1) sizing. For subprocess-based work this is actually a *better* fit than it is for librosa, since there's no GIL contention to reason about at all.
- **Caching:** mirror `audio/analysis_planning.py`'s `try_cached_profile`/`store_in_cache` plus `TrackRepository.load_spectral_profile_cache` — key on file identity, skip re-analysis on a cache hit.
- **Incremental rescan:** `track_repository.py:56-60` already made the deliberate call to prefer the FLAC `audio_md5` checksum over `(mtime, size)` when available — a prior mtime-only rescan "discarded 1,266 byte-identical files on a real re-scan." The loudness cache must use the same `audio_md5`-first key, not reinvent a weaker one.
- **Avoiding full decode where possible:** there isn't much room here given the LUFS-integrated requirement above — but LRA and true peak on very short clips are known to be statistically unstable per the EBU R128 spec, so skipping or flagging those two sub-metrics below some duration floor (duration is already captured as `record.duration`) is a legitimate scope-reduction, not a compliance violation.

## 3. Risks and gaps in WU1–WU4 against the real architecture

1. **WU1 doesn't budget the packaging problem.** `packaging/pyinstaller/xfinaudio.spec` has zero binaries today. "Port + adapter" reads like a pure-Python task; shipping ffmpeg (or a `.dylib`) to macOS users is not.

2. **WU2's "3 new SQLite fields" contradicts the established persistence pattern.** Every other computed feature (`SpectralProfile`, `DanceabilityProfile`, `EdgeSpectralProfile`) is a single **versioned Pydantic model** serialized to one nullable JSON column (`spectral_profile_json`, etc.), with its own `analysis_version` for cache invalidation (`spectral_profile.py:17-18`, `danceability.py`) and a `CASE`-based rescan-preserve clause in `TrackRepository.save_scan_results` (`track_repository.py:87-118`) keyed on `audio_md5` first, `(mtime, size)` second. Three flat scalar columns (`loudness_lufs`, `loudness_range_lra`, `true_peak_db`) get none of that for free — no version field to invalidate a bad measurement after a bugfix, and the rescan-preserve `CASE` logic would need to be triplicated across three columns instead of reused once.

3. **WU2's "integrated into the batch analyzer pipeline" is underspecified against what actually exists.** There isn't one generic batch pipeline — `audio/batch_analyzer.py`'s `analyze_paths()` is typed specifically to `SpectralAnalyzer`/`SpectralProfile`, and lazy background completion is instead **three near-identical ~250-line files**: `spectral_completion_worker.py`, `danceability_completion_worker.py`, `edge_spectral_completion_worker.py` — each hand-rolling the same QThread + ThreadPoolExecutor + cooperative-cancellation + `_IN_FLIGHT_WORKERS` bookkeeping. Adding loudness as a fourth copy-paste is the point where that duplication should get generalized instead of extended. WU2 needs to explicitly decide this, not discover it mid-implementation.

4. **WU3 doesn't say where `score_sonority_consistency` fits in `ScoringWeights`.** `recommendation/scoring.py:20-31` is a frozen Pydantic model with a validator requiring `sum(weights) > 0`; every strategy in `strategies.py` sets weights explicitly per-field. A new field needs a `0.0` default (matching the `danceability`/`spectral_edge` precedent) so it's opt-in per strategy and doesn't silently change existing playlists' math. The proposal also doesn't say whether loudness belongs in `COMPATIBILITY_COMPONENTS` or `MIXABILITY_COMPONENTS` (`scoring.py:104-105`) — see open question 3 below, this isn't cosmetic, it changes what `compatibility_score` vs `mixability_score` reports to the UI.

5. **WU3 gives no numeric thresholds.** Every existing delta-based component (`bpm_thresholds`, `energy_thresholds` in `scoring.py:83-92`) has hand-tuned bands feeding `_score_fuzzy`/`_score_threshold`. "Add a score component" without proposed LU delta bands is not implementable as-is, and picking numbers without looking at the real spread of integrated LUFS across this team's own library (unmastered demos vs. club masters can differ by 6-10+ LU) risks a component that's either always-neutral or always-punishing.

6. **WU3/strategies: hard filter or soft weight is undecided.** `same_energy` (`strategies.py:86-93`) uses a hard `energy_tolerance` cutoff, not just a weight. "Consistent Sonority" sounds like it wants the same hard-limit treatment (a DJ set with a mix of -8 LUFS and -16 LUFS masters is a real problem a soft 0.10 weight won't prevent), which means a new `loudness_tolerance`-style field, not just a `ScoringWeights` entry.

7. **WU4 "minimal UI surface" has no detail at all** — lowest risk here, but worth naming: true-peak clipping (>-1 dBTP) is independently actionable regardless of any transition/strategy score and deserves its own indicator, the same way `format_spectral_color()` (`spectral_profile.py:81-89`) gives spectral color a reusable badge convention.

8. **Failure/edge-case contract isn't stated.** Every existing analyzer returns `Profile | None` on failure (`analyzer.py:21`, `37`, `53`) and batch execution isolates per-file exceptions (`batch_analyzer.py:159-161`, `192-194`). The loudness adapter needs the same `-> LoudnessProfile | None` contract to slot into the existing patterns instead of inventing new error handling.

## 4. Concrete improvements, ranked

1. **Persist one versioned `LoudnessProfile` model** (`lufs_integrated`, `loudness_range_lra`, `true_peak_db`, `analysis_version`) serialized to a single `loudness_profile_json` column — not three flat scalars — so it inherits the proven `audio_md5`-first rescan-preserve `CASE` logic and gets a version field for free the day the measurement needs a bugfix.
2. **Verify a maintained macOS-arm64+x86_64 `libebur128` binding wheel exists before defaulting to ffmpeg subprocess.** If it does, prefer it — no stderr parsing, no per-file process spawn, no separate binary to notarize. If not, commit WU1 explicitly to the ffmpeg-bundling + codesigning work, and pin the ffmpeg build version the stderr parser is tested against (with a fixture-based regression test) since that output format has no stability guarantee across ffmpeg releases.
3. **Generalize the three existing completion-worker files before writing a fourth.** They're already ~90% identical scaffolding; extracting one parametrized `CompletionWorker(profile_type, analyzer, repository_methods)` pays for itself immediately and stops a fifth analyzer type (someone will add one) from repeating the same copy-paste.
4. **Key the loudness cache on `audio_md5` first, `(mtime, size)` second** — matching `track_repository.py:56-60`'s already-learned lesson, not a fresh mtime-only cache.
5. **Add the score component as `loudness: float = 0.0`** in `ScoringWeights`, default-neutral (`NEUTRAL_COMPONENT_SCORE = 0.5`) when a profile is missing, following the exact `spectral`/`danceability` pattern — never added to `required_fields`, since most libraries won't have it analyzed on day one and `score_transition` currently zeroes the whole score when a required field is missing.
6. **Decide hard-limit (`loudness_tolerance`, mirroring `energy_tolerance`) vs. soft weight for "Consistent Sonority" before writing WU3** — this changes the shape of both `scoring.py` and `strategies.py`, not just a config value.
7. **Surface true-peak clipping as a standalone warning/badge in WU4**, reusing the `warnings: list[str]` convention already on `TransitionScore` and the badge convention on `format_spectral_color`.

## 5. Open questions for the other reviewer

1. Integrated LUFS legitimately requires a full-file decode, unlike every existing analyzer's fixed 30-second window. Has anyone profiled real per-track wall time for ffmpeg/libebur128 at "thousands of tracks" scale, or is "fast" still an assumption? If it's meaningfully slower than spectral/danceability analysis, does it need to become an explicit "slow tier" instead of living in the same lazy-completion UX?
2. Do you agree the persistence should be one versioned `LoudnessProfile` JSON blob rather than three flat columns? If flat columns are chosen anyway for query/filter convenience, how do we replicate the `audio_md5`/`(mtime,size)` rescan-preserve `CASE` logic across three separate nullable columns instead of one?
3. Should `loudness` sit in `COMPATIBILITY_COMPONENTS` or `MIXABILITY_COMPONENTS`? Loudness consistency reads to me as a technical-handoff concern (closer to `bpm`/`energy`/`spectral_edge`, i.e. mixability) rather than a vibe/compatibility signal (closer to `harmonic`/`tags`/`spectral`) — do you see it differently?
4. Has anyone actually verified a maintained, wheel-published `libebur128` Python binding with macOS arm64+x86_64 wheels exists, or is the ffmpeg-subprocess default just because nobody checked?
5. Given a fourth completion-worker copy is about to be added, should generalizing the three existing ones be in-scope for this change, or tracked as separate follow-up debt? (I lean in-scope — the duplication threshold is already crossed at three, and a fourth makes the eventual refactor strictly more expensive.)

---

## Final Review (Opus)

Last pass against design v2's ten locked decisions, before the formal design document.
Everything below was verified against source; empirical checks are marked as such.
Findings are ranked. **F1–F3 are, in my judgment, blocking** — not because the design is
wrong in intent, but because two locked decisions rest on a premise that the code
contradicts, and the failure mode is silent destruction of the user's data.

Additional files inspected for this pass: `metadata/mixedinkey_contract.py`,
`library/scan_planning.py`, `recommendation/candidate_pool.py`,
`recommendation/playlist_service.py`, `desktop/library_controller.py`,
`config/settings.py`, `config/settings_repository.py`.

---

### F1 — CRITICAL: `audio_md5` exists only for FLAC. Decision 9's cache premise is false for 5 of the 6 supported formats, and the failure mode is silent data destruction.

Decision 9 states: *"audio_md5-first caching so tag write-back never invalidates measurements."*
That holds **only for FLAC**.

Verified empirically (`mutagen` in this environment):

```
FLAC  has md5_signature: True
MP3   has md5_signature: False
MP4   has md5_signature: False
AIFF  has md5_signature: False
WAVE  has md5_signature: False
```

`scan_service.py:372-375` reads `getattr(audio.info, "md5_signature", 0)`, which is a
**FLAC `StreamInfo` field**. For `.mp3`, `.m4a`, `.aif`, `.aiff`, `.wav` it returns `0` →
falsy → no `__audio_md5__` key → `TrackRecord.audio_md5 is None`. Those are 5 of the 6
entries in `scan_planning.py:8`'s `SUPPORTED_AUDIO_EXTENSIONS`.

Now follow what that means through `track_repository.py:87-96`:

```sql
spectral_profile_json = CASE
    WHEN excluded.spectral_profile_json IS NOT NULL THEN excluded.spectral_profile_json
    WHEN tracks.audio_md5 IS NOT NULL AND tracks.audio_md5 = excluded.audio_md5
        THEN tracks.spectral_profile_json
    WHEN tracks.file_mtime_ns = excluded.file_mtime_ns
         AND tracks.file_size_bytes = excluded.file_size_bytes
        THEN tracks.spectral_profile_json
    ELSE NULL          -- <<<< here
END
```

For a non-FLAC file the `audio_md5` branch can never fire. Tag write-back (decision 7)
changes both `mtime` and `size`, so the second branch fails too. The `CASE` falls to
**`ELSE NULL`** — and the identical clause is repeated for `danceability_profile_json`
(97-107) and `edge_spectral_profile_json` (108-118).

**Consequence:** writing a loudness tag to an MP3/M4A/AIFF/WAV causes the *next* library
scan to wipe that track's spectral, danceability, edge **and** loudness profiles. The
feature destroys the output of three unrelated analyzers as a side effect of its own
write-back, on 5 of 6 supported formats.

**Fixes, in order of preference:**

1. **Store the source identity inside `LoudnessProfile` itself** —
   `source_mtime_ns`, `source_size_bytes`, `source_audio_md5` captured at measurement
   time. Cache validity then never consults the shared `tracks.file_mtime_ns` /
   `tracks.file_size_bytes` columns. This is strictly better than a fourth consumer of a
   single shared identity pair, and it makes loudness **independent of whatever shape the
   prerequisite fix in decision 3 takes** (see F3b).
2. **Gate tag write-back to FLAC only in v1.** The user's library is FLAC-centric (their
   own `/dj-metadata` and `/mik-analyze` tooling is FLAC-scoped), so this costs almost
   nothing and eliminates the entire non-FLAC wipe class in one line.
3. If neither, the write-back path must re-stamp `file_mtime_ns`/`file_size_bytes` for
   *every* profile column transactionally with the write — which is exactly the shared-identity
   coupling the prerequisite fix is trying to remove. Don't.

---

### F2 — CRITICAL: the COMMENT-overwrite premise is contradicted by this repo's own measurement and by the user's own toolchain, and it is a one-way door with no undo.

Decision 7 overwrites the COMMENT field, justified by *"user confirmed no notes exist in
their library"*, and ships **opt-out**.

Three pieces of evidence against that premise:

1. **This repo measured the opposite.** `mixedinkey_contract.py:244-246`:
   > *"Grouping disagrees with MIK energy on 23.5% of the measured library and **stale
   > comments on 28.1%**; publisher is likewise unowned."*

   For "stale comments on 28.1%" to be a measurable number, COMMENT had to be **populated
   and parseable** on at least that share of the library. It was rejected as an energy
   source for being *stale*, not for being *absent*. "No notes exist" and "28.1% of
   comments are stale" cannot both be true.

2. **The user's own tooling writes there.** The `/dj-metadata` skill updates
   *"mood, dj_zone, comment"* on FLAC files, and `/mik-analyze` *"actualiza comment tags"*.
   XfinAudio overwriting COMMENT makes it the **third uncoordinated writer** to one field,
   last-writer-wins, with no ownership contract. Note the coupling is already real in the
   other direction: `TAG_FIELDS` (`mixedinkey_contract.py:14`) has XfinAudio *reading*
   `mood` and `dj_zone` — fields that same external tool writes.

3. **There is no undo and no dry-run in the plan.** This is a mutation across thousands of
   irreplaceable files.

Worth stating clearly, because it cuts the other way: overwriting COMMENT does **not**
break XfinAudio's own parser. `PARSED_TAG_KEYS` (`mixedinkey_contract.py:25-42`) contains
no `comment`/`comm` key, and both `_parse_camelot_key` and `_parse_energy` fall back to
`title`, never to comment. The damage is entirely to *other tools in the chain* — which is
worse, not better, because this app cannot detect or repair it.

**Concrete alternative that keeps the whole product benefit:** don't overwrite — write an
**idempotent, sentinel-delimited section**:

```
<whatever was already there> | XFA: -9.8 LUFS · LRA 4.2 · TP -0.8 dBTP
```

Preserve everything before the ` | XFA: ` sentinel; rewrite only the section after it.
Idempotent across repeated runs, still human-readable in Rekordbox/Serato/Traktor (the
actual goal), and non-destructive. Plus: a dry-run preview showing N files and a sample
before/after, and — on first write only — stash the pre-existing COMMENT into the
structured tag (`prev=<base64>`) so it is recoverable.

---

### F3 — HIGH: R5 default-enabled + R6 auto-rescan + R7 opt-out together mean an app update silently mutates the user's library with no consent moment.

Composing three locked decisions: the toggle defaults **on** (R5), first activation triggers
a **full rescan + full-library analysis** (R6), and tag write-back is **opt-out** (decision 7).
The net effect of installing the update is: hours of full-file decoding *and* tag rewrites
across thousands of files, neither of which the user actively chose in that session.

Reading and writing are different risk classes and should not share one default.
**Recommendation:** analysis default-on is fine (reversible, costs only time). Tag
write-back should **default off**, with a one-time explicit confirmation that states scope
in real numbers — *"analyze 10,392 tracks · write tags to 10,392 files"* — before the first
write. A feature and an incident differ by exactly that dialog.

#### F3b — the prerequisite in decision 3 may not cover the defect this design actually depends on

Decision 3 defers to `fix-derived-profile-cache-identity`, described as fixing
`update_*_profile` refreshing the shared `file_mtime_ns`/`file_size_bytes`. That is one of
**two** defects sharing the same root cause (one identity pair serving N profiles). The
other is the `ELSE NULL` wipe in `save_scan_results` (F1), which lives in a different method
and is not obviously in that fix's scope.

State the dependency precisely in the design doc: this work needs **per-profile identity**,
not merely "the `update_*` bug is fixed." If F1's fix #1 is adopted (identity inside the
profile model), loudness is immune either way — which is the strongest argument for it.

---

### F4 — HIGH: "not measured" filtering semantics are ambiguous, and the existing convention drops missing values — reintroducing the exact bug `_weighted_total` documents.

Decision 6 says not-measured tracks are *"excluded from target filtering."* That parses two
opposite ways: *dropped from the pool*, or *exempt from the band*. The distinction decides
whether the feature works.

The established convention in this codebase is **drop**. `playlist_service.py:1063-1068`:

```python
if track.path in preserve_paths
or (track.energy_level is not None and min_energy <= track.energy_level <= max_energy)
```

`energy_level is None` → filtered out. Same pattern for `energy_range` and `bpm_range` at
`playlist_service.py:656-671`. If loudness copies it, then during the multi-hour progressive
analysis window **most of the library has no measurement**, so a Consistent Sonority pool is
near-empty and — worse — *changes every few minutes* as analysis progresses. Same library,
same strategy, different result. That is very hard to report as a bug and very easy to
report as "the app is broken."

This is the same failure the team already paid for once, on the scoring side.
`scoring.py:416-425`:

> *"Dropping absent components from the denominator instead used to inflate the total […]
> The optimizer maximizes adjacent scores, so it systematically preferred the least
> documented tracks -- **worst during the progressive spectral pass, when much of the
> library has no profile yet**."*

Neutral scoring solved it there. A **filter is binary — neutral has no equivalent**, so the
band must handle it explicitly.

**Recommendation:** unmeasured tracks **stay in the pool**, exempt from the band, while
coverage is incomplete, and the warning must carry coverage numbers rather than a bare
count: *"Loudness band applied to 3,412 of 10,392 tracks; 6,980 not yet measured and left
in."* Optionally flip to strict exclusion once coverage is complete, or expose it as a
user-visible toggle — but never silently.

---

### F5 — HIGH: capturing identity before the tag write costs one full spurious re-analysis of the entire library.

Ordering bug, easy to miss and certain to happen: measure → write tag → store profile. The
write changes `mtime`/`size`, so a profile stamped with **pre-write** identity is stale the
instant it is persisted.

Next scan: identity mismatch → re-measure the whole library. Values are unchanged, so
decision 7's *"dual write when values change"* correctly skips the second write, identity
now settles, and scan 3 is clean.

So it **converges after one extra pass** — not an infinite loop, to be precise — but that
one pass is a full re-decode of every track, and on non-FLAC it also triggers F1's
collateral wipe of the other three profiles. Capture identity **after** the write completes,
or (better) store `source_audio_md5` per F1, which is invariant under tag changes on FLAC.

---

### F6 — MEDIUM-HIGH: the pairwise scoring component double-counts the absolute band, and "mixability" contradicts decision 8's own stated justification. This is the available simplification.

Decision 4 chose **absolute, whole-set** semantics ("target chosen by user per set moment,
e.g. warmup -14, peak -9", "whole-set anchor semantics to avoid pairwise drift"). Decision 8
*additionally* keeps a pairwise `loudness` weight in `ScoringWeights`.

Those measure the same constraint twice. If every track is inside ±X LU of one absolute
target, the pairwise delta is already bounded by 2X by construction. A transition component
on top adds no information the band has not already enforced.

The bucket question inherits the confusion. `scoring.py:101-105` defines them:

> *"Compatibility asks whether tracks belong in the same set; mixability asks whether they
> can be joined."*

Decision 8 picks **mixability** but justifies it as *"set continuity"* — which is the
compatibility definition, verbatim. Under decision 4's absolute semantics the honest answer
is **neither**: an absolute band is not a property of a transition at all. It is a pool
filter, and it belongs beside `energy_range` in `_apply_strategy_filters`
(`playlist_service.py:649-675`), returning the same `(filtered, warnings)` tuple every other
filter there returns.

**Recommendation (simplification):** ship v1 with the band, the LRA display, and the
true-peak badge — and **no pairwise scoring component**. The product promise of decision 4
is fully delivered without it. If a pairwise component is wanted later, define it as
`|LUFS(A) − LUFS(B)|` (gain-riding at the handoff — genuinely mixability, genuinely
orthogonal to the absolute band) and add it then, with real threshold bands measured
against the library. A field defaulting to `0.0` that no strategy sets is dead weight in a
frozen model that every strategy must reason about.

---

### F7 — MEDIUM-HIGH: four FFmpeg invocation details that will bite in a real DJ library.

1. **Embedded cover art.** Near-universal in DJ libraries. FFmpeg sees the attached picture
   as a video stream. Use `-map 0:a:0` (and/or `-vn`) to pin the first audio stream
   explicitly; without it, stream selection on art-bearing files is a coin flip you will
   debug in production.
2. **`-nostdin`.** A GUI app spawning many children must not let FFmpeg consume the parent's
   stdin. Pass `-nostdin` and `stdin=DEVNULL`.
3. **Explicit timeout + kill.** A truncated or corrupt file can hang FFmpeg indefinitely,
   permanently consuming a worker slot. `subprocess.run(..., timeout=N)` plus kill-on-timeout,
   and classify the result as *transient failure*, not *unmeasurable* (see F14).
4. **Orphan reaping on teardown.** `spectral_completion_worker.py:232-246`'s `shutdown()`
   resorts to `thread.terminate()`. Terminating the worker thread does **not** kill its
   FFmpeg children — they keep decoding and keep the external drive spinning after the
   window closes. Track live `Popen` handles and kill them (process group) on teardown.

Genuine upside worth capturing in the design doc: `spectral_completion_worker.py:218-221`
documents that *"librosa does not interrupt mid-file"*, so cancellation there is cooperative
at best. A subprocess **can** be killed immediately. Loudness should hold the `Popen` and
terminate it on cancel — the first analyzer in this app with real mid-file cancellation.

---

### F8 — MEDIUM-HIGH: the PyInstaller spec has two settings that will actively break a bundled binary.

From `packaging/pyinstaller/xfinaudio.spec`:

- **`upx=True`** at both `EXE` (line 68) and `COLLECT` (line 82), with **`upx_exclude=[]`**
  (line 83). UPX-compressing a macOS arm64 Mach-O invalidates its code signature and
  frequently breaks the binary outright. FFmpeg **must** be added to `upx_exclude`.
- **`codesign_identity=None`, `entitlements_file=None`** (lines 72-73). There is no signing
  configured today. A nested executable inside a hardened-runtime, notarized `.app` must be
  signed with the same Team ID; an unsigned nested binary fails notarization, and under
  hardened runtime spawning it fails at runtime. This is new release-pipeline work, not a
  spec tweak.
- `binaries=[]` (line 27) becomes non-empty, and the runtime path must resolve via
  `sys._MEIPASS` when frozen — never bare `ffmpeg` on `PATH`.
- **Quarantine:** if a user's download is not properly notarized, Gatekeeper can block the
  nested binary *per spawn*. The preflight must fail once, cleanly, into "loudness
  unavailable" — never a modal storm and never a crash, and never blocking the other three
  analyzers.

---

### F9 — MEDIUM: the GPL question resolves in your favor, with one trap left.

I checked before flagging it: `pyproject.toml:6` declares `license = "GPL-3.0-only"`. FFmpeg
built with `--enable-gpl` is GPLv2-or-later, compatible with GPLv3, so bundling a GPL build
is fine here. Two things remain:

- **Never `--enable-nonfree`** (e.g. `fdk-aac`). That produces a **non-distributable** binary
  regardless of your own license. Assert this in the conformance preflight by parsing the
  build configuration string, not by trusting the download page.
- **GPL §3 applies to the binary you ship.** You must be able to offer corresponding source
  for the exact pinned FFmpeg build. Pin the version *and* archive the source tarball
  alongside the release.

Also: you only need `ebur128` plus FLAC/MP3/AAC/ALAC/PCM decoders. A minimal build is a
fraction of the ~70-100 MB of a full static FFmpeg — meaningful for a desktop app download,
and a smaller attack and support surface.

---

### F10 — MEDIUM: "recover measurements from tags alone" has three plumbing gaps and is not format-universal.

Decision 7 promises DB-loss recovery with no re-decode. That does not come for free:

1. **`scan_service.py:269-277`'s `_retained_raw_metadata` drops it.** Raw metadata is filtered
   to `PARSED_TAG_KEYS`, so `XFINAUDIO_LOUDNESS` is discarded before it reaches persistence.
   `PARSED_TAG_KEYS` (`mixedinkey_contract.py:25-42`) must be extended.
2. **Nothing parses it into `TrackRecord`.** `_build_records` (`scan_service.py:228-266`)
   would need to construct `loudness_profile` from the tag. Put that in its own small module —
   don't widen the Mixed In Key contract to hold a field MIK never writes.
3. **The tag key is format-specific, and one format cannot carry it.** Vorbis comment (FLAC)
   is trivial; ID3 needs `TXXX:XFINAUDIO_LOUDNESS`; MP4 needs a freeform
   `----:com.apple.iTunes:XFINAUDIO_LOUDNESS` atom; AIFF uses an ID3 chunk; **WAV has no
   reliable tagging story**. Since `read_mutagen_tags` uses `easy=False`, `PARSED_TAG_KEYS`
   must contain the format-specific spellings (casefolded), not one logical name. State
   plainly that the recovery guarantee is FLAC/MP3/M4A/AIFF, not WAV.

---

### F11 — MEDIUM: do NOT bump `CURRENT_SETTINGS_VERSION` for the R5 toggle.

`settings.py:98-104` validates with **exact equality**:

```python
if value != CURRENT_SETTINGS_VERSION:
    raise ValueError(f"Unsupported settings version: {value}")
```

and `settings_repository.py:39-42` turns any `ValidationError` into `SettingsRepositoryError`.
There is **no migration path**. Bumping to `2` makes every existing user's on-disk
`"settings_version": 1` fail to load — taking `last_scan_folder`, window geometry, language
and scoring settings with it.

Adding a nested `LoudnessSettings` model with defaults to `AppSettings` requires **no bump**:
Pydantic fills the default for older files. Add the field, leave the version at 1.

---

### F12 — MEDIUM: the engine-fingerprint invalidation policy is unstated, and the obvious default is destructive.

Storing an engine fingerprint (decision 2) is right. But nothing says what happens when it
changes. The naive rule — *fingerprint differs → re-measure* — means a routine FFmpeg bump
in a future release silently triggers a full-library re-decode **and**, under decision 7, a
full-library tag rewrite on app update. That is F3's problem again, arriving through the
back door on a version the user did not think was risky.

Define it explicitly: a fingerprint change marks measurements **stale but usable**, surfaces
a coverage/refresh prompt, and re-measures only on explicit user action. Separately, decide
whether a fingerprint change even *should* invalidate — if conformance fixtures prove the
new build produces identical values on the reference set, nothing needs re-measuring, and
the fixtures you already planned are exactly the evidence for that call.

---

### F13 — MEDIUM: the three workers run **chained, not concurrent** — so time-to-first-LUFS is the sum of four passes, and the documented reason for chaining may not apply to a subprocess.

Verified: `library_controller.py:537-539` chains spectral → danceability → edge, with the
rationale stated in-line:

> *"Both analyses are CPU-bound librosa work, so their pools must run sequentially rather
> than competing for every available CPU core."*

Two consequences for decision 9's "serialized integration":

1. **Loudness becomes link four.** No LUFS data appears until three full librosa passes
   finish. On a 10k library that is plausibly hours during which Consistent Sonority has
   nothing to work with — which is precisely when F4's filtering ambiguity does maximum
   damage. Keep loudness last (cheapest-first is right), but the UI must distinguish
   *"pending"* from *"not measurable"*, and the chain must be resumable across app restarts
   rather than restarting from link one.
2. **The stated rationale is about GIL/CPU contention, and an FFmpeg subprocess does not
   contend for the GIL.** Loudness is the one pass that could legitimately overlap the
   librosa passes at reduced concurrency. I am not asserting it will be faster — they still
   share one external drive's I/O queue, and librosa decodes audio too — but the design doc
   should not inherit the serialization rationale as if it obviously transfers. Measure it.

On concurrency sizing: `_default_max_workers_for_analysis()` is `cpu_count - 1`
(`batch_analyzer.py:32-34`). Nine concurrent full-file FFmpeg decodes against a single
USB/spinning drive will thrash the queue and can be **slower** than four. Loudness deserves
its own smaller default (2-4), measured, and user-adjustable — not the shared CPU-derived one.

Worth naming as direction, not v1 scope: four passes now means **four full reads of the
library** off an external drive. A single-decode/multi-analyzer pass is the architecturally
interesting endpoint here. Don't build it now — but it strengthens the case for keeping the
worker-generalization debt visible rather than letting it calcify at four copies.

---

### F14 — MEDIUM: transient failures must not be persisted as permanent "not measured."

Decision 6's typed not-measured status needs **two** categories:

- **Sticky:** unsupported codec, too short, structurally corrupt. Never retried.
- **Transient:** drive unmounted mid-scan, FFmpeg timeout, permission error, spawn failure.
  Retried on the next pass.

Collapse them and a single mid-scan drive ejection permanently marks hundreds of tracks
unmeasurable, with no path back short of a manual full re-analysis. Given decision 4
excludes not-measured tracks from target filtering, those tracks would silently stop
appearing in Consistent Sonority sets forever.

---

### F15 — MEDIUM-LOW: schema-change checklist (eight touch points; missing one fails at runtime, not at import).

Bump `SCHEMA_VERSION` 4 → 5 (`track_repository.py:26`) and update, in `track_repository.py`:

1. `_ensure_schema` `CREATE TABLE` body (403-426) — add `loudness_profile_json TEXT`
2. `_ensure_schema` — add the `contextlib.suppress(...)` `ALTER TABLE ADD COLUMN` (429-449 block)
3. `save_scan_results` INSERT column list (63-68) **and the placeholder count** (69 — currently 22 `?`)
4. `save_scan_results` `ON CONFLICT DO UPDATE SET` + its preserve `CASE` (per F1, ideally *not* the shared-identity form)
5. `list_tracks` SELECT (141-150)
6. `list_display_tracks` SELECT (155-165)
7. `_record_to_row` (467-490), `_row_to_record` (493-515), `_display_row_to_record` (518-538)
8. `TrackRecord` in `library/models.py`, plus `_build_records` in `scan_service.py`

Confirm `needs_raw_metadata_trim = 0 < schema_version < 4` (`track_repository.py:352`) stays
`< 4` — it gates a one-time v4 trim + `VACUUM` and must not re-fire on the v5 upgrade.

---

### F16 — MEDIUM-LOW: define the numeric floors and thresholds, don't leave them to implementation.

- **LUFS-I:** gating needs enough material to produce a gated value; below ~5 s it is not
  meaningful. `record.duration` already exists — use it, don't probe the file again.
- **LRA:** built from 3 s short-term blocks with 10th/95th percentiles. Below ~30 s it is
  statistically meaningless. Return `lra=None` with `partial=True` rather than a number
  nobody should trust.
- **True peak:** always available. Two named severities as constants, not magic numbers —
  `> 0.0 dBTP` is actual inter-sample clipping; `> -1.0 dBTP` is at-risk. Both are legitimate
  DJ-actionable signals independent of any strategy.
- FFmpeg's true peak uses 4× oversampling (the BS.1770-4 minimum). Fine for a warning badge;
  do not describe it in the UI as lab-grade measurement.
- DJ note worth writing down so it is not mistaken for a defect later: heavily limited club
  masters legitimately show LRA 3-5 LU. Low LRA is information, not an error.

---

### F17 — LOW: coverage must be a persisted query, not just live progress.

The existing `progress_updated(processed, total)` signal covers the in-flight case. For the
coverage surface in decision 10, the UI needs the answer at app start without re-scanning —
a `SELECT COUNT(*) ... WHERE loudness_profile_json IS NOT NULL` alongside the total. Cheap,
and it is also the number F4's warning text needs.

---

### F18 — LOW: the stderr parser must fail loud, or a broken engine is indistinguishable from "not done yet."

Every analyzer here returns `Profile | None` on failure (`analyzer.py:21,37,53`), and batch
execution swallows per-file exceptions (`batch_analyzer.py:159-161`). Loudness should match
that contract for *per-file* failure — but a **parse** failure is categorically different: if
an FFmpeg build change alters the summary format, every file returns `None` and the UI shows
"0 measured" forever, looking exactly like analysis that has not run yet.

Make an unparseable-but-successful FFmpeg run a **loud, distinct, logged engine-level error**
that disables the feature with a stated reason, and cover it with a conformance fixture
asserting the parser rejects malformed output rather than silently returning `None`.

---

## Summary — what I would change before writing the design doc

**Blocking:**
- **F1** — `audio_md5` is FLAC-only; the write-back cache premise is false for 5 of 6 formats
  and silently wipes three other analyzers' profiles. Store identity inside `LoudnessProfile`,
  and gate write-back to FLAC in v1.
- **F2** — the "no notes exist" premise is contradicted by `mixedinkey_contract.py:244-246`
  and by the user's own COMMENT-writing tooling. Use an idempotent sentinel-delimited section
  instead of overwrite; add dry-run and first-write backup.
- **F3** — default-on analysis + auto-rescan + opt-out writing = an update that mutates the
  library with no consent moment. Split the defaults: analysis on, **write-back off**.

**Should fix before shipping:** F4 (unmeasured tracks must stay in the pool — this is the
already-paid-for `_weighted_total` lesson repeating on the filter side), F5 (post-write
identity capture), F7 (`-map 0:a:0`, `-nostdin`, timeout, orphan reaping), F8 (`upx_exclude`,
codesigning).

**Simplification available:** F6 — drop the pairwise scoring component from v1 entirely. The
band + LRA display + true-peak badge deliver decision 4's product promise, and the component
as specified double-counts the band while sitting in a bucket that contradicts its own stated
justification. Less code, fewer decisions to defend, nothing lost.

**Best structural idea in this pass:** F1's fix #1. Putting source identity inside each
profile model decouples this work from the prerequisite in decision 3, kills the write-back
invalidation problem, and points at the right long-term shape for the other three profiles —
one identity pair serving four analyzers is the root cause behind F1, F3b and F5 alike.

---

## Gate WU2 Review

**Verdict: FAIL — 5 blockers (2 are true contract violations).**

Reviewed: committed history only, worktree `../loudness-review-codex`, commits
`5770b3d` → `28beed4` → `5a7b837` (HEAD). Contract: `openspec/changes/add-loudness-module/design.md`
§2 and §3, tasks `2.1`–`2.5`. All line references below are that worktree at HEAD `5a7b837`
unless stated otherwise. Nothing was modified anywhere.

### What is genuinely right — state it first

The persistence core is well built and the hardest thing in the contract was implemented
correctly:

- **B7 regression guard satisfied.** `loudness_profile_json` is in the INSERT column list
  (`track_repository.py:70`) with the placeholder count correctly bumped 22 → 23, and has an
  explicit `CASE` (`:121-124`), covered by a preservation regression test.
- **The `CASE` is unconditional-preserve, and that is the right call.** `:121-124` is
  `WHEN excluded IS NOT NULL THEN excluded ELSE tracks.loudness_profile_json` — deliberately
  *without* the shared-identity guard the three sibling columns use. That is precisely design
  §2's "decouples loudness from the shared identity pair entirely", and it is what makes
  blocker **W2** below a visibility bug rather than a data-loss bug.
- **F1/F5 consumer side is correct.** `load_loudness_profile_cache` (`:450-473`) validates
  `analysis_version`, `engine_fingerprint`, and `(profile.source_mtime_ns,
  profile.source_size_bytes)` against a fresh `stat()` — reading identity from **inside the
  profile**, never from `tracks.file_mtime_ns/file_size_bytes`. `force_reanalyze` is an
  explicit parameter.
- **The migration test is better than average.** It renames the table, recreates it *without*
  the new column, sets `PRAGMA user_version = SCHEMA_VERSION`, and asserts `_ensure_schema`
  still adds the column — the correct way to prove design §2's "no `SCHEMA_VERSION` bump
  required" claim rather than asserting it in prose.
- **RED-first evidence is concrete**, with real counts rather than a checkbox: task 2.3 records
  `RED → 5 failed, 82 passed` … `GREEN → 87 passed` in `apply-progress.md`.
- Commits are small, single-purpose, conventionally named, and each records its own rollback
  boundary.

---

### W1 — BLOCKER (critical): `.m4a` is missing from the post-write refresh helper, so the F1 wipe survives intact for one format

`track_repository.py:32`:

```python
_METADATA_REFRESH_SUFFIXES = frozenset({".mp3", ".flac", ".wav", ".aif", ".aiff"})
```

`library/scan_planning.py:8` defines six supported formats:

```python
SUPPORTED_AUDIO_EXTENSIONS = frozenset({".aif", ".aiff", ".flac", ".m4a", ".mp3", ".wav"})
```

`.m4a` is absent from the helper's set, so `refresh_post_metadata_identity` returns `False`
at the suffix gate (`:437`) and never refreshes identity for M4A files.

M4A is also the format with **no `audio_md5`** (`md5_signature` is a FLAC `StreamInfo` field;
verified empirically — FLAC `True`, MP4/MP3/AIFF/WAVE `False`). So for an M4A file after a
WU3 tag write: shared identity is not refreshed → `audio_md5` is `NULL` → the sibling `CASE`
branches in `save_scan_results` both fail → **`ELSE NULL`** → spectral, danceability and edge
profiles are wiped on the next scan.

That is exactly the F1 failure mode this entire design was constructed to prevent, preserved
for one format. The contract is unambiguous — task 2.3: *"tag write must not wipe
spectral/danceability/edge **on any format**"*; design §2: *"atomically preserved across the
mtime/size change **on all formats**"*. Delivered: 5 of 6.

**How it got through — this is the instructive part.** The guarding test is
`tests/test_track_repository.py`:

```python
@pytest.mark.parametrize("suffix", [".mp3", ".flac", ".wav", ".aiff"])
def test_refresh_post_metadata_identity_preserves_all_sibling_profiles_across_supported_formats(
```

The test *name* claims coverage "across supported formats"; the parametrization covers four
of six. The one format missing from the parametrization is the one missing from the
implementation, so the suite is green and the guarantee is false. A green test asserting a
claim it does not exercise is worse than no test — it retires the question.

**Fix:** derive the set from `SUPPORTED_AUDIO_EXTENSIONS` rather than restating it, and
parametrize the test over the same source so the two cannot drift again.

---

### W2 — BLOCKER (high): `list_display_tracks` was not updated, so the running app never sees any loudness measurement

`list_tracks` was updated — its SELECT includes `loudness_profile_json` (`:152`) and
`_row_to_record` populates the field (`:663`). Its sibling read path was not:

- `list_display_tracks` SELECT (`:159-170`) omits `loudness_profile_json`
- `_display_row_to_record` (`:667`+) never populates `loudness_profile`

That matters because the display path — not `list_tracks` — is what the application actually
runs on:

- `desktop/window_factory.py:236` — `window.restore_persisted_tracks(repository.list_display_tracks())`
  builds the **entire app track state at launch**
- `application/playlist_workflow.py:108` — the recommendation workflow re-hydrates profiles
  from `list_display_tracks()` (there is already an established backfill precedent there for
  `spectral_profile`, `:105-115`)
- it is the port contract surface: `library/ports.py:25`

Net effect: measurements persist correctly to SQLite and are then dropped on the floor by the
primary read path. Every `TrackRecord` in the running application carries
`loudness_profile = None` after any restart, so WU3's target-band filter would classify 100%
of the library as unmeasured and WU4's UI would render permanently empty — with the DB full
of correct data. It would look like an analysis bug and be a `SELECT` bug.

Not data loss (W1's unconditional `CASE` protects the column), but it makes the capability
WU2 delivers unobservable. The fix is two lines; the reason it is a blocker is that shipping
WU3 on top of it guarantees a false "coverage 0%" diagnosis.

---

### W3 — BLOCKER (medium-high): task 2.4 is marked `[x]`, but no retry policy exists in any layer

`load_loudness_profile_cache` (`:450-473`) filters on `analysis_version`, `engine_fingerprint`
and identity. There is **no `status`-aware branching anywhere in the repository layer**, and
`grep` finds no retry helper in `audio/loudness.py` either.

Trace both directions and neither half of the policy works:

- **Today:** `_failure()` (`audio/loudness.py:228-236`) constructs profiles leaving
  `source_mtime_ns`/`source_size_bytes` at their `None` default (`:44-45`), and `analyze()`
  (`:165-196`) never stamps them. So `(None, None) != (int, int)` — every failure profile
  misses the cache and is re-analyzed on every pass. That violates design §2's *"typed failure
  statuses persist so corrupt files are not retried every scan"*: an `unsupported` or
  `too_short` file gets a full FFmpeg spawn on every scan, forever.
- **After WU3 3.4** ("restat → stamp identity → persist", stated without status qualification):
  failure profiles start carrying identity, become cache hits, and `transient_failure` turns
  **permanently sticky** — violating design §1, which classifies timeouts and kills as
  *transient failure specifically so they are retried*. One ejected external drive would
  permanently mark hundreds of tracks unmeasurable.

Codex disclosed the layering choice in `IMPLEMENTATION-NOTES.md` ("Typed statuses, including
`transient_failure`, are returned from that cache for unchanged inputs so pipeline callers can
avoid retry loops"), which is a defensible seam — but the caller that would implement it is
task **2.5, which is unchecked**. A policy deferred to an unimplemented task cannot support
marking 2.4 complete.

**Contract defect, not only an implementation gap:** tasks.md 2.4 reads *"retry only on
version/fingerprint bump or explicit reanalyze"*, which collapses the transient/sticky
distinction that design §1 and §2 both draw. Resolve the contract text before implementing,
or the next attempt will encode the same ambiguity.

---

### W4 — BLOCKER (medium): the whole of design §3 (pipeline) is unimplemented — WU2 is 4/5, not complete

Gate question 5 has a clean answer: **nothing in design §3 exists.** The three commits touch
only `library/track_repository.py` and `library/models.py`. Untouched:

- `audio/batch_analyzer.py` — no loudness batch path
- `library/scan_service.py` — `_build_records` never constructs `loudness_profile`
- `desktop/library_controller.py` — the serialized chain (`:537-539`) still has three links

So: no serialized lazy-lifecycle integration, no disk-bound concurrency cap (2–3), no priority
order (selected → candidates → visible folder → rest), no per-result immediate persistence.

**This is disclosed, not silent** — `tasks.md` correctly shows `- [ ] 2.5`. Credit where due.
But the gate was requested as "Codex completed WU2", and WU2 is 4 of 5 tasks with the entire
pipeline section outstanding. The gate must record that discrepancy rather than inherit the
framing.

---

### W5 — BLOCKER (medium): no full-suite verification exists for any WU2 commit

The recorded green run — `1706 passed`, `pyright 0 errors`, `ruff` clean, with per-command
SHA-256 output hashes — is the **WU1 self-verification at HEAD `202f6fc`**, which precedes all
three WU2 commits (`202f6fc` → `46b9712` → `b2cbc79` → `5770b3d` → `28beed4` → `5a7b837`).

WU2's own evidence is a focused file only: `uv run pytest -q tests/test_track_repository.py`
→ `87 passed`. Design §9 requires *"Full suite green + coverage non-regression (baseline
91.14%)"*. Changing `library/models.py` (adding a field to `TrackRecord`, the model threaded
through scan, persistence, recommendation and UI) without a full-suite run is exactly the
change shape that breaks distant tests. Run the full suite and coverage against HEAD before
the gate is reconsidered.

---

### Non-blocking findings

- **N1 — `source_audio_md5` is a dead field.** Declared (`audio/loudness.py:46`) and
  serialized, never read: `load_loudness_profile_cache` compares only mtime/size. It is also
  the single mechanism that would survive an **external** tag write — `/dj-metadata` and
  `/mik-analyze` rewrite FLAC tags routinely, changing mtime/size and forcing a full
  re-decode of the library on the next scan even though the audio is byte-identical.
  Recommend consulting it as a fallback when mtime/size mismatch but `audio_md5` matches.
- **N2 — 2.2 is only half-verifiable.** The consumer (cache check) is correct; the producer
  does not exist, since `analyze()` never stamps identity. Current behaviour is fail-safe
  (`None` never matches → re-analyze), but "captured AFTER tag writes" cannot be proven
  end-to-end until WU3 3.4 lands. Keep the RED test for ordering in that work unit.
- **N3 — `refresh_post_metadata_identity` encodes an unenforced precondition.** The docstring
  says *"callers must not use it after replacing audio content"*; nothing enforces it. Misuse
  silently stamps stale profiles as current and permanently prevents their invalidation.
  Consider accepting the expected pre-write identity and no-op'ing on mismatch — the
  precondition then fails closed instead of corrupting silently.
- **N4 — no `SCHEMA_VERSION` bump** (`:27` still `4`) matches design §2 and is properly
  tested. Document one consequence: an older build (22-column INSERT) opening the upgraded DB
  writes `NULL` into `loudness_profile_json` on rescan, silently discarding measurements on
  downgrade.
- **N5 — the notes misstate the format set.** `IMPLEMENTATION-NOTES.md` describes the helper
  as accepting "supported MP3/FLAC/WAV/AIFF suffixes", treating four formats as the supported
  set when the codebase defines six. W1 was therefore *documented*, but under a false premise —
  which is why it read as complete.
- **N6 — R12 referenced an artifact that does not exist.** Design §2 says to call "the shared
  identity helper **from** `fix-derived-profile-cache-identity`". That change left no such
  named helper; it added sibling-preserving `CASE` guards inside `update_spectral_profile` and
  friends (`:174`+). Creating `refresh_post_metadata_identity` was a reasonable resolution, but
  it is a contract correction and should be recorded as one rather than left implicit.
- **N7 — process observation, not a code finding.** `IMPLEMENTATION-NOTES.md` records a native
  runtime stop pending an exact maintainer reset ("No WU2 actor or harness was launched after
  this native stop"), and the three WU2 commits follow it. Whether the reset was performed is
  outside this review's scope; flagging so the ledger state is reconciled deliberately.

---

### Gate questions — direct answers

| # | Question | Answer |
|---|---|---|
| 1 | `loudness_profile_json` in `save_scan_results` INSERT/CASE (B7)? | **Yes** — `:70`, `:121-124`, placeholders bumped, regression-tested |
| 2 | Cache validity from identity inside the profile, after tag writes, never shared columns? | **Consumer yes** (`:450-473`); **producer absent** (N2) — no stamping exists yet |
| 3 | Sibling updates via the shared identity helper on **all** formats (R12)? | **No — W1.** `.m4a` excluded (`:32`); the F1 wipe survives for that format |
| 4 | Typed failure statuses persisted; retry policy respected? | **Persisted yes; retry policy absent — W3.** No status-aware logic in any layer |
| 5 | Pipeline: serialized lifecycle, disk-bound concurrency, priority order, immediate persistence? | **None implemented — W4.** Task 2.5 honestly unchecked |
| 6 | TDD evidence quality / silent contract deviation? | **Evidence structurally good** (RED counts, migration test). **No silent deviation** — but W1's test name overstates its parametrization, and W5 means no full-suite proof exists |

### Exit criteria to re-gate

1. Derive `_METADATA_REFRESH_SUFFIXES` from `SUPPORTED_AUDIO_EXTENSIONS`; parametrize the
   sibling-preservation test from the same source (**W1**).
2. Add `loudness_profile_json` to `list_display_tracks` + `_display_row_to_record`, with a test
   asserting a persisted profile survives the display read path (**W2**).
3. Resolve the transient-vs-sticky contract inconsistency in tasks 2.4 / design §1–§2, then
   implement status-aware retry and re-mark 2.4 honestly (**W3**).
4. Either complete 2.5 or re-scope the gate as **WU2 partial (2.1–2.4)** (**W4**).
5. Full suite + `pyright` + `ruff` + coverage ≥ 91.14% at HEAD, recorded as for WU1 (**W5**).
