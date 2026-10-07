#!/usr/bin/env bash
# Fast isolated UX-test harness for the XfinAudio Electron preview.
#
# Goals:
#   - smoke: one command that proves build + tests are green BEFORE a manual
#     user session, so testers never burn time on a broken tree.
#   - launch: start the app in a throwaway data directory (fresh or reused),
#     optionally seeded with metadata-only library cache, so a session starts
#     at the flow under test instead of redoing setup.
#
# Safety: never touches the installed app, the main checkout, real library
# data, audio files or Serato databases. Seeds copy tracks.db/roots.json
# (metadata cache only — no audio). No provider credentials are read.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/desktop-electron"
PY="$ROOT/.venv/bin/python"

find_electron() {
  if [ -n "${ELECTRON_BIN:-}" ]; then printf '%s' "$ELECTRON_BIN"; return 0; fi
  local candidates=(
    "$APP/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"
    "$ROOT/../combined-app-preview/desktop-electron/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron"
  )
  local c
  for c in "${candidates[@]}"; do
    if [ -x "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  return 1
}

require() {
  [ -x "$PY" ] || { echo "missing $PY (run: uv sync)" >&2; exit 1; }
  [ -d "$APP" ] || { echo "missing $APP" >&2; exit 1; }
}

smoke() {
  require
  echo "== smoke 1/3: electron build + node tests"
  (cd "$APP" && XFIN_PYTHON="$PY" npm run build >/dev/null && XFIN_PYTHON="$PY" node --test tests/*.test.mjs | tail -5)
  echo "== smoke 2/3: focused headless core tests"
  (cd "$ROOT" && UV_OFFLINE=1 uv run pytest tests/test_headless_optional_ai.py tests/test_headless_protocol.py -q | tail -2)
  echo "== smoke 3/3: python type+lint on touched core"
  (cd "$ROOT" && UV_OFFLINE=1 uv run ruff check src/xfinaudio/headless >/dev/null && echo "ruff: ok")
  echo "SMOKE PASS — tree is green for a user session."
}

init_settings() {
  # Watch stays off for harness profiles: a seeded root must never trigger a
  # background scan during a timed UX session. Defaults come from AppSettings.
  local data="$1"
  [ -f "$data/settings.json" ] && return 0
  "$PY" - "$data" "$ROOT" <<'PY'
import sys, pathlib
sys.path.insert(0, pathlib.Path(sys.argv[2]) / "src")
from xfinaudio.config.settings import AppSettings, LibrarySettings
data = pathlib.Path(sys.argv[1])
data.mkdir(parents=True, exist_ok=True)
(data / "settings.json").write_text(
    AppSettings(library=LibrarySettings(watch_for_changes=False)).model_dump_json(indent=2) + "\n"
)
PY
}

launch() {
  require
  local electron
  electron="$(find_electron)" || { echo "Electron not found; set ELECTRON_BIN=<path>" >&2; exit 1; }
  local mode="fresh" seed="" dir=""
  while [ $# -gt 0 ]; do
    case "$1" in
      --reuse) mode="reuse"; dir="${2:?--reuse needs a directory}"; shift 2 ;;
      --seed-from) seed="${2:?--seed-from needs a directory}"; shift 2 ;;
      *) echo "unknown option: $1" >&2; exit 1 ;;
    esac
  done
  if [ "$mode" = "fresh" ]; then
    dir="$(mktemp -d "${TMPDIR:-/tmp}/xfinaudio-ux.XXXXXX")"
    chmod 700 "$dir"
  else
    [ -d "$dir" ] || { echo "no such directory: $dir" >&2; exit 1; }
  fi
  if [ -n "$seed" ]; then
    [ -f "$seed/tracks.db" ] && cp "$seed/tracks.db" "$dir/tracks.db"
    [ -f "$seed/roots.json" ] && cp "$seed/roots.json" "$dir/roots.json"
    echo "seed: metadata cache copied (no audio, no playlists)"
  fi
  init_settings "$dir"
  echo "data dir: $dir"
  echo "PID: $$"
  cat <<'CHECKLIST'

Manual UX checklist (report: step + screen + exact error text + screenshot):
  1. Biblioteca  — carga, filtros, contador de pistas, sin errores silenciosos.
  2. Crear lista — estrategia + variante, genera revisión con puntuación.
  3. Revisar     — antes/después, detalle, comparar, reordenar, guardar.
  4. Listas      — editar/rerenombrar/duplicar/restaurar.
  5. Editor      — mover/quitar/escuchar; Guardar y Descartar cambian estado.
  6. IA (si aplica) — preparar → payload exacto → consentir → respuesta → aplicar → guardar.
  7. Loudness/Ajustes — progreso visible, estado al terminar, sin copy obsoleto.
CHECKLIST
  exec /usr/bin/env -i PATH=/opt/homebrew/bin:/usr/bin:/bin HOME="$dir" \
    XFIN_DATA_DIR="$dir" XFIN_PYTHON="$PY" "$electron" "$APP"
}

case "${1:-all}" in
  smoke) shift; smoke "$@" ;;
  launch) shift; launch "$@" ;;
  all) shift; smoke; launch "$@" ;;
  *) echo "usage: $0 [smoke | launch [--reuse DIR] [--seed-from DIR] | all]" >&2; exit 1 ;;
esac
