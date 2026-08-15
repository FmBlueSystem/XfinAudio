# Library File Watcher Specification

## Purpose

While a folder is scanned into the SQLite track database, external tools
(e.g. Mixed In Key) may modify, create, or remove files under that folder
without XfinAudio's knowledge, leaving the library and recommendation views
silently stale. This capability adds passive, debounced filesystem-change
detection for the currently scanned folder and surfaces a user-actionable
"Changes detected — Rescan" affordance. It never rescans automatically and
never introduces a new scan or analysis path — it only adds a new trigger
source for the existing `ScanService.scan_selected_folder()` pipeline.

## Requirements

### Requirement: Watcher observes the currently scanned folder

The system MUST observe, recursively, the folder passed to the last
successful scan for filesystem create/modify/delete events, using an
OS-level watch mechanism rather than polling.

#### Scenario: Watcher arms after a successful scan
- GIVEN the user has successfully scanned a folder via
  `scan_selected_folder()`
- WHEN the scan completes
- THEN the watcher starts observing that folder recursively for filesystem
  events

#### Scenario: No watch before any scan has completed
- GIVEN no folder has been successfully scanned yet
- WHEN the app is running
- THEN no filesystem watch is active

### Requirement: Filesystem changes are debounced before surfacing

The system MUST coalesce bursts of filesystem events observed on the
watched folder into a single settled "changes detected" signal, using a
settle window with no further events before flagging the change.

#### Scenario: Rapid multi-file writes coalesce into one activation
- GIVEN the watcher is actively observing the scanned folder
- WHEN an external tool writes to many files in the folder in rapid
  succession, faster than the settle window
- THEN the "changes detected" state activates exactly once for that burst,
  not once per file

#### Scenario: A single change also surfaces after the settle window
- GIVEN the watcher is actively observing the scanned folder
- WHEN one file under the folder is created, modified, or removed and the
  settle window elapses with no further events
- THEN the "changes detected" state activates

### Requirement: Changes are surfaced as a user-actionable affordance, never an automatic rescan

The system MUST NOT trigger a rescan automatically under any circumstance.
Detected, settled changes MUST surface as a dismissible-until-acted-on
"Changes detected — Rescan" affordance on the Library screen that the user
must explicitly click to trigger a rescan.

#### Scenario: Settled change shows the affordance, not a rescan
- GIVEN the watcher observes a settled filesystem change
- WHEN the settle window elapses
- THEN the Library screen shows a "Changes detected — Rescan" affordance
- AND no scan is executed automatically

#### Scenario: Affordance persists until the user acts or the folder changes
- GIVEN the "Changes detected — Rescan" affordance is visible
- WHEN the user takes no action
- THEN the affordance remains visible and no rescan occurs

### Requirement: The affordance invokes the existing scan pipeline unchanged

Clicking the "Changes detected — Rescan" affordance MUST call the existing
`ScanService.scan_selected_folder()` entry point unchanged, and MUST clear
the "changes detected" state once that scan completes.

#### Scenario: Clicking the affordance runs the existing scan pipeline
- GIVEN the "Changes detected — Rescan" affordance is visible
- WHEN the user clicks it
- THEN `scan_selected_folder()` executes exactly as it does from the manual
  "Scan" button, with no new scan semantics
- AND the "changes detected" state clears once that scan completes

### Requirement: Watcher lifecycle is tied to scan state and folder selection

The system MUST pause the watcher for the duration of an in-flight scan and
resume it afterward, MUST stop the watch on the previous folder and arm a
new watch when a different folder is scanned, and MUST stop the watcher
cleanly on application shutdown.

#### Scenario: Watcher pauses during an in-flight scan
- GIVEN the watcher is actively observing a folder
- WHEN a scan of that folder begins (manual or affordance-triggered)
- THEN the watcher pauses for the duration of the scan
- AND resumes observing once the scan completes or is canceled, without
  self-triggering from the scan's own filesystem reads

#### Scenario: Switching folders re-arms the watch
- GIVEN the watcher is observing folder A
- WHEN the user successfully scans a different folder B
- THEN the watch on folder A stops
- AND a new watch arms on folder B

#### Scenario: Watcher stops cleanly on app shutdown
- GIVEN the watcher is actively observing a folder
- WHEN the application shuts down
- THEN the watcher/observer thread stops with no leaked threads

### Requirement: State updates follow immutable AppState conventions

Detected-change state MUST be represented as new `AppState` field(s)
updated via `state.model_copy(update=...)`, not as a mutable flag bolted
onto an existing object.

#### Scenario: Changes-detected state is applied via model_copy
- GIVEN a settled filesystem change is detected
- WHEN the app updates state to reflect it
- THEN the update MUST go through `state.model_copy(update=...)` and MUST
  NOT mutate an existing `AppState` instance in place

## Non-Goals

- **No automatic rescan.** The watcher never triggers
  `scan_selected_folder()` on its own; a rescan only ever happens from an
  explicit user click on the surfaced affordance.
- **No DSP or audio-analysis changes.** The watcher reacts to filesystem
  metadata-change events only. It never inspects or re-analyzes audio
  bytes, and the rescan it triggers is the existing, unmodified
  `scan_folder()` pipeline.
- **No audio mutation.** This capability does not read, write, or modify
  audio file contents.
- **No multi-folder or whole-library watching.** Only the single folder
  passed to the last successful scan is watched at any time; there is no
  "watched folder list" or independent whole-library watch concept.
- **No change to cache-validity logic.** `TrackRepository`'s existing
  `audio_md5` / `file_mtime_ns` / `file_size_bytes` based decision of
  whether a cached spectral/danceability profile is kept or invalidated on
  rescan is unchanged by this capability.
- **No standalone background service.** The watcher thread/observer lives
  and dies with the running desktop app process; there is no daemon outside
  it.

## Acceptance Criteria

Derived from the proposal's Success Criteria:

- [ ] After a file under the currently scanned folder is created, modified,
      or removed, and after the settle window elapses with no further
      events, the Library screen shows a "Changes detected — Rescan"
      affordance.
- [ ] Clicking the affordance triggers the existing
      `scan_selected_folder()` pipeline unchanged and clears the "changes
      detected" state on completion.
- [ ] No rescan is ever triggered automatically without a user click.
- [ ] Bursts of rapid filesystem events coalesce into a single affordance
      activation, not one per file.
- [ ] The watcher pauses during an in-flight scan and resumes afterward
      without spurious self-triggering.
- [ ] Switching to a different folder stops watching the old folder and
      arms the watch on the new one.
- [ ] The watcher/observer thread stops cleanly on app shutdown and on
      explicit folder switch, with no leaked threads across test runs.
- [ ] `watchdog` is added as a pinned dependency and `uv.lock` resolves.
- [ ] Full verification suite (`pytest`, `pyright`, coverage gate,
      `ruff check`, `ruff format --check`, release gate script) passes.
