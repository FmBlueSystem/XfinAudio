# XfinAudio 2.3.0 · AI-guided playlist improvement source candidate

2026-10-07. Status: **unreleased beta/source candidate**. This document is source-review preparation, not a tag, release, installer, deployment or promise of production stability.

## What changed since 2.2.0

**AI-guided playlist improvement.** From a saved playlist's editor, a user types a natural-language instruction and reviews concrete track/order proposals before anything changes: a local prepare step discloses the exact recipient, candidate counts and fields; `ai.payload` exposes the exact request body read-only (no credential, no network) before consent; consent is per-request and confirmed again in the native system dialog; the provider response is validated locally into a before/after diff with engine assessment (readiness, transition score, move markers); applying changes only the draft; saving uses the dedicated proposal-bound route, separate from apply. Provider tests use fake transport; AI remains off by default.

**Legacy Qt package removed.** `xfinaudio.desktop` (91 files), its test suite, the `PySide6` and `pyobjc-framework-Cocoa` dependencies, the Qt console script, the PyInstaller/`build_dmg.sh` lane and the CI packaging input are gone. The Electron shell plus the frozen headless core (`packaging/macos`) is the only runtime; Serato remains the only DJ export format and CSV/JSON report exports stay out of scope by decision. Historical workflows in the docs remain for reference only.

**Review copy is Spanish throughout.** Readiness labels/details/summary, playlist warnings (BPM drops, spectral shifts), scoring warnings and the assessment description were localized; the prep-copilot filter follows the new markers.

**Interaction fixes from field testing.** Phase-aware waiting copy with elapsed seconds during provider calls; visible reasons for disabled prepare/CTA controls; `#prev → #now` move markers and moved counts in improvement diffs; refreshed status banners that state what happened and what to do next; disabled primary buttons styled consistently; a reason-specific hint for the Live guide gate; read-only core queries answer while an AI request holds the host.

**Verification tooling.** `scripts/preview-harness.sh` runs `smoke` (build + full Node suite + focused headless tests + ruff) and `launch` (throwaway profile, metadata-only seed, watch disabled, printed UX checklist).

## Publication preparation

Python and Electron project metadata/locks identify 2.3.0. On this source commit: `release_gate_check.py --run` exited 0 with 2,780 Python tests at 91.81% coverage (89% floor), Pyright/Ruff/format/smoke/docs/hygiene/package green; the Electron suite passed 515/515 with the separate hash-locked interpreter. This wiring is verified locally; check the eventual exact GitHub commit's CI before relying on a hosted result.

## Candidate identity and acceptance limits

V12 and its already-built local Mac candidate are **not rebuilt or relabeled** by this source-only follow-up. That candidate retains its prior source seal and versions. No new 2.3.0 binary is claimed; new source gates do not retroactively validate a different executable.

Field acceptance covers the complete AI improvement flow in an isolated profile (one consented provider request, proposal applied and saved in the disposable database) plus a live walkthrough of Biblioteca, Crear lista, Revisar, Exportación Serato, Listas, Editor, Live and Ajustes. Not exercised: loudness analysis runs (their only write path targets the real library), audio playback, the native folder chooser and Live with a ready selection. Tests do not establish human interaction, audible output, long-library stress, real AI provider reliability or live Serato import.

Legacy import remains explicit, fresh-profile-only and read-only at its source. Spanish UI and intentional convenience-feature differences remain documented. There is no automatic updater. Local integrity signing is not Developer ID distribution or notarization.

## Resumen en español

La versión 2.3.0 añade la mejora guiada de playlists con IA (instrucción → divulgación → payload exacto inspeccionable → consentimiento por solicitud y confirmación nativa → propuesta con diff antes/después → aplicar al borrador → guardado dedicado) y elimina el paquete Qt legacy con sus dependencias. Toda la copia de revisión está en español y las fricciones detectadas en prueba de campo quedan corregidas (espera con fase y tiempo, motivos de controles deshabilitados, marcadores de movimiento, banners claros). Las pruebas usan transporte simulado; la IA sigue desactivada por defecto. El análisis de perfiles no modifica audio; loudness conserva vista previa y confirmación nativa; Serato es el único formato DJ y la base V2 nunca se escribe.

Licencia del código: GPL-3.0-only. La distribución pública de binarios requiere revisar los avisos, licencias, código correspondiente y configuración efectiva de sus dependencias. No legal advice or legal clearance is implied.
