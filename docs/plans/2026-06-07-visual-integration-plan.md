# Plan de Integración Visual — XfinAudio
**Date:** 2026-06-07
**Branch:** feature/visual-integration

---

## Estrategia conservadora

Los tests de `test_main_window.py` acceden a `window.scanned_records`, `window.last_recommendation`, etc. directamente — son la fuente de verdad en los tests. **NO se puede cambiar esto sin reescribir 553 tests.**

Por lo tanto:
- `self.X` permanece como fuente de verdad en MainWindow
- `_sync_state()` mantiene `self._state` sincronizado
- Las screens reciben `render(vm, state)` llamado desde `_sync_state()`
- Las tabs del QTabWidget se reemplazan usando las screen objects directamente

---

## Orden de reemplazo de tabs

| Orden | Tab | Screen | Justificación |
|---|---|---|---|
| 1 | Infraestructura render | — | `_sync_state()` llama `render()` en screens; add_missing_sync_state calls |
| 2 | Library (tab 0) | LibraryScreen | Punto de entrada; menor riesgo de romper tests |
| 3 | Build (tab 1) | BuildScreen | Depende de Library para tracks |
| 4 | Review (tab 2) | ReviewScreen | Semáforo de readiness — core del nuevo UX |
| 5 | Export (tab 3) | ExportScreen | Último paso del flujo; más coupling con ExportCoordinator |
| 6 | Metadata (tab 4) | MetadataScreen | Flujo paralelo; menor criticidad |

---

## Signals a conectar por screen

### LibraryScreen
| Signal | Handler en MainWindow |
|---|---|
| `folder_change_requested` | `choose_folder()` |
| `scan_requested` | `scan_selected_folder()` |
| `cancel_scan_requested` | `cancel_scan()` |
| `selection_changed(list[str])` | nuevo handler `_on_library_selection_changed(paths)` |
| `metadata_screen_requested` | nuevo handler → `workflow_tabs.setCurrentIndex(4)` |

### BuildScreen
| Signal | Handler |
|---|---|
| `recommend_requested(str, list)` | nuevo wrapper `_on_recommend_requested(strategy, paths)` → adapta a `recommend_playlist()` |
| `copilot_generate_requested` | `generate_prep_copilot()` |
| `copilot_variant_applied(int)` | nuevo wrapper `_on_copilot_variant_applied(idx)` → adapta a `apply_selected_prep_copilot_variant()` |
| `back_requested` | nuevo handler → `workflow_tabs.setCurrentIndex(0)` |

### ReviewScreen
| Signal | Handler |
|---|---|
| `back_requested` | nuevo handler → `workflow_tabs.setCurrentIndex(1)` |
| `proceed_to_export_requested` | nuevo handler → `workflow_tabs.setCurrentIndex(3)` si `can_export` |

### ExportScreen
| Signal | Handler |
|---|---|
| `preview_requested` | `preview_serato_export()` |
| `export_requested` | `export_recommendation_to_serato()` |
| `readiness_export_requested` | `export_dj_readiness_report()` |
| `safe_folder_change_requested` | `choose_safe_export_folder()` |
| `back_requested` | nuevo handler → `workflow_tabs.setCurrentIndex(2)` |

### MetadataScreen
| Signal | Handler |
|---|---|
| `back_requested` | nuevo handler → `workflow_tabs.setCurrentIndex(0)` |

---

## Mismatches de signals identificados

### recommend_requested
- **Screen emite:** `Signal(str, list)` → `(strategy_name, selected_paths)`
- **MainWindow espera:** `recommend_playlist()` sin args (lee de widgets)
- **Fix:** Nuevo wrapper `_on_recommend_requested(strategy_name, paths)` que extrae los datos del signal y llama `recommend_playlist()` adaptado.

### copilot_variant_applied
- **Screen emite:** `Signal(int)` → índice de fila seleccionada
- **MainWindow espera:** `apply_selected_prep_copilot_variant()` que lee de `prep_copilot_table`
- **Fix:** Nuevo wrapper `_on_copilot_variant_applied(index)` que selecciona la fila en `prep_copilot_table` y llama al método existente.

---

## Cómo se reemplaza una tab

En `_build_layout()`, cada tab se arma así:
```python
library_page = QWidget()
layout = QVBoxLayout(library_page)
layout.addWidget(self.tracks_table)
# ...
self.workflow_tabs.addTab(library_page, "Library")
```

**Estrategia de reemplazo**: Cambiar el QWidget anónimo por la screen instanciada:
```python
self.workflow_tabs.addTab(self._library_screen, "Library")
```
Eliminar el QWidget anónimo y su layout. Los widgets que estaban dentro del tab anónimo (tracks_table, folder_button, etc.) se reemplazarán por los widgets equivalentes de la screen.

**Para los tests**: Los tests que acceden a `window.tracks_table` seguirán funcionando si la screen expone el mismo atributo en el mismo lugar.

---

## Render loop

Después de Task 1, `_sync_state()` llamará:
```python
def _sync_state(self) -> None:
    self._state = AppState(...)  # ya existente
    self._render_screens()       # nuevo

def _render_screens(self) -> None:
    self._library_screen.render(self._library_vm, self._state)
    self._build_screen.render(self._build_vm, self._state)
    self._review_screen.render(self._review_vm, self._state)
    self._export_screen.render(self._export_vm, self._state)
    self._metadata_screen.render(self._state)
```

Esto garantiza que las screens siempre reflejan el estado actual.

---

## Handlers sin _sync_state() (a corregir en Task 1)

- `restore_persisted_tracks()` — agrega `_sync_state()` al final
- `_clear_scan_dependent_state()` — agrega `_sync_state()` al final
- `_begin_scan_state()` — agrega `_sync_state()` al final
- `_end_scan_state()` — agrega `_sync_state()` al final
- `_begin_recommendation_state()` — agrega `_sync_state()` al final
- `_end_recommendation_state()` — agrega `_sync_state()` al final
- `generate_prep_copilot()` — agrega `_sync_state()` al final
- `set_safe_export_folder()` — agrega `_sync_state()` al final

---

## Variables de instancia a eliminar (FASE FINAL — tras integración completa)

Solo cuando AppState sea inequívocamente la fuente de verdad y los tests lo reflejen:
- `self.selected_folder` → `self._state.selected_folder`
- `self.scanned_records` → `self._state.scanned_records`
- `self._records_by_path` → `self._state.records_by_path`
- `self.last_recommendation` → `self._state.last_recommendation`
- `self.last_playlist_explanation` → `self._state.last_playlist_explanation`
- `self.last_quality_report` → `self._state.last_quality_report`
- `self.last_dj_readiness_report` → `self._state.last_dj_readiness_report`
- `self.last_prep_copilot_plan` → `self._state.last_prep_copilot_plan`
- `self.applied_prep_copilot_variant_name` → `self._state.applied_variant_name`
- `self.serato_export_history` → `self._state.serato_export_history`

**NOTA:** No eliminar hasta que los tests sean actualizados para usar `window._state.X`. Esta sesión NO elimina variables — es deuda para la siguiente.

---

## Criterio de done por tab

Una tab está "conectada" cuando:
1. La screen aparece en el QTabWidget (reemplaza el QWidget anónimo)
2. Los signals están conectados a handlers
3. `render()` se llama en `_sync_state()` y la screen muestra datos reales
4. Los tests existentes siguen en verde
5. Al menos 1 nuevo test verifica que la screen renderiza desde el ViewModel

---

## Riesgo principal

**Los tests de MainWindow acceden a widgets por nombre directo** (`window.tracks_table`, `window.strategy_combo`, etc.). Si la screen nueva no expone los mismos atributos con los mismos nombres, los tests rompen.

**Mitigación:** Al reemplazar un tab, mantener el atributo de widget en `self.X` como alias al widget de la screen. Por ejemplo:
```python
# En _build_widgets, DESPUÉS de que la screen ya esté conectada:
self.tracks_table = self._library_screen.tracks_table
```
Esto garantiza backward compatibility con los tests sin reescribirlos.
