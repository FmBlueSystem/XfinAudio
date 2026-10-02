# XfinAudio 2.2.0 · Qt-free migration source candidate

2026-10-01. Status: **unreleased beta/source candidate**. This document is source-review preparation, not a tag, release, installer, deployment or promise of production stability.

## Current functionality

The sandboxed Electron interface calls the original Python engines through bounded local pipes. It includes library scan/rescan and offline filters; all eleven strategies and three variants; real read-only spectral, danceability and edge completion; generated review and saved-playlist editing; Live assistance; preferences/watch; exact metadata worklists and direct Serato export; explicitly previewed/native-confirmed loudness writing with recoverable original-byte backups; eight optional AI surfaces; and fresh-profile-only, native-selected legacy-data import with music-root reauthorization. See the [exact scope and deliberate differences](../desktop-electron/MIGRATION_SCOPE.md).

The renderer has context isolation, sandboxing and no Node access. Audio preview uses opaque authorized identities. AI remains disabled by default and preserves per-action consent, bounded requests and local authority over Apply. Source/profile scanning is read-only. Serato export is the only DJ export format in the new interface; live Serato database V2 is never written.

## Publication preparation

Python and Electron project metadata/locks now identify 2.2.0. CI explicitly exercises the supported full-manifest sharded Python aggregate with the unchanged 89% coverage floor and all Electron tests using a separate hash-locked Qt-free interpreter. Failed, cancelled, skipped or missing Node results cannot establish a green result. This wiring is tested locally; check the eventual exact GitHub commit's CI before relying on a hosted result.

The dependency inventory distinguishes legacy Qt, the new Python runtime, Electron/toolchain components, and platform-specific FFmpeg provenance. Metadata, hashes and contained native dependencies are evidence, not binary redistribution clearance. The [publication plan](../openspec/changes/electron-publication-readiness/publication-plan.md) preserves PR360 and independent watcher work through a separate draft review chain.

## Candidate identity and acceptance limits

V12 and its already-built local Mac candidate are **not rebuilt or relabeled** by this source-only follow-up. That candidate retains its prior source seal and versions. No new 2.2.0 binary is claimed; new source gates do not retroactively validate a different executable.

V12's exact-source and isolated native programmatic evidence is historical. Modified-source verification is recorded separately. Programmatic synthetic/copy-only checks do not establish human interaction, audible output, long-library stress, real AI provider reliability, or live Serato import. The earlier Linux final GUI relaunch host-tool limitation remains disclosed in its matching evidence.

The installed Qt app and real data remain untouched. Legacy import is explicit, fresh-profile-only and read-only at its source; do not treat it as a silent upgrade or merge. Spanish UI and the intentional convenience-feature differences remain documented. There is no automatic updater. Local integrity signing is not Developer ID distribution or notarization.

## Resumen en español

La migración conserva los algoritmos Python y sustituye Qt en el runtime nuevo por Electron. La versión 2.2.0 identifica este candidato de código fuente; no anuncia una publicación de binarios ni cambia el candidato V12 ya entregado. El análisis de perfiles no modifica audio. Loudness necesita vista previa y confirmación nativa; Serato conserva destino explícito, validación y backups. La IA es opcional y las pruebas usan transporte simulado, sin credenciales reales.

Licencia del código: GPL-3.0-only. La distribución pública de binarios requiere revisar los avisos, licencias, código correspondiente y configuración efectiva de sus dependencias. No legal advice or legal clearance is implied.
