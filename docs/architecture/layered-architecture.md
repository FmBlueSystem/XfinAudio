# XfinAudio Layered Architecture Map

XfinAudio should evolve toward a layered architecture where UI renders and adapts, application use cases orchestrate, domain modules decide product behavior, ports describe external contracts, and infrastructure touches real systems. This document maps the current repo to those layers and identifies the next reviewable SDD/TDD slices.

## Quick path

1. Keep `xfinaudio.desktop` as Presentation and adapter orchestration.
2. Grow `xfinaudio.application` as the use-case layer.
3. Keep product rules in domain packages: `recommendation`, `library`, `exporting`, `quality`, `metadata`, and selected pure `audio` modules.
4. Extract explicit ports only when an implementation boundary is causing coupling or test pain.
5. Move filesystem, Serato, settings persistence, and external-library adapters behind those ports over time.

## Intended layers

| Layer | Responsibility | Current examples | Must not own |
|---|---|---|---|
| 1. Presentation / UI | Widgets, labels, screens, layout, user interaction. | `desktop/screens/*`, `desktop/theme.py`, `desktop/shortcuts.py` | Business ranking, export decisions, persistence rules. |
| 2. Presentation adapters | Translate UI events to commands and render results. | `desktop/*_controller.py`, `desktop/*_view_model.py`, `desktop/*_coordinator.py` | Core product decisions or durable state policy. |
| 3. Application / Use cases | Orchestrate product workflows across domain modules and ports. | `application/playlist_workflow.py` | QWidget access, table rendering, modal dialogs. |
| 4. Domain / Business rules | Pure product policy and deterministic decisions. | `recommendation`, `quality`, `metadata`, parts of `library`, `exporting`, `audio` | PySide6, desktop imports, concrete UI state. |
| 5. Ports / Contracts | Interfaces for repositories, exporters, analyzers, settings, and external systems. | Protocols currently embedded in `library`, `config`, `exporting`, `desktop/app_state.py` | Concrete filesystem/UI implementation details. |
| 6. Infrastructure / Adapters | Concrete filesystem, Serato, audio, settings, and repository implementations. | `library/track_repository.py`, `exporting/serato_*`, `config/settings_repository.py`, audio loaders | UI decisions or domain policy. |

## Dependency rule

Allowed direction:

```text
Presentation -> Presentation adapters -> Application -> Domain
                                    Application -> Ports
Infrastructure -> Ports / Domain data models
```

Forbidden direction:

```text
Domain/Application -> desktop/PySide6
Domain -> concrete UI state
Domain -> modal dialogs, tables, labels, or Qt workers
```

## Current package assignment

| Package | Current layer assignment | Notes |
|---|---|---|
| `desktop` | Layers 1 and 2, plus runtime UI state adapters | Correct home for PySide6. Still contains legacy compatibility and runtime-state sync. |
| `application` | Layer 3 | Should grow. It currently orchestrates playlist workflow but not every product use case. |
| `recommendation` | Layer 4 | Mostly well assigned. Imports `audio`, `library`, and `quality` for scoring and reports. |
| `quality` | Layer 4 | Mostly well assigned. It imports recommendation/exporting concepts for report context. |
| `metadata` | Layer 4 | Clean, no outbound package dependency in the current import scan. |
| `library` | Layers 4, 5, and 6 mixed with explicit ports and pure scan planning | Contains models, pure scan candidate planning, scan execution, playlist/track repositories, and persistence. Repository ports are explicit; scan planning is now separated from metadata/audio execution. |
| `exporting` | Layers 4, 5, and 6 mixed with explicit readiness and software catalog boundaries | Contains export readiness/planning, pure software/extension catalog, and concrete Serato/Rekordbox/Traktor/VirtualDJ writers. |
| `audio` | Layers 4 and 6 mixed with explicit analyzer and planning boundaries | Contains pure spectral profile logic, pure batch-analysis planning/cache policy, analyzer contracts, and external audio-library execution. |
| `config` | Layers 4/5/6 with an explicit settings port | Settings models remain pure, `config.ports.SettingsRepositoryPort` defines the persistence contract, and `settings_repository.py` remains the concrete JSON/filesystem adapter. |

## Verified architecture invariants

These checks should produce no output:

```bash
python - <<'PY'
from pathlib import Path
for path in sorted(Path('src/xfinaudio').rglob('*.py')):
    text = path.read_text(errors='ignore')
    if 'desktop' not in path.parts and 'PySide6' in text:
        print(path)
PY
```

```bash
python - <<'PY'
from pathlib import Path
for path in sorted(Path('src/xfinaudio').rglob('*.py')):
    text = path.read_text(errors='ignore')
    if 'desktop' not in path.parts and 'xfinaudio.desktop' in text:
        print(path)
PY
```

## Mixed-layer hotspots

| Hotspot | Why it matters | Recommended treatment |
|---|---|---|
| `library` repositories and scan service | Domain models, repository contracts, concrete persistence, scan planning, and scan execution are close together. | Keep pure scan planning in `library.scan_planning`; continue extracting execution or persistence seams only around use cases that need substitution or narrower tests. |
| `exporting` writers | Export decisions, software catalog, and concrete file/format writers share package space. | Keep pure export planning/readiness/software catalog separate; introduce writer ports when application use cases need more substitution. |
| `audio` analysis | Pure spectral color policy, batch planning/cache decisions, and external audio-library loading live in the same package. | Keep pure spectral models and analysis planning independent; treat analyzer execution and thread/process dispatch as infrastructure. |
| `config` | Settings schema and concrete repository are still adjacent, but `SettingsRepositoryPort` now makes the persistence boundary explicit. | Keep desktop/application code depending on the port; move future settings workflows into application services only when behavior requires it. |
| Desktop shell compatibility surfaces | Layout method grafting and legacy AppState read/write compatibility now live behind explicit compatibility surfaces. | Continue shrinking or removing each compatibility surface independently; do not move new product rules into them. |
| Runtime AppState sync | `AppController` and `ScanService` mutate runtime snapshot/progress fields. | Consider a runtime-state model only if progress/cancellation testing becomes painful. |

## SDD/TDD slice backlog

These are deliberately small. Do not batch them into a mega-refactor.

### Slice 1: Application export use case boundary

**Status:** Completed in PR #124.

**Goal:** move export orchestration decisions behind an application-level use case while keeping UI copy and dialogs in `desktop`.

| Item | Target |
|---|---|
| New/changed module | `xfinaudio.application.export_playlist` or similar |
| Candidate ports | export writer, export destination resolver, readiness/report provider |
| Keep in desktop | folder picker, confirmation dialogs, status labels, error dialogs |
| Tests first | use-case unit tests with fake writer/readiness dependencies |
| Out of scope | Changing Serato/Rekordbox/Traktor/VirtualDJ file formats |

### Slice 2: Library repository port boundary

**Status:** Completed in PR #126.

**Goal:** make playlist/track persistence contracts explicit before moving more saved-playlist logic into application use cases.

| Item | Target |
|---|---|
| New/changed module | `xfinaudio.library.ports` or `xfinaudio.application.ports` |
| Candidate ports | `TrackRepositoryPort`, `TrackDisplayRepositoryPort`, `TrackSpectralProfileCacheReaderPort`, `TrackSpectralProfileCachePort`, `PlaylistRepositoryPort` |
| Keep in infrastructure | concrete JSON/SQLite/filesystem repository behavior |
| Tests first | application/use-case tests using in-memory fakes |
| Out of scope | Database migration or storage format changes |

### Slice 3: Saved playlist application service

**Status:** Completed in PR #128.

**Goal:** move save/update/delete/re-export orchestration out of `desktop.playlist_coordinator` into an application service.

| Item | Target |
|---|---|
| New/changed module | `xfinaudio.application.saved_playlists` |
| Depends on | repository ports and export use case boundary |
| Keep in desktop | editor widgets, row selection, user messages |
| Tests first | service tests for save, rename, delete, and re-export commands |
| Out of scope | UI redesign |

### Slice 4: Audio analyzer adapter boundary

**Status:** Completed in PR #130.

**Goal:** separate pure spectral profile policy from concrete audio loading/analyzer execution.

| Item | Target |
|---|---|
| New/changed module | analyzer port plus concrete adapter wrapper |
| Keep pure | `SpectralProfile` model and color/cohesion policy |
| Infrastructure | librosa/soundfile execution and filesystem access |
| Tests first | fake analyzer tests for workflow behavior |
| Out of scope | New DSP features or audio mutation |

### Slice 4b: Audio analysis planning boundary

**Status:** In progress.

**Goal:** separate pure batch-analysis planning/cache decisions from thread/process analyzer execution.

| Item | Target |
|---|---|
| New/changed module | `xfinaudio.audio.analysis_planning` |
| Keep pure | cache-hit selection and duplicate pending-path selection |
| Infrastructure | `xfinaudio.audio.batch_analyzer` thread/process/sequential execution |
| Tests first | planning unit tests plus batch analyzer duplicate scheduling test |
| Out of scope | New DSP features, spectral math changes, audio mutation, or UI changes |

### Slice 5: Legacy desktop shell cleanup

**Status:** Partially completed through reviewable sub-slices.

**Goal:** reduce dynamic layout method grafting and legacy MainWindow read/write compatibility after application boundaries are stronger.

| Completed sub-slice | Result | Evidence |
|---|---|---|
| Desktop shell compatibility boundary | Moved legacy layout method installation out of `desktop/layout.py` and into `desktop/shell_compat.py`. | PR #134; `openspec/specs/desktop-shell-compat-boundary/spec.md` |
| MainWindow state write compatibility boundary | Reduced `MainWindow.__setattr__` to a thin delegator and moved legacy AppState write policy into `desktop/shell_compat.py`. | PR #138; `openspec/specs/mainwindow-state-compat-boundary/spec.md` |
| MainWindow state read compatibility boundary | Reduced `MainWindow.__getattr__` to a thin delegator and moved legacy AppState/delegated read policy into `desktop/shell_compat.py`. | PR #142; `openspec/specs/mainwindow-read-compat-boundary/spec.md` |
| Shell compatibility surface split | Historical split of `desktop/shell_compat.py` into layout/state surfaces; the layout surface was later removed after the graft map reached zero. | PR #148; PR #150 archive; `openspec/specs/split-shell-compat-surfaces/spec.md` |
| MainWindow explicit shell surfaces | Historical migration away from the facade; current `MainWindow` uses `desktop.shell_state_compat` only after the layout graft surface was removed. | Issue #151; `openspec/specs/mainwindow-explicit-shell-surfaces/spec.md` |
| Library shell methods explicit | Removed `choose_folder` and `_refresh_idle_action_state` from dynamic layout grafting and made them explicit `MainWindow` delegators. | Issue #155; `openspec/changes/library-shell-methods-explicit/` |
| Export shell methods explicit | Removed the Export / Safe Export method group from dynamic layout grafting and made it explicit `MainWindow` delegation to export actions. | Issue #159; `openspec/changes/export-shell-methods-explicit/` |
| Settings shell methods explicit | Removed `_open_settings_dialog` and `_on_spectral_cohesion_changed` from dynamic layout grafting and made them explicit `MainWindow` delegators to `SettingsController`. | Issue #165; `openspec/changes/settings-shell-methods-explicit/` |
| Scan entry shell methods explicit | Removed scan entry and scan cleanup methods from dynamic layout grafting and made them explicit `MainWindow` delegators to `ScanService` and `LibraryController`. | Issue #169; `openspec/changes/scan-entry-shell-methods-explicit/` |
| Library table shell methods explicit | Removed Library table rendering, filtering, selected-folder persistence, and restore methods from dynamic layout grafting and made them explicit `MainWindow` delegators to `LibraryController`. | Issue #173; `openspec/changes/library-table-shell-methods-explicit/` |
| Metadata filter shell methods explicit | Removed metadata filter selection and metadata-record provider methods from dynamic layout grafting and made them explicit `MainWindow` delegators to `LibraryController`. | Issue #177; `openspec/changes/metadata-filter-shell-methods-explicit/` |
| Prep Copilot shell methods explicit | Removed Prep Copilot generate/apply methods from dynamic layout grafting and made them explicit `MainWindow` delegators to the Prep Copilot controller. | Issue #181; `openspec/changes/prep-copilot-shell-methods-explicit/` |
| Copilot variant shell bridge explicit | Removed `_on_copilot_variant_applied` from dynamic layout grafting and made it an explicit `MainWindow` delegator to `PrepCopilotController.on_variant_applied(index)`. | Issue #189; `openspec/changes/copilot-variant-shell-bridge-explicit/` |
| Spectral completion shell methods explicit | Removed the five spectral completion lifecycle methods from dynamic layout grafting and made them explicit `MainWindow` delegators to `LibraryController`; `LEGACY_LAYOUT_METHODS` is now empty. | Issue #193; `openspec/changes/spectral-completion-shell-methods-explicit/` |
| Empty shell layout compatibility surface removed | Deleted the empty `desktop.shell_layout_compat` module, removed its MainWindow install call, and narrowed `desktop.shell_compat` to state compatibility only. | Issue #197; `openspec/changes/remove-empty-shell-layout-compat/` |
| Recommendation shell methods explicit | Removed recommendation request, worker lifecycle, completion/failure, and DJ readiness table methods from dynamic layout grafting and made them explicit `MainWindow` delegators to `RecommendationService` and `DjReadinessController`. | Issue #185; `openspec/changes/recommendation-shell-methods-explicit/` |

| Remaining item | Target |
|---|---|
| Compatibility surface removal | Shrink or remove each compatibility surface independently as direct callers migrate away from legacy aliases. |
| MainWindow wiring cleanup | Continue moving UI orchestration and controller wiring out of `desktop/main_window.py` only when a small tested boundary is clear. |
| Tests first | Keep focused shell/controller tests before removing or splitting compatibility paths. |
| Out of scope | Product behavior changes. |

## Decision guidance

Use this rule when deciding where new code belongs:

| Question | If yes, place it in |
|---|---|
| Does it render widgets, read tables, or show dialogs? | `desktop` |
| Does it translate a click into a command or render a result? | `desktop` controller/view model |
| Does it coordinate multiple product modules? | `application` |
| Does it decide recommendation, readiness, metadata, or export policy? | domain package |
| Is it a contract for storage/export/audio/settings? | ports layer |
| Does it touch filesystem, Serato, audio libraries, or persistence? | infrastructure adapter |

## Current recommendation

Do **not** reopen the completed AppState responsibility-separation work. The main Application, Ports, and Infrastructure boundary slices now have explicit seams, and Slice 5 has already split the worst legacy MainWindow read/write and layout compatibility into explicit shell compatibility surfaces. The next useful architectural move is to remove or shrink those surfaces one at a time, not to add more behavior to them.
