# XfinAudio — Architecture & Agent Conduct

> Living document for AI agents working on this codebase.  
> Last updated: 2026-06-07

---

## 1. What this project is

**XfinAudio** is a metadata-driven DJ playlist assistant for macOS.  
It scans audio files (FLAC, MP3, AIFF, etc.), extracts BPM / Camelot key / energy / genre / tags (via Mixed In Key or mutagen), and recommends harmonic DJ playlists using a weighted transition scorer.

The primary UI is a **PySide6 desktop app** (`src/xfinaudio/desktop/`).  
The core engine is pure Python (`src/xfinaudio/recommendation/`, `src/xfinaudio/library/`, `src/xfinaudio/quality/`).

---

## 2. Directory structure

```
src/xfinaudio/
├── desktop/           # PySide6 UI — screens, ViewModels, main window
│   ├── screens/       # QWidget screens (Library, Build, Review, Export, Metadata)
│   ├── app_state.py   # Immutable AppState (model_copy, no mutation)
│   ├── *_view_model.py # Pure Python ViewModels (no Qt imports)
│   ├── main_window.py # God-object ~1600L — touch with care
│   └── theme.py       # Stylesheet constants & column widths
├── recommendation/    # Playlist scoring & generation
│   ├── camelot.py     # Camelot wheel parsing & harmonic scoring
│   ├── scoring.py     # TransitionScore = weighted(Key, BPM, Energy, Tags)
│   ├── strategies.py  # Strategy profiles (harmonic_journey, warmup, build, ...)
│   ├── playlist_service.py # recommend_playlist() — the solver
│   ├── prep_copilot.py     # safe / balanced / adventurous variants
│   └── optimizer.py   # Sequence optimizer (greedy / etc.)
├── library/           # Data layer
│   ├── models.py      # TrackRecord, MetadataStatus (Pydantic v2)
│   ├── scan_service.py # MetadataScanService — background scanning
│   └── track_repository.py # SQLite persistence
├── quality/           # Validation & readiness
│   ├── dj_readiness.py      # Ready / Needs Review / Blocked gates
│   └── recommendation_quality.py # Average score, transition metrics
├── exporting/         # Output formats
│   ├── serato_crate.py      # Serato crate writer
│   ├── serato_playlist_exporter.py
│   └── explainability.py    # PlaylistExplanation (transitions, scores)
├── application/       # Orchestration
│   └── playlist_workflow.py # Scan + Recommend + Export workflow
└── config/            # Settings persistence (Pydantic, JSON)

tests/                 # pytest suite — 500+ tests
├── test_*.py          # Unit & integration tests
├── conftest.py        # Shared fixtures (qapp, fake services)
└── fixtures/          # Audio fixtures for scanning tests

docs/                  # Markdown docs (release gates, plans, specs)
packaging/             # PyInstaller config
scripts/               # CI / release gate scripts
```

---

## 3. Architectural patterns

### 3.1 Screen → ViewModel → AppState

Each screen is a **thin QWidget** that renders data from a **pure-Python ViewModel**.

```
LibraryScreen  ←  LibraryViewModel.tracks_for_display(state)
BuildScreen    ←  BuildViewModel.available_strategies()
ReviewScreen   ←  ReviewViewModel.readiness_status(state)
```

- **Screens** emit `Signal`s (`scan_requested`, `selection_changed`, etc.).
- **MainWindow** connects signals to handlers. Screens do **not** call business logic directly.
- **AppState** is immutable. Every mutation returns a new instance via `model_copy(update=...)`.

### 3.2 The god-object boundary

`main_window.py` (~1600 lines) is the **single mutable coordination point**. It owns:
- Qt widget wiring
- Background thread launching (`ScanController`, `RecommendationController`)
- State transitions (`_sync_state()` triggers `_render_screens()`)
- File dialogs & persistence

**Rule:** Do not extract logic from `main_window.py` unless:
1. The extraction has unit tests.
2. You can verify the UI manually (Qt runs offscreen in CI).
3. The change is mechanical (e.g., moving a method to a new module) and does not alter behavior.

### 3.3 Scoring pipeline

```
TrackRecord A ──┐
                ├──→ score_transition(A, B) → TransitionScore
TrackRecord B ──┘

TransitionScore.total_score = weighted_average(
    harmonic = score_camelot_transition(A.key, B.key)  # 60%
    bpm      = _score_bpm(A.bpm, B.bpm)                # 20%
    energy   = _score_energy(A.energy, B.energy)       # 15%
    tags     = _score_tags(A.tags|genre, B.tags|genre) #  5%
)
```

**Key rules:**
- Camelot diagonal moves (e.g. 8A → 9B) score **0.9** (fuzzy keymixing).
- BPM difference > **3%** between adjacent tracks is a **hard block** for DJ readiness.
- Energy difference > **3 levels** scores 0.

### 3.4 Table population

Tables are populated via `table_populators.py` with an injected `item_factory`.  
This allows tests to inject `SortAwareTestItem` while production uses `_SortAwareTableItem`.

---

## 4. Code rules

### 4.1 Python

- **3.11+** — use `|` unions, `StrEnum`, `dataclass(frozen=True)`.
- **Type hints** on public functions and methods.
- **No bare `except:`** — always catch specific exceptions.
- **Logging**, not `print` — use `logging.getLogger(__name__)`.
- **Pydantic v2** — `model_copy(update=...)` for immutability, never mutate in place.

### 4.2 Qt / PySide6

- **Screens** never import business logic. They import `AppState` and `*ViewModel` only.
- **No blocking I/O on the main thread** — use `QThread` + worker pattern (`_workers.py`).
- **Always `blockSignals(True)`** when repopulating tables programmatically.
- **Tooltips on every truncated cell** — `item.setToolTip(value)`.
- **Hide vertical headers** on data tables — `table.verticalHeader().setVisible(False)`.

### 4.3 Testing

- **pytest** — run with `python -m pytest tests/`.
- **Minimum bar:** all tests pass, ruff clean, format clean.
- **UI tests** use `qapp` fixture (from `pytest-qt` or custom `conftest.py`).
- **Table populators** are tested with injected `item_factory` — always maintain this seam.

---

## 5. What NOT to do

| ❌ Don't | Why |
|---|---|
| Refactor `main_window.py` for aesthetic reasons | ~1600L god-object, UI tests run offscreen, high regression risk |
| Change scoring thresholds without updating tests | BPM 3%, Camelot scores, energy thresholds are contractual |
| Add new dependencies without pinning | Use `>=lower,<upper` in `pyproject.toml`, run `uv lock` |
| Mutate `AppState` in place | Always `state = state.model_copy(update={...})` |
| Use `table.sortItems()` on the library table | Use ViewModel-level sorting + repopulation to preserve numeric sort |
| Ignore `DjReadinessReport` gates | `blocked` → export disabled; `needs_review` → export allowed with warning |
| Add columns to tables without checking `theme.py` | `_TRACK_TABLE_COLUMN_WIDTHS` and friends must stay in sync |

---

## 6. Agent checklist before finishing

```
□ pytest passes  (python -m pytest tests/)
□ ruff check .   passes
□ ruff format --check . passes
□ No new bare except:
□ No new dependencies without bounds
□ If UI changed: manual QA screenshot or description in commit
□ If table columns changed: theme.py widths updated
□ If scoring changed: test_camelot_scoring.py & test_main_window.py updated
```

---

## 7. Key files for context

| File | Purpose |
|---|---|
| `pyproject.toml` | Project config, deps, tool settings |
| `src/xfinaudio/desktop/app_state.py` | Immutable state shape |
| `src/xfinaudio/recommendation/camelot.py` | Harmonic scoring rules |
| `src/xfinaudio/recommendation/scoring.py` | Transition score formula |
| `src/xfinaudio/quality/dj_readiness.py` | Readiness gates |
| `src/xfinaudio/desktop/theme.py` | Visual constants |
| `tests/conftest.py` | Test fixtures |

---

## 8. Related documents

- `AGENTS.md` (project root) — Skill quality standards (GGA rules)
- `.planning/codebase/AGENT-DISPATCH.md` — Historical dispatch log (resolved, read-only)
- `HARMONIC_MIXING.md` — Public-facing harmonic mixing guide
- `CONTRIBUTING.md` — Human contributor guide
