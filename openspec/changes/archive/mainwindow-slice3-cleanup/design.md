# Design: MainWindow Slice 3 Cleanup

## Technical Approach

Behavior-preserving extraction. Move menu + about into `MenuBuilder`, settings handling into `SettingsController`, both taking `host` (the `MainWindow`). `MainWindow` keeps thin delegates so existing tests/signals stay intact. Formalize the `ExportCoordinator` host boundary with an `ExportHost` Protocol (inline, replacing the `TYPE_CHECKING` `MainWindow` import). Apply 7 minimal ruff fixes. Mirrors the existing `ExportCoordinator(host=self)` slice-1 pattern (`main_window.py:315`).

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|----------|--------|----------|-----------|
| Host passing | Constructor `host` handle | Pass widgets/signals explicitly | Matches `ExportCoordinator` slice-1; minimal churn |
| About dialog home | Move into `MenuBuilder` | Keep in `MainWindow` | Menu owns both about actions (`:210,:229`); cohesive |
| Protocol location | Inline in `export_coordinator.py` | New `protocols.py` | Single consumer; avoids premature shared module |
| Settings dialog import | Keep lazy import inside method | Module-level | Preserves current lazy-load (`:1032`), avoids import cost/cycles |
| Delegation | `MainWindow` keeps public method names | Rewire callers | Tests + signal connections (`:696`, `:1035`) unchanged |

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `desktop/menu_builder.py` | Create | `MenuBuilder` — menu bar + About dialog |
| `desktop/settings_controller.py` | Create | `SettingsController` — open + apply settings |
| `desktop/main_window.py` | Modify | Delegate menu/settings; remove moved bodies |
| `desktop/export_coordinator.py` | Modify | Add `ExportHost` Protocol; drop `MainWindow` import |
| `desktop/i18n.py` | Modify | Remove `locale` (F401) |
| `desktop/screens/build_screen.py` | Modify | E501 `:193` |
| `desktop/screens/review_screen.py` | Modify | E501 `:45`, F841 `:175`, B905 `:246` |
| `desktop/table_populators.py` | Modify | E501 `:162`, `:164` |
| `library/track_repository.py` | Modify | SIM105 `:128-131` |

## Item 1 — MenuBuilder

**Move:** `_build_menu` (`main_window.py:204-230`), `_show_about_dialog` (`:232-265`).
**Interface:**
```python
class MenuBuilder:
    def __init__(self, host: "MainWindow") -> None: ...
    def build(self, menu_bar: QMenuBar) -> None: ...   # builds XfinAudio + Help menus
    def show_about_dialog(self) -> None: ...
```
**Host attrs needed:** `tr()`, used as `QAction(parent=host)`, `host.close` (Quit), `host._open_settings_dialog` (Settings action target). About action targets `self.show_about_dialog`.
**MainWindow change:** `:154` becomes `self._menu_builder = MenuBuilder(self); self._menu_builder.build(self.menuBar())`. Keep `_show_about_dialog` as `def _show_about_dialog(self): self._menu_builder.show_about_dialog()` (if any external ref) — otherwise drop.

## Item 2 — SettingsController

**Move:** `_open_settings_dialog` (`main_window.py:1030-1036`), `_apply_settings` (`:1038-1051`).
**Interface:**
```python
class SettingsController:
    def __init__(self, host: "MainWindow") -> None: ...
    def open_dialog(self) -> None: ...                 # was _open_settings_dialog
    def apply(self, new_settings: AppSettings) -> None: # was _apply_settings
```
**Host attrs needed:** `settings` (get/set), `settings_repository`, `safe_export_folder_label.setText`, `_format_safe_export_folder_label()`, `_sync_state()`, `tr()`, used as dialog `parent=host`. `SettingsDialog` stays lazy-imported inside `open_dialog`.
**MainWindow change:** keep delegates `_open_settings_dialog` → `self._settings_controller.open_dialog()` and `_apply_settings` → `self._settings_controller.apply(...)` because `library_screen.settings_requested` (`:696`) and `dialog.settings_changed` (`:1035`) connect to these names.

## Item 3 — ExportHost Protocol

Every `self._host.X` in `export_coordinator.py`:

**Attributes (read):** `last_recommendation`, `last_dj_readiness_report`, `last_quality_report`, `settings`, `applied_prep_copilot_variant_name`, `status_label`, `export_guidance_label`, `_export_screen`, `serato_export_history`, `serato_export_history_table`.
**Attribute (write):** `serato_export_history`.
**Methods:** `tr(str) -> str`, `_sync_state()`, `_show_dj_readiness(...)`, `_selected_missing_metadata_filter()`, `_selected_metadata_status_filter()`, `_metadata_status_records(status)`, `_metadata_missing_field_records(field)`.

**Definition (inline, replace `:38-39` TYPE_CHECKING block):**
```python
from typing import Protocol
class ExportHost(Protocol):
    last_recommendation: PlaylistRecommendation | None
    last_dj_readiness_report: DjReadinessReport | None
    last_quality_report: Any | None
    settings: Any                       # AppSettings
    applied_prep_copilot_variant_name: str | None
    status_label: Any                   # QLabel
    export_guidance_label: Any          # QLabel
    serato_export_history: list[dict]
    serato_export_history_table: Any    # QTableWidget
    _export_screen: Any
    def tr(self, text: str) -> str: ...
    def _sync_state(self) -> None: ...
    def _show_dj_readiness(self, recommendation, quality_report, *, serato_plan, serato_volume_root) -> None: ...
    def _selected_missing_metadata_filter(self) -> str | None: ...
    def _selected_metadata_status_filter(self) -> str | None: ...
    def _metadata_status_records(self, status: str) -> list[Any]: ...
    def _metadata_missing_field_records(self, field: str) -> list[Any]: ...
```
`__init__` signature becomes `def __init__(self, host: ExportHost) -> None`. Note `_export_screen.software_selector.currentText()` (`:138`) — type `_export_screen` as `Any` to avoid leaking the screen type.

## Item 4 — Lint fixes

| File:line | Error | Fix |
|-----------|-------|-----|
| `i18n.py:12` | F401 | Delete `import locale` |
| `build_screen.py:193` | E501 | Split ternary: assign `text = self.tr("Anchor: {0}").format(anchor) if anchor else self.tr("Select a track in the Library to set the anchor.")` then `self.anchor_label.setText(text)` |
| `review_screen.py:45` | E501 | Wrap the `3:` tooltip string across two adjacent string literals (implicit concat) under 120 cols |
| `review_screen.py:175` | F841 | Remove `header = table.horizontalHeader()` (unused) |
| `review_screen.py:246` | B905 | `enumerate(zip(values, tooltips, strict=True))` |
| `table_populators.py:162` | E501 | Break `tips.append(...translate(...))` onto multiple lines |
| `table_populators.py:164` | E501 | Same multi-line break |
| `track_repository.py:128-131` | SIM105 | Replace try/except-pass with `with contextlib.suppress(sqlite3.OperationalError): connection.execute("ALTER TABLE tracks ADD COLUMN duration REAL")`; add `import contextlib` |

## Testing Strategy

| Layer | What | How |
|-------|------|-----|
| Unit | `ExportHost` decouples coordinator | New test uses a fake host satisfying Protocol; assert export flows w/o `MainWindow` |
| Integration | Menu/settings delegation | Existing `MainWindow` tests run unmodified; verify menu actions + `settings_changed` signal |
| Static | Lint clean | `uv run ruff check .`, `ruff format --check .` |
| Regression | Full suite | `uv run pytest -q` zero failures |

## Migration / Rollout

No migration required. Each item is an isolated commit; `git revert` restores prior behavior.

## Open Questions

- [ ] Does any test reference `_show_about_dialog` directly? If yes, keep the thin delegate; if not, remove it entirely from `MainWindow`.
