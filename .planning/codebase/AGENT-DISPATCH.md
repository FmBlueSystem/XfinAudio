# Agent Dispatch — Registro de Resolución

> **Estado:** RESUELTO directamente (2026-06-06). No se despacharon agentes.
> Los concerns se validaron contra el código real y se resolvieron inline con
> verificación por tests. Este archivo reemplaza al plan de despacho original,
> que era inejecutable (referenciaba `CONCERNS.md`, `ARCHITECTURE.md`,
> `CONVENTIONS.md` y `TESTING.md`, ninguno existía) y contenía números de línea
> obsoletos y varios falsos positivos.

**Proyecto:** `/Users/freddymolina/Documents/audio`
**Baseline al iniciar:** 332 tests verdes · **Estado final:** 334 tests verdes, ruff + format limpios.

---

## Resumen de validación del plan original

| Afirmación del plan | Realidad verificada | Acción |
|---|---|---|
| `main_window.py` 1734 líneas / 82 métodos | 1803 líneas / 70 métodos | Stats corregidas |
| Falta logging en 10 módulos | El proyecto usa **excepciones tipadas** como mecanismo primario; solo se traga errores en `scan_service` y en los `except` de UI | Logging aplicado solo donde se traga el error |
| Asserts de export en líneas 1248–1252 | No existían ahí; son asserts de cancelación del scan en 1315–1319 | Consolidados en un guard |
| `except Exception` en 991/1029/1135/1170 | Reales en 378/400/1058/1095/1201/1236 | Logging agregado, catch-all preservado |
| `serato_playlist_exporter` con `except ValueError: return None` | **No existe** ningún `return None`; los `except ValueError` son control de flujo deliberado | Descartado (falso positivo) |
| Falta índice SQLite en `track_repository` | El filtrado por bpm/energy/camelot es 100% en Python; no hay `WHERE`/`ORDER BY` sobre esas columnas | Descartado (falso positivo) |
| Falta test de schema migration | Ya cubierto por 4 tests existentes en `test_track_repository.py` | Descartado (duplicado) |
| Race condition doble recommend sin test | La UI ya deshabilita el botón; un test de timing de `QThread` sería flaky | Descartado (fragilidad) |

---

## Cambios aplicados

### 1. Upper bounds de dependencias — `pyproject.toml`
`mutagen>=1.47,<2.0`, `pydantic>=2.0,<3.0`, `PySide6>=6.0,<7.0`. `uv lock` actualizado.
Protege contra major bumps que rompan sin aviso.

### 2. Error handling + logging — `src/xfinaudio/desktop/main_window.py`
- `LOGGER = logging.getLogger(__name__)`.
- `LOGGER.exception(...)` en los `except` de los workers y de los 4 handlers de export
  Serato. **Se mantiene el catch-all**: en un boundary de UI/thread, capturar todo es
  correcto (un error inesperado no debe matar el worker thread ni crashear la UI); lo que
  faltaba era dejar rastro del traceback.
- 3 `assert` de invariante de scan consolidados en un guard `RuntimeError` explícito que
  sobrevive a `python -O`.

### 3. Type safety pre-existente — `src/xfinaudio/desktop/main_window.py`
- `__lt__` heterogéneo: `# type: ignore[operator]` (el `TypeError` ya está manejado en runtime).
- `selected_status`: `cast(MetadataStatus, ...)` tras el guard (Pyright no estrecha `str` a Literal con `not in`).

### 4. Test de integración real — `tests/test_integration_scan_recommend_export.py`
Ejercita el wiring real `scan_folder → TrackRepository → PlaylistWorkflowService.recommend →
write_serato_crate → parse`. Solo se stubean los seams legítimos del scanner
(descubrimiento de paths y lectura de tags). Cubre el GAP 1 real: exclusión de metadata
incompleta de la recomendación end-to-end.

### 5. Extracción de workers — `src/xfinaudio/desktop/_workers.py`
`BackgroundWorker` y `ScanWorker` (antes `_BackgroundWorker`/`_ScanWorker`, internas de
`main_window`) movidas a su propio módulo. Refactor conservador del god-object: separa la
responsabilidad de threading sin tocar el estado mutable de la ventana.

> Nota: tras crear `_workers.py`, Pyright puede reportar `reportMissingImports` por caché
> stale del language server. Es falso positivo — el módulo importa en runtime y los tests
> pasan. Se limpia al reiniciar el servidor LSP.

---

## Pendiente para una sesión dedicada

El refactor completo del god-object (`main_window.py` sigue en ~1750 líneas) — extraer el
estado mutable a un modelo y reubicar lógica — quedó fuera de alcance por riesgo: Qt corre
offscreen en tests y no hay QA manual de UI posible. Hacerlo requiere una sesión con
validación interactiva de la app.

---

## Verificación final

```bash
cd /Users/freddymolina/Documents/audio
uv sync --locked
uv run pytest -q           # 334 passed
uv run ruff check .        # All checks passed
uv run ruff format --check .
```
