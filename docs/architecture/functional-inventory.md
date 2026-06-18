# XfinAudio Functional Inventory and Module Boundaries

This document groups XfinAudio features into independent modules and marks where business logic should live versus where PySide6 UI code should live. The goal is to make refactors and tests smaller: domain/application modules own decisions; `xfinaudio.desktop` renders state and forwards user intent.

## Quick path

1. Keep pure business rules outside `xfinaudio.desktop`.
2. Let desktop classes read widgets, emit commands, render view models, and show errors.
3. Add unit tests at the module boundary before moving logic.
4. Keep one thin UI smoke test per screen or signal path.

## Boundary rule

| Layer | Owns | Must not own |
|---|---|---|
| `library` | Track records, scan results, persisted library state, metadata completeness | Qt widgets or screen decisions |
| `recommendation` | Strategy policy, candidate pools, scoring, sequence optimization, Prep Copilot planning | Combo-box labels, tables, status labels |
| `exporting` | Export plans, format writers, safe write rules, sidecars | Button state or modal dialogs |
| `quality` | DJ readiness and recommendation-quality reports | Screen rendering |
| `config` | Settings models and persistence | Modal settings workflow |
| `application` | Use-case orchestration across modules | QWidget access |
| `desktop` | PySide6 widgets, signal wiring, rendering, user interactions | Business ranking, export policy, readiness gates |

## Functional modules

| Module | User-facing functionality | Current primary files | Business owner target | UI owner target | Current tests | First separation slice |
|---|---|---|---|---|---|---|
| Library scan and persistence | Scan folders, parse metadata, persist searchable library | `src/xfinaudio/library/scan_service.py`, `src/xfinaudio/library/track_repository.py`, `src/xfinaudio/desktop/scan_service.py`, `src/xfinaudio/desktop/library_controller.py` | `xfinaudio.library` + `xfinaudio.application` | `xfinaudio.desktop.screens.library_screen`, `xfinaudio.desktop.library_controller` | `tests/test_scan_service.py`, `tests/test_track_repository.py`, `tests/test_main_window.py` | Move scan lifecycle decisions out of `desktop.scan_service`; keep QThread adapter in desktop only. |
| Library browse/filter | Search, sort, status filter, missing-metadata filter, table population | `src/xfinaudio/desktop/library_filter.py`, `src/xfinaudio/desktop/table_populators.py`, `src/xfinaudio/desktop/screens/library_screen.py` | `xfinaudio.library` filter/query helpers | `LibraryScreen` and table renderer | `tests/test_library_filter.py`, `tests/test_table_populators.py`, `tests/test_library_screen.py` | Keep filter predicates pure; let UI only bind query widgets and render rows. |
| Recommendation strategy selection | Choose strategy and explain intent | `src/xfinaudio/recommendation/strategies.py`, `src/xfinaudio/desktop/build_view_model.py`, `src/xfinaudio/desktop/screens/build_screen.py` | `xfinaudio.recommendation.strategies` | `BuildScreen` combo/rendering | `tests/test_playlist_strategies.py`, `tests/test_main_window.py` | Resolve UI display labels to internal strategy names in the strategy registry, not in widgets. |
| Recommendation candidate pool | Build an interactive-size pool around selected anchors | `src/xfinaudio/recommendation/candidate_pool.py`, compatibility wrapper `src/xfinaudio/desktop/recommendation_presenter.py` | `xfinaudio.recommendation.candidate_pool` | Desktop calls policy and displays guidance | `tests/test_recommendation_presenter.py`, `tests/test_anchor_preflight.py` | Completed first slice: policy is importable without desktop/Qt. |
| Recommendation scoring and optimization | Score transitions and order playlists | `src/xfinaudio/recommendation/scoring.py`, `src/xfinaudio/recommendation/optimizer.py`, `src/xfinaudio/recommendation/neighbors.py`, `src/xfinaudio/recommendation/playlist_service.py` | `xfinaudio.recommendation` | Desktop receives progress/result only | `tests/test_transition_scoring.py`, `tests/test_sequence_optimizer.py`, `tests/test_playlist_service.py`, `tests/test_neighbor_graph.py` | Keep optimizer and scoring deterministic; desktop should not assert exact internals beyond returned contract. |
| Prep Copilot | Generate safe/balanced/adventurous variants from a DJ intent | `src/xfinaudio/recommendation/prep_copilot.py`, `src/xfinaudio/desktop/prep_copilot.py`, `src/xfinaudio/desktop/screens/build_screen.py` | `xfinaudio.recommendation.prep_copilot` | Desktop converts widgets to `DJSetIntent` and renders variants | `tests/test_main_window.py`, future focused tests for `prep_copilot.py` | Normalize strategy values before engine lookup; move UI table actions away from plan generation. |
| DJ readiness and quality | Explain recommendation quality and block unsafe export | `src/xfinaudio/quality/dj_readiness.py`, `src/xfinaudio/quality/recommendation_quality.py`, `src/xfinaudio/desktop/dj_readiness_controller.py` | `xfinaudio.quality` | Desktop table/labels only | `tests/test_dj_readiness.py`, `tests/test_explainability.py`, `tests/test_review_view_model.py` | Export coordinator should consume readiness decisions, not compute/own them. |
| Review mix | Inspect ordered tracks, transitions, warnings, remove/preview tracks | `src/xfinaudio/desktop/screens/review_screen.py`, `src/xfinaudio/desktop/review_view_model.py`, `src/xfinaudio/desktop/library_controller.py` | `xfinaudio.recommendation` + `xfinaudio.quality` | `ReviewScreen` and view model | `tests/test_review_screen.py`, `tests/test_review_view_model.py`, `tests/test_main_window.py` | Move playlist edit/removal state transitions into pure helpers before UI rendering. |
| Export planning and writing | Preview/export Serato, Rekordbox, Traktor, VirtualDJ; write readiness sidecars | `src/xfinaudio/exporting/playlist_file_export.py`, `src/xfinaudio/exporting/*`, `src/xfinaudio/desktop/export_coordinator.py`, `src/xfinaudio/desktop/export_actions.py`, `src/xfinaudio/desktop/screens/export_screen.py` | `xfinaudio.exporting` + application export use case | Desktop asks for folder/confirmation and renders status | `tests/test_playlist_file_export.py`, `tests/test_export_coordinator.py`, `tests/test_playlist_exporters.py`, `tests/test_serato_playlist_export.py`, `tests/test_export_screen.py` | Non-Serato file target planning is extracted; next extract readiness/export gate decisions without moving UI copy. |
| Metadata cleanup worklists | Show incomplete metadata and export cleanup crates | `src/xfinaudio/desktop/screens/metadata_screen.py`, `src/xfinaudio/desktop/table_populators.py`, `src/xfinaudio/desktop/export_coordinator.py` | `xfinaudio.library` metadata queries + `xfinaudio.exporting` worklist plans | `MetadataScreen` | `tests/test_main_window.py`, `tests/test_table_populators.py` | Move missing-field worklist selection to pure library/export helpers. |
| Audio preview | Preview tracks from library/review without leaving app | `src/xfinaudio/desktop/audio_player.py`, `src/xfinaudio/desktop/audio_player_state.py`, `src/xfinaudio/desktop/library_controller.py` | `audio_player_state` pure state only | Qt multimedia adapter | `tests/test_audio_player.py`, `tests/test_audio_player_state.py`, `tests/test_audio_preview_errors.py` | Keep playback state pure; isolate `QMediaPlayer` behind desktop adapter. |
| Saved playlists | Save, edit, rename, delete, and re-export playlists | `src/xfinaudio/library/playlist_models.py`, `src/xfinaudio/library/playlist_repository.py`, `src/xfinaudio/desktop/playlist_coordinator.py`, `src/xfinaudio/desktop/screens/my_playlists_screen.py`, `src/xfinaudio/desktop/screens/playlist_editor.py` | `xfinaudio.library` playlist models/repository + application use case | Desktop list/editor screens | `tests/test_playlist_repository.py`, `tests/test_playlist_model.py`, `tests/test_playlist_editor.py`, `tests/test_my_playlists_screen.py` | Move save/update commands into application service; desktop should not coordinate repository details. |
| Live Assistant | Performance view with load-next suggestions, alerts, history | `src/xfinaudio/desktop/screens/live_assistant_screen.py` | Future `xfinaudio.recommendation.live_assistant` policy | `LiveAssistantScreen` only | `tests/test_live_assistant_screen.py`, `tests/test_live_assistant_state.py` | Extract alert generation and candidate ranking; remove duplicate Camelot compatibility logic from QWidget. |
| Spectral color/cohesion | Compute/read spectral profiles, display colors, influence scoring | `src/xfinaudio/audio/spectral_profile.py`, `src/xfinaudio/audio/batch_analyzer.py`, `src/xfinaudio/desktop/app_state_transitions.py`, `src/xfinaudio/desktop/spectral_completion_worker.py`, `src/xfinaudio/recommendation/scoring.py` | `xfinaudio.audio` + `xfinaudio.recommendation.scoring` + pure desktop state transitions | Desktop worker/progress and table rendering only | `tests/audio/test_spectral_profile.py`, `tests/audio/test_batch_analyzer.py`, `tests/test_app_state_transitions.py`, `tests/test_spectral_completion_worker.py` | Spectral profile AppState application is immutable; next move remaining progress-independent completion policy into a pure service. |
| Settings | Persist app preferences, export folder, optimizer settings, language | `src/xfinaudio/config/settings.py`, `src/xfinaudio/config/settings_repository.py`, `src/xfinaudio/desktop/settings_dialog.py`, `src/xfinaudio/desktop/settings_controller.py` | `xfinaudio.config` | Dialog/controller only | `tests/test_settings.py`, `tests/test_settings_repository.py`, `tests/test_settings_dialog.py`, `tests/test_settings_controller.py` | Extract settings update commands so tests do not patch modal dialogs. |
| Desktop shell | Main window, navigation, menus, shortcuts, status, theme, i18n | `src/xfinaudio/desktop/main_window.py`, `src/xfinaudio/desktop/window_factory.py`, `src/xfinaudio/desktop/layout.py`, `src/xfinaudio/desktop/menu.py`, `src/xfinaudio/desktop/navigation.py`, `src/xfinaudio/desktop/theme.py`, `src/xfinaudio/desktop/i18n.py` | None: shell should delegate | `xfinaudio.desktop` | `tests/test_main_window.py`, `tests/test_visual_integration.py`, `tests/test_navigation.py`, `tests/test_theme_dark_mode.py` | Replace dynamic method grafting and direct AppState mutation with explicit controllers/use cases over time. |

## Unit-test priority

| Priority | Module | Why first | Test target |
|---|---|---|---|
| 1 | `xfinaudio.recommendation.candidate_pool` | Pure policy already existed in desktop and caused coupling | `tests/test_recommendation_presenter.py` |
| 2 | `xfinaudio.recommendation.strategies` | Protects UI label vs internal name boundary | `tests/test_playlist_strategies.py` |
| 3 | Export decisions | Highest safety risk: readiness gates and write destinations | `tests/test_playlist_file_export.py`; future `tests/test_export_decisions.py` |
| 4 | AppState transitions | Current mutable state makes UI tests broad | `tests/test_app_state_transitions.py`; future broader transition tests |
| 5 | Live Assistant alerts | Business rules live directly in QWidget | Future `tests/test_live_assistant_policy.py` |

## Static analysis follow-up

After the first unit-test seams are stable, use static analysis to track architecture drift:

```bash
python - <<'PY'
from pathlib import Path
for path in sorted(Path('src/xfinaudio').rglob('*.py')):
    if 'desktop' not in path.parts and 'PySide6' in path.read_text(errors='ignore'):
        print(path)
PY
```

Expected result: no non-desktop module imports PySide6.

Recommended dependency checks:

- Non-desktop modules must not import `xfinaudio.desktop`.
- Desktop modules may import domain/application modules, but domain modules must not import desktop modules.
- New business rules should land in `library`, `recommendation`, `exporting`, `quality`, `config`, or `application` before UI wiring.

## Next slices

1. Continue export boundary extraction with readiness/export gate decisions; non-Serato file target planning is now in `xfinaudio.exporting.playlist_file_export`.
2. Continue AppState transition extraction: spectral profile application is immutable; next target scan-clearing/recommendation reset once UI label coupling is isolated.
3. Extract Live Assistant candidate ranking and alert policy from `screens/live_assistant_screen.py`.
4. Reduce `tests/test_main_window.py` by replacing private-widget tests with module-level unit tests plus a small UI smoke set.
