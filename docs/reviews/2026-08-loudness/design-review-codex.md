# Loudness Module Design Review

## Executive verdict

**Proceed, but revise the design before implementation.** For XfinAudio's first production implementation, use a **pinned FFmpeg executable behind a `LoudnessAnalyzer` port**, not an in-process libebur128 binding, pyloudnorm, or a new pure-Python meter. FFmpeg provides the best current combination of codec coverage, EBU R128 behavior, true-peak support, streaming memory use, and operational isolation. That choice is only sound if XfinAudio owns binary discovery, version validation, cancellation, parsing, packaging, and license evidence; assuming a Homebrew `ffmpeg` on `PATH` is not an acceptable desktop distribution design.

The proposed WU1-WU4 decomposition is directionally good but incomplete. The largest architectural problems are:

1. `audio/batch_analyzer.py` is spectral-specific, while the real desktop lazy pipeline lives in separate Qt completion workers.
2. all derived-profile caches currently share one `file_mtime_ns`/`file_size_bytes` identity, which can make stale profiles look current when any one analyzer refreshes that identity;
3. pairwise loudness similarity does not guarantee whole-playlist consistency because small adjacent differences can drift across a set; and
4. the three scalar database fields do not carry analyzer version, failure state, or independent cache identity.

## Repository evidence inspected

- Analyzer ports/adapters: `src/xfinaudio/audio/analyzer.py:18-63`
- Spectral batch facade: `src/xfinaudio/audio/batch_analyzer.py:17-196`
- Batch cache planning: `src/xfinaudio/audio/analysis_planning.py:14-86`
- Track domain model: `src/xfinaudio/library/models.py:15-39`
- Persistence ports: `src/xfinaudio/library/ports.py:14-84`
- SQLite repository and migrations: `src/xfinaudio/library/track_repository.py:26-30`, `63-120`, `168-227`, `337-450`, `457-538`
- Scan phases and lazy-profile seam: `src/xfinaudio/library/scan_service.py:68-138`, `146-225`, `279-344`
- Desktop completion lifecycle: `src/xfinaudio/desktop/spectral_completion_worker.py:76-127`; `src/xfinaudio/desktop/library_controller.py:410-475`, `521-632`
- Immutable profile application: `src/xfinaudio/desktop/app_state_transitions.py:44-99`
- Scoring and missing-data policy: `src/xfinaudio/recommendation/scoring.py:20-41`, `99-112`, `116-248`, `378-445`
- Strategy registry: `src/xfinaudio/recommendation/strategies.py:12-44`, `44-123`, `126-175`
- Optimizer objective: `src/xfinaudio/recommendation/optimizer.py:111-155`, `175-224`
- Strategy-to-UI path: `src/xfinaudio/application/strategy_catalog.py:20-39`; `src/xfinaudio/desktop/build_view_model.py:41-59`; `src/xfinaudio/desktop/screens/build_screen.py:327-330`
- Library UI columns: `src/xfinaudio/desktop/screens/library_screen.py:25-38`; `src/xfinaudio/desktop/library_screen_builder.py:121-150`; `src/xfinaudio/desktop/table_populators.py:28-70`
- PyInstaller spec and dependency policy: `packaging/pyinstaller/xfinaudio.spec:15-54`, `76-94`; `pyproject.toml:15-37`

## 1. Implementation verdict

### FFmpeg subprocess — recommended for v1

**Speed and memory.** FFmpeg decodes and measures in native code and streams frames through the filter; it does not require loading an entire track into a NumPy array. Subprocess startup is measurable but small relative to decoding a multi-minute track. For thousands of tracks, total work is dominated by full decode, not process launch.

**Compliance and fidelity.** FFmpeg's `ebur128` filter exposes integrated loudness, LRA, and true-peak mode. It is mature and codec-complete for the formats XfinAudio already scans. True peak depends on the exact FFmpeg build and resampling support, so the executable and filter capability must be pinned and tested rather than treated as an unspecified system service. The official filter/source documents true-peak mode; the design should validate the selected binary with conformance fixtures, not merely assert EBU compliance ([FFmpeg ebur128 source](https://ffmpeg.org/doxygen/8.0/f__ebur128_8c_source.html)).

**Operational tradeoffs.** Parsing human-oriented stderr is brittle across versions and log settings. The adapter needs a deliberately pinned command contract (`-nostdin`, deterministic locale, hidden banner/progress, null output), strict finite/range validation, a bounded stderr capture, and tests against the exact shipped FFmpeg version. Treat missing filter support, corrupt input, timeout, cancellation, non-zero exit, malformed summary, and silent/too-short content as typed outcomes—not one undifferentiated `None`.

**macOS/PyInstaller.** The current PyInstaller spec has `binaries=[]` (`packaging/pyinstaller/xfinaudio.spec:24-28`). Qt Multimedia's collected FFmpeg libraries are not an `ffmpeg` CLI executable that a subprocess adapter can invoke. A packaged design must add the executable as a binary, resolve it relative to the frozen bundle, support the built architecture(s), verify executable permission, and include it in nested code-signing/notarization and clean-machine launch tests. PyInstaller supports adding binaries in the spec, but XfinAudio still owns this integration ([PyInstaller spec-file documentation](https://pyinstaller.org/en/stable/spec-files.html)). The chosen FFmpeg build configuration also needs explicit license/source-offer inventory; “FFmpeg” is not one uniform redistribution license.

### libebur128 binding — technically excellent meter, worse product integration today

libebur128 directly implements integrated loudness, EBU Tech 3342 LRA, and true-peak scanning, including conformance tests ([libebur128 project](https://github.com/jiixyj/libebur128)). Its DSP is native and avoids subprocess parsing. However, it accepts PCM frames, not MP3/FLAC/M4A paths. XfinAudio would still need a reliable streaming decoder, channel mapping, and block feeder. Reusing `librosa.load()` would risk whole-track allocation and accidental mono/resampling policy; using libsndfile alone may not match FFmpeg's codec coverage.

The binding also adds a native-library ABI, Python binding maintenance, universal/per-architecture macOS builds, PyInstaller collection, and code-signing work. It becomes the better long-term option only if profiling proves subprocess launch/parsing materially harmful **and** XfinAudio adopts a shared streaming decode layer for several analyzers. It is not the lowest-risk first implementation.

### pyloudnorm — useful validation oracle, not the production adapter

pyloudnorm implements BS.1770-4 integrated loudness and now exposes an LRA calculation, but its documented usage reads the full signal into an ndarray. That is a poor fit for thousands of DJ tracks and duplicates decode/memory work already performed elsewhere. More importantly, pyloudnorm does not currently provide the requested true-peak meter; the upstream true-peak request remains open. Its own LRA documentation says “attempt to measure,” which is weaker than the production requirement ([pyloudnorm documentation](https://github.com/csteinmetz1/pyloudnorm), [true-peak request](https://github.com/csteinmetz1/pyloudnorm/issues/61)).

It is valuable as an **independent test oracle** for integrated loudness on synthetic WAV fixtures, not as the sole production engine.

### New pure-Python implementation — reject

A new meter would own K-weighting, block overlap, absolute and relative gates, multichannel weighting, LRA percentiles, oversampled true peak, numerical edge cases, and conformance testing. Python loops would be slow; a vectorized implementation would still require large decoded arrays and effectively recreate pyloudnorm. This is high maintenance with no product advantage. Do not spend XfinAudio's engineering budget rebuilding an established metering standard.

### Required naming correction

Use **loudness**, not “sonority,” in code and UI. Sonority can mean timbral richness or psychoacoustic quality; the measured quantity here is program loudness. Prefer `true_peak_dbtp` over `true_peak_db` so sample peak dBFS and true peak dBTP cannot be confused.

## 2. Performance strategy for thousands of tracks

### Accept the hard limit

Exact integrated LUFS and LRA are whole-program measurements. There is no honest way to avoid decoding the entire track while retaining the claimed measurement semantics. Partial sampling can be offered only as a separately named estimate and must never populate the exact EBU R128 fields. True peak likewise needs the entire signal if the stored value claims to be the track maximum.

### Make exact work incremental, prioritized, and bounded

1. **Metadata scan remains fast.** Do not add FFmpeg loudness measurement to the synchronous metadata phase in `library/scan_service.py:149-225`. Return records, then complete loudness lazily.
2. **Cache by analyzer version plus independent audio identity.** Reuse `audio_md5` where it represents stable audio essence; otherwise use mtime+size as a fallback. Store a loudness analysis version and engine/build fingerprint. Do not let a loudness write refresh the identity used to validate unrelated spectral profiles.
3. **Analyze only missing/stale tracks.** Incremental rescan should enqueue new or changed audio, not the entire library. Persist each successful result immediately so cancellation/crash loses at most in-flight tracks.
4. **Prioritize product value.** Queue selected tracks and current recommendation candidates first, then visible/current-folder tracks, then the remaining library. A “Consistent Loudness” strategy should clearly report coverage and may trigger analysis of its bounded candidate pool before recommendation.
5. **Bound concurrency by storage and thermal behavior, not `cpu_count - 1`.** Each FFmpeg process performs native decode/filter work and may create its own threads. Start conservatively (for example, 2 workers; possibly 1 for slow external drives and 2-4 for SSDs), benchmark, and make the cap configurable. The existing `cpu_count - 1` policy in `audio/batch_analyzer.py:32-35` and the completion workers is not automatically safe for multiple FFmpeg processes.
6. **Use one analysis scheduler.** The controller intentionally serializes spectral, danceability, and edge analysis to avoid CPU saturation (`desktop/library_controller.py:521-607`). Adding an independent loudness pool would defeat that policy. Extend the serialized chain or, better, replace the growing worker chain with a resource-aware analysis queue.
7. **Cancellation must reach child processes.** Cancelling futures is insufficient once FFmpeg has started. The adapter must terminate the process, wait briefly, then kill if necessary, while still draining pipes safely. Shutdown must not leave child processes behind.
8. **Measure throughput before choosing defaults.** Capture real-time factor, tracks/minute, cache-hit ratio, failure rate, peak memory, UI responsiveness, and temperature on Intel and Apple Silicon with internal SSD and representative external storage.

### Optional later optimization

The current spectral, danceability, edge, and proposed loudness analyzers decode the same file in separate passes. A future shared streaming decode service could fan PCM blocks to multiple native analyzers in one pass, but that is a larger architectural change. Do not smuggle it into WU2. First ship a correct cached loudness pass and gather evidence that repeated decode is the actual bottleneck.

## 3. Risks and gaps in WU1-WU4

### WU1 — port and adapter

- Define a frozen, versioned `LoudnessProfile` rather than returning an unstructured triple.
- Specify integrated LUFS, LRA in LU, true peak in dBTP, channel handling (including mono/dual-mono), silence/short-file semantics, numeric bounds, and engine version.
- Define typed errors/outcomes and a capability preflight for executable present, executable allowed, `ebur128` filter present, and true-peak support.
- Make command construction injectable and testable without real audio or a real FFmpeg binary.
- Keep subprocess execution shell-free; paths are argument tokens, never interpolated command strings.
- Pin and document the FFmpeg binary/build. System `PATH` may be an explicit developer fallback, not the packaged default.

### WU2 — persistence and batch integration

- `audio/batch_analyzer.py` is not a generic batch pipeline; its types, worker entry point, cache, and results are spectral-specific (`audio/batch_analyzer.py:17-46`). Either extract a generic bounded dispatcher or create a loudness-specific batch service without pretending the current module is generic.
- The actual desktop lazy lifecycle is `spectral_completion_worker.py` plus `library_controller.py`, not only `batch_analyzer.py`. WU2 must cover start, progress, cache read, per-result persistence, immutable state update, cancellation, shutdown, and handoff to the next analyzer.
- **Critical cache bug risk:** each profile update rewrites shared `file_mtime_ns` and `file_size_bytes`, while each cache reader trusts those fields (`library/track_repository.py:168-335`). If audio changes and loudness is recomputed first, stale spectral/danceability/edge JSON can be accepted under the new identity. Introduce per-analysis identity/version columns or atomically invalidate every sibling profile whenever identity changes.
- Three nullable scalars cannot distinguish never analyzed, stale, unsupported, and failed. Store a versioned JSON profile plus independent identity/status, or add equivalent explicit columns. If scalar columns are retained for queryability, they should be a projection of the versioned result.
- Bump `SCHEMA_VERSION`; cover v4-to-v5 migration, fresh database creation, future-version rejection, rollback/backup, corrupted values, and preservation/invalidation on rescan.
- Do not silently preserve old loudness after the underlying audio changes merely because tags or path are stable. Conversely, avoid recalculating exact loudness for metadata-only edits when `audio_md5` proves audio essence is unchanged.

### WU3 — scoring and strategy

- Add the component to `SCORED_COMPONENTS`; decide explicitly whether it belongs to compatibility or mixability. It is closer to transition/set continuity than musical compatibility.
- Add a new weight field with **default `0.0`**. Existing strategies instantiate `ScoringWeights` with omitted fields; a non-zero model default would silently alter all of them. Existing weights already total 1.10, and `_weighted_total()` normalizes them (`recommendation/scoring.py:416-433`), so the design must discuss relative dilution rather than require a sum of 1.0.
- Keep loudness out of `required_fields`. Missing required metadata currently zeros the entire transition (`recommendation/scoring.py:140-169`); incomplete background loudness should instead be neutral or make the loudness-specific strategy unavailable/explicitly degraded.
- Define the score curve and calibration evidence. Integrated-LUFS delta is the primary adjacent consistency input. LRA should be a separate dynamic-character comparison or informational field; true peak should drive a safety/quality warning, not masquerade as perceived loudness similarity.
- **Pairwise drift gap:** maximizing adjacent similarity can produce a set that walks gradually from very quiet to very loud. If the product promise is whole-set consistency, add an anchor/target deviation or whole-set variance/range objective, not only `score_loudness_consistency(left, right)`. The optimizer already has a separate slot-level energy-arc term because a playlist shape is not reducible to pair scores (`recommendation/optimizer.py:32-97`).
- Define strategy behavior for partial coverage. Neutral `0.5` is correct for ordinary strategies but can make a loudness-specific strategy appear functional while mostly ignoring loudness. Require a minimum analyzed coverage or complete the bounded candidate pool first, and warn honestly when falling back.
- Register the strategy in `StrategyName` and `_STRATEGIES` (`recommendation/strategies.py:12-44`). Test registry, candidate planning, recommendation, replacement/reorder rescoring, explanations, settings serialization if exposed, and deterministic tie-breaking.

### WU4 — minimal UI

- A strategy entry already flows automatically from registry to catalog to `BuildViewModel` and the combo (`application/strategy_catalog.py:20-31`, `desktop/build_view_model.py:41-51`, `desktop/screens/build_screen.py:327-330`). Do not build a redundant selector.
- “Minimal UI” still needs a product definition. At minimum show analysis coverage/progress, distinguish unavailable/failed/pending, and expose LUFS/LRA/dBTP for a selected track or library column(s). The current library table is a fixed 12-column contract (`desktop/screens/library_screen.py:25-38`; `desktop/table_populators.py:40-70`).
- `AppState` only models spectral completion progress (`desktop/app_state.py:66-81`), and profile application requires immutable replacement in both `scanned_records` and `records_by_path` (`desktop/app_state_transitions.py:44-99`). WU4 must include that state transition instead of mutating records in place.
- Recommendation buttons ignore analysis completion (`desktop/build_view_model.py:53-59`). Decide whether the loudness strategy waits, analyzes its candidate pool, degrades with a warning, or is disabled until coverage is sufficient.
- Avoid displaying false precision: one decimal place for LUFS/LRA/dBTP is adequate unless conformance evidence justifies more.

## 4. Ranked improvements

1. **Fix cache identity architecture before adding loudness.** Give every derived profile its own analysis version and audio-identity binding, or atomically invalidate siblings on identity change.
2. **Define the product semantics of “consistent loudness.”** Choose whole-set target/range behavior, missing-coverage policy, and whether loudness is a hard strategy prerequisite before designing the score.
3. **Adopt a versioned `LoudnessProfile` and typed result model.** Include integrated LUFS, LRA LU, true peak dBTP, engine/build fingerprint, analysis version, and status.
4. **Use a pinned, bundled FFmpeg adapter with capability preflight and conformance fixtures.** Never rely solely on PATH or parse arbitrary FFmpeg versions.
5. **Integrate through one resource-aware lazy analysis scheduler.** At minimum serialize loudness with the existing three completion pools; ideally stop adding one bespoke Qt worker per profile.
6. **Make analysis incremental and priority-driven.** Selected/candidate tracks first, persistent per-track writes, exact cache reuse, bounded concurrency, and child-process cancellation.
7. **Separate metrics by meaning.** Integrated LUFS drives loudness continuity; LRA describes dynamics; true peak drives headroom/clipping warnings. Do not compress all three into one opaque “sonority” score.
8. **Protect existing recommendations.** Add loudness weight at 0.0 by default, explicitly opt strategies in, and test that all existing strategy results remain unchanged when loudness data is absent.
9. **Expand packaging/release gates.** Verify binary architecture, executable presence, filter capability, clean-account launch, nested signing/notarization behavior, and FFmpeg license/source inventory.
10. **Benchmark before tuning worker count or considering libebur128.** Switch to an in-process binding only on measured evidence and only with a credible streaming decoder plan.

## 5. Open questions for the other reviewer

1. Is “Consistent Sonority” intended to minimize adjacent LUFS jumps, keep the whole set near the anchor, or target an operator-selected LUFS? Which promise should the UI make?
2. Should the strategy be unavailable below a coverage threshold, block while its candidate pool is analyzed, or return a degraded recommendation with an explicit warning?
3. Do you agree that LRA and true peak should remain explanatory/quality signals rather than share one transition score with integrated LUFS?
4. Would you extend the existing serialized worker chain for v1, or require a generic analysis scheduler before introducing a fourth derived profile?
5. How should mono be handled: native mono weighting or dual-mono compensation? Which behavior matches the DJ-library product expectation?
6. What exact FFmpeg build, architectures, codecs, and license configuration should be shipped, and who owns its update/security cadence?
7. Is `audio_md5` sufficiently available and semantically stable across every supported format to be the primary loudness cache key, or do we need a new audio-essence fingerprint?
8. What conformance corpus and tolerances will prove integrated LUFS, LRA, and true peak across FFmpeg upgrades?
9. Should loudness analysis be automatic for the whole library, opt-in, idle-only, or triggered by selecting the loudness strategy?
10. Is a separate estimated/fast mode worth the product complexity, given that it cannot truthfully populate exact EBU R128 metrics?

## Final recommendation

Approve the feature concept but **do not approve the current WU1-WU4 design unchanged**. Revise WU1 around a versioned profile and pinned FFmpeg capability contract; revise WU2 around independent cache identity and the real desktop worker lifecycle; revise WU3 around whole-set loudness semantics and partial-coverage honesty; keep WU4 small by reusing the existing strategy catalog while adding only the progress/value/status surface needed to prevent misleading results.
