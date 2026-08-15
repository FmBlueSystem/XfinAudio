# Proposal: Library File Watcher — Detect Changes, Prompt Rescan

## Intent

Users run Mixed In Key (or a similar external tagging tool) against their
library *after* XfinAudio has already scanned it into the SQLite track
database. Today nothing in the app notices that files on disk changed —
the user has to remember to click "Scan" again, and until they do, the
library and recommendation views quietly work from stale metadata with no
indication anything is wrong.

This change adds passive filesystem-change detection for the currently
scanned folder. When XfinAudio notices that one or more files under the
scanned folder were modified, created, or removed since the last scan, it
surfaces a "Changes detected — Rescan" affordance instead of an automatic,
unrequested rescan. The user stays in control of when the (potentially
expensive) rescan runs; the app only removes the burden of remembering to
check.

Success looks like: after an external tool finishes writing updated tags to
files under the scanned folder, XfinAudio settles on the change within a
few seconds and shows a clear, dismissible-until-acted-on affordance. The
existing `scan_selected_folder()` / `PlaylistWorkflowService.scan_folder()`
pipeline executes unchanged when the user acts on it — this proposal adds a
trigger source, not a new scan path.

## Proposal Question Round

This proposal was authored in automatic (non-interactive) mode per the
delegation request. The product questions below were not put to the user
directly; the assumptions are stated explicitly so they can be corrected
before spec/design proceed.

1. **Detection mechanism — OS-level watch vs. polling?**
   Assumption: use an OS-level filesystem watch (`watchdog` library, which
   maps to FSEvents on macOS, inotify on Linux, `ReadDirectoryChangesW` on
   Windows) rather than periodic polling. The project is macOS-primary but
   not macOS-only, and `watchdog` gives near-instant, low-CPU notification
   without a polling loop stat-ing every file on an interval. `watchdog` is
   not currently a dependency; it will be added as a new pinned dependency
   (`>=lower,<upper` in `pyproject.toml`, `uv.lock` updated) per
   `AGENTS.md`.

2. **Trigger behavior — automatic rescan vs. user-confirmed affordance?**
   Assumption: **never rescan automatically**. Show a
   "Changes detected — Rescan" banner/affordance on the Library screen that
   the user clicks to trigger the existing scan pipeline. Rationale: Mixed
   In Key writes files incrementally over a batch job, an unattended
   rescan could fire mid-write and mid-user-workflow (e.g. while browsing
   results or mid-recommendation build), and reusing the same
   `scan_selected_folder()` entry point as the manual "Scan" button keeps
   this a pure new-trigger-source change with no new scan semantics.

3. **Debounce / settle time — how do we avoid scanning a half-written file?**
   Assumption: coalesce filesystem events per watched folder with a
   settle window (proposed default: 2 seconds of no further events) before
   flagging "changes detected," implemented as a `QTimer`-based debounce on
   the Qt main thread (consistent with the existing coalesced
   `_request_sync` pattern in `ScanService`), not a raw watchdog callback
   acting immediately. The 2-second default is a starting point, not a
   frozen constant — the design phase should treat it as reviewable to
   avoid degrading UX on unusually large synchronized MIK batch writes.

4. **Scope — selected/scanned folder only, or the whole library?**
   Assumption: watch only the folder that was last successfully scanned
   (the same folder passed to `scan_selected_folder()`), recursively,
   mirroring the recursive folder walk `library/scan_service.py` already
   performs. Selecting a different folder or re-scanning stops the old
   watch and (re-)arms a watch on the new folder. There is no
   "whole library" concept independent of the scanned folder today, so
   introducing one is out of scope.

5. **Should the watcher run during an active scan?**
   Assumption: pause (stop) the filesystem watch for the duration of an
   in-flight scan and re-arm it once the scan completes or is canceled,
   to avoid spurious events and CPU competition while the scan itself is
   reading the same directory tree.

### Assumptions Carried Into Spec/Design

- No audio mutation, no DSP scope: the watcher reacts to filesystem
  metadata-change events only and triggers the existing tag-driven
  `scan_folder()` pipeline; it never inspects or re-analyzes audio bytes
  itself.
- Change detection at the filesystem-event level flags "something in this
  folder changed" (created, modified, or removed path); the existing
  `TrackRepository` upsert logic (already using `audio_md5` and
  `file_mtime_ns`/`file_size_bytes`) remains the sole authority for
  deciding whether a given file's cached spectral/danceability profile
  should be kept or invalidated on the resulting rescan. This proposal
  does not change that logic.
- New files appearing under the watched folder also surface the "Changes
  detected" affordance (a new file is a change the user likely wants
  reflected), but this remains scoped to triggering the same full-folder
  rescan the "Scan" button already performs — not a new incremental/DSP
  analysis path.
- No background daemon or process outside the running desktop app; the
  watch thread/observer lives and dies with the app process and the
  currently scanned folder.
- Immutable `AppState` conventions apply: "changes detected" is new state
  surfaced via `state.model_copy(update=...)`, not a mutable flag bolted
  onto an existing object.

Please confirm or correct these five assumptions before spec/design begin;
absent correction, spec.md and design.md will proceed on this basis.

## Scope

### In Scope
- A new watcher component that observes the currently scanned folder for
  filesystem changes (create/modify/delete) using `watchdog`, recursively,
  scoped to the folder passed to the last successful scan.
- Debounced "changes detected" signal (settle window, coalesced across
  bursts of events) delivered onto the Qt main thread.
- New `AppState` field(s) representing "changes detected since last scan"
  and a Library-screen affordance ("Changes detected — Rescan") that,
  when clicked, calls the existing `ScanService.scan_selected_folder()`
  path unchanged.
- Watcher lifecycle wired to: start after a successful scan of a folder;
  stop/re-arm on folder change or new scan; pause during an in-flight
  scan; stop on app shutdown.
- New pinned dependency `watchdog` in `pyproject.toml` + `uv.lock`.

### Out of Scope
- Automatic, unattended rescanning. The trigger is always a user click on
  the surfaced affordance.
- Any new DSP/audio-analysis path. The rescan executed on user action is
  the existing `scan_folder()` pipeline, unchanged.
- Watching folders other than the currently scanned one, or any
  "multi-library" / "watched folder list" concept.
- Changes to `TrackRepository`'s existing mtime/size/`audio_md5`
  change-detection logic for deciding cache validity.
- A standalone background service/daemon outside the desktop app process.

## Capabilities

### New Capabilities
- `library-file-watcher`: passive, debounced filesystem-change detection
  for the currently scanned folder, surfaced as a user-actionable
  "Changes detected — Rescan" affordance.

### Modified Capabilities
- None functionally modified. `ScanService.scan_selected_folder()` gains
  one new caller (the affordance click handler) but its own behavior is
  unchanged.

## Approach

Use strict RED → GREEN → REFACTOR → VERIFY.

1. Add `watchdog` as a pinned dependency; verify `uv.lock` resolves and
   `uv run pyright` has stubs/compatible typing for it (add a minimal
   typed wrapper protocol if upstream stubs are insufficient, to keep the
   rest of the app decoupled from the third-party library's types).
2. Introduce a small library-layer watcher abstraction (e.g.
   `library/folder_watcher.py`) that wraps `watchdog`'s `Observer` behind
   an app-owned interface: `start(folder)`, `stop()`, and a debounced
   callback invoked after the settle window following the last observed
   event. Write RED tests against this abstraction using a fake/staged
   filesystem event source before wiring real `watchdog` internals, so
   the debounce/coalesce logic is unit-testable without real filesystem
   timing flakiness.
3. Wire the watcher into the desktop layer (likely a new
   `desktop/library_watch_service.py`, following the existing
   `ScanService` ownership pattern) that: owns the `QTimer`-based debounce
   on the Qt main thread, starts/stops/pauses the watcher per the
   lifecycle rules above, and updates `AppState` via
   `state.model_copy(update=...)` when a settled change is detected.
4. Add the Library-screen "Changes detected — Rescan" affordance bound to
   the new state field; clicking it calls the existing
   `scan_selected_folder()` entry point and clears the "changes detected"
   state.
5. Cover lifecycle edge cases with tests: rapid multi-file writes coalesce
   into one affordance activation; watcher pauses during an in-flight
   scan and does not re-trigger from the scan's own filesystem reads;
   switching folders stops the old watch and arms the new one; app
   shutdown cleanly stops the observer thread.

Expected to fit the 400-line review budget as a single slice; if the
`watchdog` dependency wrapper plus wiring plus UI affordance exceeds it,
chain via feature-branch-chain (watcher abstraction + tests first, then
desktop wiring + UI affordance).

## Affected Areas

| Area | Impact | Description |
|------|--------|--------------|
| `pyproject.toml`, `uv.lock` | Modified | Add pinned `watchdog` dependency |
| `src/xfinaudio/library/folder_watcher.py` | New | App-owned watcher abstraction wrapping `watchdog`, debounce/coalesce logic |
| `src/xfinaudio/desktop/library_watch_service.py` | New | Qt-thread-safe lifecycle owner (start/stop/pause), `QTimer` debounce, `AppState` update |
| `src/xfinaudio/desktop/scan_service.py` | Modified | Pause/resume watch service around scan start/completion; no change to scan execution itself |
| `AppState` model | Modified | New field(s) for "changes detected since last scan" |
| Library screen UI | Modified | New "Changes detected — Rescan" affordance bound to state, click calls existing scan entry point |
| `tests/` | Modified | New watcher-abstraction unit tests, debounce tests, lifecycle wiring tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Watcher fires mid-write from Mixed In Key, surfacing "changed" for a half-written file | Medium | Debounce/settle window before flagging; rescan itself is user-triggered so the user can wait for MIK to finish before clicking |
| Platform-specific `watchdog` backend behaves inconsistently (FSEvents vs inotify vs polling fallback) | Medium | Test against the abstraction's debounce contract, not backend internals; document macOS as the primary supported/tested platform |
| Watcher thread leaks or fails to stop cleanly on folder switch/app shutdown | Low | Explicit lifecycle tests for start/stop/pause across folder-change and shutdown paths |
| New dependency increases install/packaging surface | Low | Pin version range per `AGENTS.md`; `watchdog` is a widely used, actively maintained library with no heavy transitive deps |
| Feedback loop: watcher reacts to the scan's own directory reads | Low | Pause watcher during in-flight scan (`watchdog` reacts to writes not reads, but pausing removes ambiguity and CPU competition) |
| User ignores the affordance indefinitely and works from stale data without realizing | Low | Affordance stays visible/persistent until acted on or the folder changes again; out of scope for this proposal but flagged for a follow-up (e.g. status-bar persistence) |

## Rollback Plan

The watcher is additive: it introduces a new dependency, a new
library/desktop module pair, one new `AppState` field, and one new UI
affordance wired to an existing, unmodified scan entry point. Reverting
the change removes the dependency, the new modules, the state field, and
the affordance; `scan_selected_folder()` and the manual "Scan" button are
untouched and continue to work exactly as before. No persisted user data
(SQLite schema, export history) is affected.

## Dependencies

- New pinned runtime dependency: `watchdog` (`>=lower,<upper` range to be
  fixed during design/implementation; `uv.lock` updated accordingly).
- Existing `uv`, pytest, Pyright, Ruff, and release gate tooling.

## Success Criteria

- [ ] After a file under the currently scanned folder is created,
      modified, or removed, and after the settle window elapses with no
      further events, the Library screen shows a "Changes detected —
      Rescan" affordance.
- [ ] Clicking the affordance triggers the existing
      `scan_selected_folder()` pipeline unchanged and clears the
      "changes detected" state on completion.
- [ ] No rescan is ever triggered automatically without a user click.
- [ ] Bursts of rapid filesystem events (e.g. MIK writing many files in a
      batch) coalesce into a single affordance activation, not one per
      file.
- [ ] The watcher pauses during an in-flight scan and resumes afterward
      without spurious self-triggering.
- [ ] Switching to a different folder (new scan) stops watching the old
      folder and arms the watch on the new one.
- [ ] The watcher/observer thread stops cleanly on app shutdown and on
      explicit folder switch (no leaked threads across test runs).
- [ ] `watchdog` is added as a pinned dependency; `uv.lock` resolves.
- [ ] Full verification suite (`pytest`, `pyright`, coverage gate,
      `ruff check`, `ruff format --check`, release gate script) passes.
