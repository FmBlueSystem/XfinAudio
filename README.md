# XfinAudio — Metadata-Driven DJ Playlist Intelligence

XfinAudio is a GPL-3.0-only desktop DJ playlist assistant for DJs who already organize tracks in tools like Mixed In Key and Serato DJ Pro, but need a faster, safer, explainable way to turn a large metadata-rich library into playable playlist candidates.

It is not a mixer, not an audio analyzer, and not a replacement for DJ judgment. It is a local desktop decision-support tool: it reads metadata, persists a searchable library, recommends musically coherent track sequences, explains every transition, and exports safe Serato crate worklists that help the DJ prepare, validate, and improve the library.

Developed by **Freddy Molina** at **[BlueSystem.io](https://bluesystem.io)** — Audio Division.

---

## Table of contents

- [English](#english)
  - [The pain XfinAudio solves](#the-pain-xfinaudio-solves)
  - [What XfinAudio does](#what-xfinaudio-does)
  - [Core DJ workflow](#core-dj-workflow)
  - [Technical techniques used](#technical-techniques-used)
  - [Application features](#application-features)
  - [Recommendation strategies](#recommendation-strategies)
  - [DJ software export model](#dj-software-export-model)
  - [Safety posture and non-goals](#safety-posture-and-non-goals)
  - [Install](#install)
  - [Quick start for development](#quick-start-for-development)
  - [Release gates](#release-gates)
  - [License and dependency caveats](#license-and-dependency-caveats)
- [Español](#español)
  - [El dolor que XfinAudio viene a resolver](#el-dolor-que-xfinaudio-viene-a-resolver)
  - [Qué hace XfinAudio](#qué-hace-xfinaudio)
  - [Flujo DJ principal](#flujo-dj-principal)
  - [Técnicas usadas](#técnicas-usadas)
  - [Características de la app](#características-de-la-app)
  - [Estrategias de recomendación](#estrategias-de-recomendación)
  - [Modelo de exportación a software DJ](#modelo-de-exportación-a-software-dj)
  - [Postura de seguridad y no-objetivos](#postura-de-seguridad-y-no-objetivos)
  - [Instalación](#instalación)
  - [Inicio rápido para desarrollo](#inicio-rápido-para-desarrollo)
  - [Compuertas de release](#compuertas-de-release)
  - [Licencia y dependencias](#licencia-y-dependencias)

---

# English

## The pain XfinAudio solves

A DJ library can easily contain thousands of tracks with partially useful metadata: BPM, Camelot key, energy, genre, subgenre, mood, tags, edits, versions, and source-specific fields. The real problem is not just owning music; the real problem is turning that library into a sequence that makes sense in a booth.

Common DJ workflow pain points:

| Pain | What goes wrong without tooling | How XfinAudio helps |
|---|---|---|
| Huge libraries are hard to navigate | The DJ scrolls by memory, loses time, and repeats familiar tracks. | XfinAudio persists the scanned library, adds search, status filters, sortable columns, and focused candidate pools. |
| Harmonic compatibility is easy to forget under pressure | A track can look right by genre but clash by key. | The app scores Camelot-compatible transitions and surfaces key warnings. |
| BPM jumps can be musically impossible | A generated sequence may jump from 102 BPM to 122 BPM and break the mix. | Generated adjacent transitions are guarded by a maximum 3% BPM-difference rule. |
| Genre and vibe mismatches hide behind good BPM/key scores | A technically compatible transition can still feel wrong. | Genre, subgenre, mood, and tag overlap are part of the score and warning model. |
| Metadata cleanup is tedious | The DJ may not know which tracks are missing BPM, key, or energy. | XfinAudio separates complete/incomplete tracks and exports Missing BPM, Missing Key, and Missing Energy Serato worklists. |
| Serato export is easy to get wrong | Writing the wrong crate path or replacing the same crate repeatedly creates confusion. | The app writes non-overwriting, strategy-grouped crates under Serato `Subcrates` using the expected crate naming convention. |
| Black-box recommendations are hard to trust | A DJ should not accept a generated playlist blindly. | Every transition is reviewed with component scores, explanations, and warnings before export. |

The point is simple: XfinAudio reduces preparation friction without taking away musical control. The DJ still leads. The app makes the library easier to inspect, sequence, explain, and improve.

## What XfinAudio does

XfinAudio scans existing audio metadata, stores normalized track records, builds deterministic playlist recommendations, explains the quality of the transitions, and exports playlist artifacts.

It is designed around this principle:

> Metadata first, DJ control always, no destructive audio mutation.

Current scope:

- Local desktop app built with PySide6/Qt.
- Python 3.11 package distributed from source/wheel.
- Read-only metadata scanning through mutagen.
- Mixed In Key-oriented metadata parsing.
- SQLite persistence for scanned library records.
- Strategy-based playlist recommendation.
- DJ Prep Copilot planning with Safe, Balanced, and Adventurous variants from one set intent.
- Explainable transition scoring.
- Serato crate export and metadata-cleanup worklists.
- **Full internationalization (i18n) in English and Spanish** with runtime language switching.
- **Duration column** read from audio file metadata.
- **Custom app icon** for macOS dock and PyInstaller bundles.
- **Integrated audio preview** — listen to tracks directly from the library table without leaving the app.
- **Playlist persistence** — save, edit, rename, and re-export playlists via the "My Playlists" screen.
- **Multi-software export** — export playlists to Rekordbox XML, Traktor NML, and VirtualDJ list XML in addition to Serato crates.
- **Live Assistant mode** — performance view with real-time suggestions, risk alerts, and set history.
- Manual desktop QA required before any release claim.

For harmonic scoring concepts, Camelot movement, strategy intent, and current non-goals, see [HARMONIC_MIXING.md](HARMONIC_MIXING.md).

## Core DJ workflow

### 1. Prepare metadata outside XfinAudio

XfinAudio expects the DJ to prepare metadata using existing DJ/library tools, especially Mixed In Key and Serato.

Important metadata fields:

- Title
- Artist
- BPM
- Camelot key
- Energy level
- Genre
- Tags / subgenre / mood / DJ zone-style metadata
- **Duration** (read automatically from file headers)

XfinAudio does not detect BPM or key from waveforms. It reads the metadata that is already present.

### 2. Scan the music folder

The desktop app scans supported audio files recursively:

- `.aif`
- `.aiff`
- `.flac`
- `.m4a`
- `.mp3`
- `.wav`

The scan is read-only. It does not mutate audio files.

During scan, the app:

- Reads tags using mutagen.
- Normalizes Mixed In Key metadata.
- Marks each track as `complete` or `incomplete`.
- Records which required fields are missing.
- Persists the result in the app-owned SQLite database.
- Emits progress updates to keep the desktop UI responsive.
- Supports cooperative scan cancellation.

### 3. Browse and filter the library

The app loads the saved library on launch. If a previous scan folder exists, it restores it so the next scan can behave like a refresh.

Library browsing includes:

- Song search.
- Column sorting (double-click header).
- Column reordering (drag header).
- Complete/incomplete status filter.
- Missing-field filter for BPM, Key, and Energy.
- Visible Missing column.
- Genre and Tags/Subgenre columns.
- **Duration column** (formatted as `M:SS`).
- Path-safe row selection after sorting/filtering.

### 4. Select one or more anchor tracks

Playlist generation is intentionally anchored by DJ intent.

- One selected complete track becomes the playlist start.
- Multiple selected complete tracks become the opening manual order.
- Incomplete tracks are excluded from recommendations.
- The selected tracks are preserved while the app builds around them.

This is important: XfinAudio should not invent a set without respecting the DJ's starting point.

### 5. Choose a strategy

The DJ selects a strategy such as `harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, `same_energy`, or `same_vibe`.

Each strategy changes the scoring weights, filters, or sorting intent.

### 6. Review before export

After recommendation, the app shows:

- Ordered tracks.
- Strategy used.
- Transition score per track-to-track move.
- Key score.
- BPM score.
- Energy score.
- Tag score.
- Final score.
- Warnings.
- Quality summary.

The DJ should inspect this before exporting. This is not a blind automation tool.

### 7. Preview tracks before exporting (optional)

Use the integrated audio player to listen to tracks directly from the library table. Click the play button on any row to preview. The player coordinates so only one track plays at a time, and volume is persisted across sessions.

### 8. Save the playlist (optional)

If the playlist should be kept for later, use the **My Playlists** screen to save it with a custom name. Saved playlists can be reopened, edited via drag-and-drop, renamed, or deleted. They can also be re-exported to any supported DJ software without regenerating.

### 9. Export to DJ software

XfinAudio exports to **Serato**, **Rekordbox**, **Traktor**, and **VirtualDJ**.

Choose the target software from the export screen. Each exporter produces the native format expected by the target platform:

- **Serato**: crate files under `_Serato_/Subcrates` with `%%` hierarchy.
- **Rekordbox**: `DJ_PLAYLISTS` 1.0.0 XML.
- **Traktor**: NML v19 with collection and playlist nodes.
- **VirtualDJ**: `VirtualFolder` XML with artist-title entries.

All exports are strategy-grouped, timestamped, and non-overwriting.

Example logical Serato grouping:

```text
XfinAudio
└── Build
    └── 20260606-030500 - build - Stayin Alive - 2 tracks
```

Actual crate filename under `Subcrates`:

```text
XfinAudio%%Build%%20260606-030500 - build - Stayin Alive - 2 tracks.crate
```

### 10. Improve metadata and refresh

XfinAudio also exports metadata worklists:

```text
XfinAudio%%Metadata%%Incomplete%%...
XfinAudio%%Metadata%%Missing BPM%%...
XfinAudio%%Metadata%%Missing Key%%...
XfinAudio%%Metadata%%Missing Energy%%...
```

The intended loop:

1. Filter by `Incomplete` or a specific missing field.
2. Export the metadata worklist crate to Serato.
3. Complete the missing metadata in Serato or another metadata tool.
4. Return to XfinAudio.
5. Click `Scan Metadata` on the same folder.
6. Confirm the refresh delta: incomplete before → incomplete after; fixed count.

## Technical techniques used

### Metadata-first architecture

XfinAudio is deliberately metadata-first. It avoids expensive or legally sensitive audio DSP scope and focuses on fields DJs already manage.

It reads:

- BPM from common BPM tags.
- Camelot key from Mixed In Key-style fields, standard key fields, or title fallback.
- Energy from Mixed In Key-style energy fields, grouping, publisher/comment patterns, or title fallback.
- Genre from standard genre tags.
- Tags from genre, mood, subgenre, DJ zone, and genre category-style fields.
- **Duration from audio file headers** (mutagen `info.length`), formatted as `M:SS`.

### Mixed In Key parsing contract

The parser normalizes raw tag dictionaries into a stable model:

```text
TrackRecord
├── title
├── artist
├── bpm
├── camelot_key
├── energy_level
├── duration
├── genre
├── tags
├── metadata_status
├── missing_required_fields
├── source_fields
└── raw_metadata
```

A track is complete only when BPM, Camelot key, and energy are present. Duration is displayed but not required for completeness.

### Deterministic transition scoring

Each transition is scored through transparent components:

| Component | What it measures |
|---|---|
| Harmonic score | Camelot compatibility between left and right track. |
| BPM score | Percent BPM distance using a fuzzy scoring curve. |
| Energy score | Distance between Mixed In Key-style energy levels. |
| Tag score | Overlap between genre, subgenre, mood, and tag metadata. |

The final score is a weighted average of available components. Missing required metadata produces warnings instead of pretending the transition is reliable.

### Camelot harmonic logic

The harmonic layer parses keys such as `11B`, validates the Camelot range, and scores musically meaningful moves. It also supports key-shift normalization during scoring, allowing a transition to be evaluated as if one side had been pitch shifted by semitones.

This matters for DJs because pitch/key adjustment can make a transition viable even when raw stored keys look less compatible.

### BPM guardrail: maximum 3% generated adjacent jump

Generated adjacent tracks are filtered so a generated transition does not exceed a 3% BPM difference.

This guardrail exists because BPM scoring alone is not enough. A sequence can have a decent overall plan but still contain a locally impossible jump. XfinAudio drops generated tracks that would break that rule and reports a warning.

Manual DJ-selected anchor/order tracks are still respected as controls; the guardrail protects generated continuation quality.

### Strategy profiles

Strategies are policy profiles, not random prompts. Each strategy defines:

- Name.
- Display name.
- Description.
- Harmonic/BPM/energy/tag weights.
- Optional energy range.
- Optional BPM range.
- Optional energy tolerance.
- Optional sort hint.
- Optional vibe metadata requirement.

This makes behavior testable and explainable.

### Candidate narrowing for desktop speed

The desktop app limits the interactive recommendation pool so a large library remains usable in a GUI workflow.

The pool keeps selected priority tracks, then favors compatible candidates based on shared vibe terms and closeness to anchors. This prevents the app from blocking while still keeping recommendations anchored in DJ intent.

### Background workers for UI responsiveness

Long operations run away from the Qt UI thread:

- Metadata scan runs in a worker thread.
- Playlist recommendation runs in a worker thread.
- The UI disables conflicting actions while work is in progress.
- The UI restores valid controls after completion/failure.
- Scan cancellation is cooperative and safe.

### SQLite persistence

The app persists scanned tracks in an app-owned SQLite database keyed by absolute file path.

The repository upserts by path, so a refresh updates metadata for the same files instead of duplicating records. This is essential for the metadata-improvement loop.

### Settings persistence

App settings store workflow preferences such as:

- Safe export folder.
- Last scan folder.
- **UI language** (Auto / English / Español).

Persisting the last scan folder turns a later scan into a real refresh workflow.

### Internationalization (i18n)

XfinAudio uses Qt's `QTranslator` system for full runtime translation:

- All UI strings are marked with `self.tr()` / `QCoreApplication.translate()`.
- Source language is English; Spanish translations ship as compiled `.qm` files.
- Language can be changed in **Settings → Language** (requires app restart).
- Translation workflow: mark strings → run `scripts/update_translations.py` → edit `.ts` source or run `scripts/fill_spanish_translations.py` → `.qm` files compiled automatically.

### Serato crate generation

XfinAudio builds deterministic Serato crate bytes using a supported TLV subset:

- Version record.
- Ordered track records.
- UTF-16BE path payloads.
- Validation against expected ordered paths.

Crate writes require explicit confirmation, create backups when replacing existing targets, and can be rolled back.

### Export explainability

The app can export deterministic playlist artifacts:

- JSON recommendation export.
- CSV playlist export.
- M3U playlist export.
- JSON quality report export.
- JSON and CSV DJ Readiness report export.

The JSON recommendation includes the explanation model so reviewers can inspect not just the playlist, but why each transition exists.

## Application features

### Desktop library management

- Choose folder.
- Scan metadata.
- Cancel scan.
- Load saved library on startup.
- Persist last scan folder.
- Show complete/incomplete counts.
- Show refresh delta after re-scan.
- Filter by metadata status.
- Filter by missing required field.
- Search by song title.
- Sort columns (double-click header).
- Reorder columns (drag header).
- Display title, artist, BPM, key, energy, **duration**, missing fields, genre, tags/subgenre, status, and path.

### Recommendation workflow

- Requires selecting at least one complete track.
- Supports selected start track.
- Supports multiple selected tracks as opening manual order.
- Uses only complete tracks for recommendations.
- Preserves DJ-selected controls.
- Narrows candidates for interactive desktop speed.
- Applies selected strategy profile.
- Supports DJ Prep Copilot intent planning with comparable Safe, Balanced, and Adventurous variants.
- Shows a desktop Prep Copilot comparison panel with variant readiness, track count, warnings, target track count, and genre focus controls.
- Color-codes Prep Copilot readiness cells, supports double-click to apply a variant quickly, and shows the applied variant near export controls.
- Applies the selected Prep Copilot variant into the main review, DJ Readiness, transition review, and Serato export flow.
- Exports applied Prep Copilot variants to non-overwriting Serato crates grouped by strategy and variant.
- Previews the exact Serato export destination, track count, variant, write behavior, and readiness before writing a crate.
- Writes DJ Readiness JSON/CSV sidecar reports next to every exported Serato crate for auditability.
- Shows recent Serato export history with crate, readiness JSON, and readiness CSV paths.
- Runs recommendation off the UI thread.
- Shows ordered output and transition scores.

### Review and quality workflow

- Transition review table.
- Key score.
- BPM score.
- Energy score.
- Tag score.
- Final score.
- Human-readable warnings.
- Quality summary with track count, transition count, average score, and warning count.
- DJ Readiness status: `Ready`, `Needs Review`, or `Blocked`.
- DJ Readiness check panel with `Check`, `Status`, and `Detail` columns, plus color-coded status badges.
- DJ Readiness report export to JSON and CSV in the configured safe export folder for audit and prep handoff.
- Operational blockers for impossible BPM jumps, missing required metadata, and unresolved Serato paths.
- Serato round-trip validation after export: crate bytes must match the plan and referenced files must resolve on disk.
- Export guidance that tells the DJ to inspect results before Serato export.

### DJ software export workflow

- Detects usable Serato libraries from home and mounted volumes.
- Chooses the Serato library that best matches the playlist track paths.
- Prefers the correct volume root for external-drive libraries.
- Converts absolute macOS paths into Serato crate-relative paths.
- Exports generated recommendations into strategy-grouped crates for Serato.
- Exports complete/incomplete metadata worklists for Serato.
- Exports Missing BPM, Missing Key, and Missing Energy worklists for Serato.
- Exports to **Rekordbox XML**, **Traktor NML**, and **VirtualDJ list XML**.
- Keeps export history visible in the app.
- Avoids overwriting generated crates by timestamp and uniqueness suffix.

### Audio preview

- Built-in audio player using Qt Multimedia.
- Play/pause per track directly from the library table.
- Single-player coordination: starting a new preview stops the current one.
- Volume control persisted in settings.
- Automatic cleanup on track change or app close.

### Playlist persistence

- Save generated playlists to an app-owned SQLite database.
- Browse, rename, and delete saved playlists via the **My Playlists** screen.
- Drag-and-drop playlist editor: reorder tracks, add from library, remove by selection.
- Re-export saved playlists to any supported DJ software.

### Multi-software export

- Export playlists to **Serato**, **Rekordbox**, **Traktor**, and **VirtualDJ**.
- Software selector in the export screen with dynamic button labels.
- Rekordbox: `DJ_PLAYLISTS` 1.0.0 XML with track metadata.
- Traktor: NML v19 with collection entries and playlist nodes.
- VirtualDJ: `VirtualFolder` XML with artist-title entries.
- Backward-compatible: Serato remains the default path.

### Live Assistant mode

- Performance view for booth use: **Now Playing**, **Next Suggestions**, **Set History**.
- Real-time risk alerts for BPM jumps, key clashes, and energy drops.
- One-click loading of next track into the suggestion pipeline.
- Keyboard shortcuts: `Esc` to clear, `Space` to load next, `1`/`2`/`3` to accept suggestions.

### Settings and localization

- **Settings dialog** with language selector (Auto / English / Español).
- **Safe export folder** configuration.
- **Library info** showing scan folder and track counts.
- Language change requires app restart and prompts accordingly.

### Safety and release workflow

- Read-only audio scanning.
- App-owned database/settings/export writes only.
- Serato crate write planning before write.
- Confirmed crate writes only.
- Backup when replacing an existing crate.
- Validation after write.
- Rollback support.
- Automated release/readiness checks.
- Explicit manual desktop QA requirement.

## Recommendation strategies

| Strategy | Intent | Main behavior |
|---|---|---|
| `harmonic_journey` | Smooth harmonic travel. | Prioritizes Camelot compatibility while keeping BPM and energy smooth. |
| `warmup` | Controlled opening section. | Focuses on lower-to-mid energy tracks and ascending energy. |
| `build` | Gradually lift the room. | Prefers rising energy while still considering harmonic/BPM/tag quality. |
| `peak_time` | High-energy section. | Filters toward energy 7-10 and sorts by stronger energy. |
| `chill` | Lower-intensity sequence. | Prefers lower energy and BPM up to 118. |
| `same_energy` | Stable intensity band. | Heavily weights energy and keeps a stable energy profile. |
| `same_vibe` | Shared genre/tag feel. | Heavily weights genre/tag overlap and falls back when vibe metadata is unavailable. |

## DJ software export model

XfinAudio supports exporting to **Serato**, **Rekordbox**, **Traktor**, and **VirtualDJ**.

### Serato crates

XfinAudio does not mutate live Serato database V2 files. It writes Serato crate files under `_Serato_/Subcrates`.

The app uses an explicit safe export/backup/validation flow:

1. Build a dry-run export plan.
2. Validate the destination is a `_Serato_` folder with `Subcrates`.
3. Convert track paths to the correct crate-relative form.
4. Build deterministic crate bytes.
5. Require explicit write confirmation.
6. Backup any existing target crate.
7. Write the crate.
8. Validate the bytes written match the plan.
9. Provide rollback action.

Generated playlist crates are not overwritten every time. They are timestamped and grouped by strategy.

Metadata worklist crates are also timestamped and grouped by purpose.

### Rekordbox, Traktor, and VirtualDJ

For non-Serato targets, XfinAudio writes standard XML files in the format expected by each platform:

- **Rekordbox**: `DJ_PLAYLISTS` 1.0.0 XML with track metadata (Title, Artist, BPM, Key, Energy, Genre).
- **Traktor**: NML v19 XML with collection entries and playlist nodes.
- **VirtualDJ**: `VirtualFolder` XML with `song` entries using `artist - title` format.

These exports follow the same strategy-grouped, timestamped, non-overwriting convention as Serato crates. The DJ selects the target software from a dropdown in the export screen.

## Project status

- **Author and maintainer:** [Freddy Molina](https://github.com/FmBlueSystem) — [BlueSystem.io](https://bluesystem.io), Audio Division.
- License posture: full open source under GPL-3.0-only. See `LICENSE` and `docs/open-source-license.md`.
- Distribution model: XfinAudio ships as an installable Python package (source/wheel). Users install it with `pip`, `pipx`, or `uv tool` and the dependency resolver fetches PySide6 and mutagen from PyPI under their own licenses.
- **macOS .app bundle**: A PyInstaller spec is included under `packaging/pyinstaller/` for building a local `.app` bundle. The bundle includes Qt Multimedia plugins and FFmpeg libraries for audio preview. Unsigned bundles work for personal use; signed/notarized distribution requires Apple Developer ID and separate legal review.
- **Test suite**: 734 tests, all passing. Strict TDD is enforced for all changes.
- Platform posture: validated on macOS with Python 3.11. The dependencies are cross-platform, but Linux and Windows are not yet validated.
- Publication checklist: follow `docs/repository-publication-checklist.md` before turning a local tree into a public source repository.

## Safety posture and non-goals

XfinAudio is intentionally non-destructive:

- It does not mutate audio files.
- It does not render, mix, time-stretch, pitch-shift, or analyze waveforms.
- It does not perform key detection, BPM detection, beat tracking, or cue/phrase detection.
- It does not mutate live Serato database V2 files.
- The app writes only its app-owned database, settings, and export files.
- Serato crate writes are only through the explicit safe export/backup/validation flow documented in the project.

Non-goals:

- Replacing Serato DJ Pro.
- Replacing Mixed In Key.
- Replacing the DJ's ears or experience.
- Auto-generating a final set without review.
- Editing audio files.
- Publishing a signed macOS binary before signing, notarization, dependency-license review, and manual QA are complete.

## Install

XfinAudio is distributed as a Python package, not as a signed binary. Install it as an isolated tool straight from the repository (no PyPI account or Apple Developer ID required):

```bash
uv tool install git+https://github.com/FmBlueSystem/XfinAudio.git
# or
pipx install git+https://github.com/FmBlueSystem/XfinAudio.git
```

Then launch the desktop app:

```bash
xfinaudio
```

### Building a macOS .app bundle (optional)

For personal use or testing, you can build a local `.app` bundle with PyInstaller:

```bash
uv run python -m PyInstaller packaging/pyinstaller/xfinaudio.spec \
  --clean --noconfirm \
  --distpath packaging/pyinstaller/dist \
  --workpath packaging/pyinstaller/build
```

The resulting `packaging/pyinstaller/dist/XfinAudio.app` can be launched with:

```bash
open packaging/pyinstaller/dist/XfinAudio.app
```

> **Note:** Unsigned `.app` bundles may show a security warning on first launch. Go to **System Settings → Privacy & Security** and click **Open Anyway**.

Publishing the package to PyPI (so users can run `pipx install xfinaudio`) is an optional later step that requires a PyPI account and API token; it does not require code changes.

## Quick start for development

Requirements: Python 3.11 and `uv`.

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Launch the local desktop app for manual QA:

```bash
uv run xfinaudio
```

Update translations after adding new translatable strings:

```bash
uv run python scripts/update_translations.py
uv run python scripts/fill_spanish_translations.py
```

## Release gates

Before any release claim, run the automated gates and record the manual gates described in `docs/release-readiness-smoke.md`:

```bash
uv run python scripts/release_gate_check.py --run
uv run python scripts/smoke_release_readiness.py
```

Manual desktop QA is still required for real user workflows. Signed macOS `.app`/DMG redistribution requires Apple Developer ID, notarization, and separate legal review for binary redistribution.

## Trademarks

XfinAudio is an independent project and is not affiliated with, endorsed by, or sponsored by any third-party companies whose products or trademarks are referenced.

- **Mixed In Key** is a trademark of Mixed In Key LLC.
- **Serato**, **Serato DJ Pro**, and related marks are trademarks or registered trademarks of Serato Limited.
- **Camelot**, **Camelot Wheel**, and **Camelot System** are trademarks of Mixed In Key LLC.
- **Open Key Notation** is an open standard.

All other trademarks, service marks, and brand identifiers referenced are the property of their respective owners.

## License and dependency caveats

Source code is distributed under GPL-3.0-only. Redistribution must comply with GPLv3 and third-party dependency obligations.

No legal advice or legal clearance is implied by this repository documentation. Binary/app bundle redistribution needs legal review for PySide6/Qt, mutagen, and other third-party dependencies. See `NOTICE.md`, `docs/open-source-license.md`, and `docs/third-party-license-inventory.md`.

---

# Español

## El dolor que XfinAudio viene a resolver

Una biblioteca DJ puede tener miles de canciones con metadata parcialmente útil: BPM, Camelot key, energía, género, subgénero, mood, tags, edits, versiones y campos propios de distintas herramientas. El problema real no es solamente tener música; el problema real es convertir esa biblioteca en una secuencia que tenga sentido musical en cabina.

Dolores comunes del flujo DJ:

| Dolor | Qué pasa sin una herramienta dedicada | Cómo ayuda XfinAudio |
|---|---|---|
| La biblioteca es demasiado grande | El DJ navega por memoria, pierde tiempo y repite siempre los mismos tracks. | XfinAudio persiste la biblioteca escaneada, agrega búsqueda, filtros, columnas ordenables y pools de candidatos enfocados. |
| La compatibilidad armónica se olvida bajo presión | Un track puede parecer correcto por género pero chocar por tonalidad. | La app puntúa transiciones compatibles por Camelot y muestra advertencias de key. |
| Los saltos de BPM pueden ser imposibles | Una secuencia puede saltar de 102 BPM a 122 BPM y romper la mezcla. | Las transiciones generadas tienen una regla máxima de 3% de diferencia de BPM entre canciones adyacentes. |
| El género/vibe puede no coincidir aunque BPM y key sí | Una transición técnicamente compatible puede sentirse mal. | Género, subgénero, mood y tags entran en el score y en las advertencias. |
| Completar metadata es tedioso | El DJ no siempre sabe qué canciones necesitan BPM, key o energía. | XfinAudio separa completas/incompletas y exporta worklists de Missing BPM, Missing Key y Missing Energy a Serato. |
| Exportar a Serato puede ser confuso | Es fácil escribir en una ruta incorrecta o reemplazar el mismo crate una y otra vez. | La app escribe crates no destructivos, agrupados por estrategia, dentro de `Subcrates` y con nombres compatibles con Serato. |
| Las recomendaciones caja negra no son confiables | Un DJ no debería aceptar una playlist generada sin entenderla. | Cada transición muestra scores, explicaciones y warnings antes de exportar. |

La idea es simple: XfinAudio reduce fricción en la preparación sin quitarle control musical al DJ. El humano dirige. La app ayuda a inspeccionar, ordenar, explicar y mejorar la biblioteca.

Desarrollado por **Freddy Molina** en **[BlueSystem.io](https://bluesystem.io)** — División de Audio.

## Qué hace XfinAudio

XfinAudio escanea metadata existente, guarda records normalizados, genera recomendaciones determinísticas de playlists, explica la calidad de las transiciones y exporta artefactos de playlist.

Principio central:

> Metadata primero, control DJ siempre, cero mutación destructiva de audio.

Alcance actual:

- App desktop local construida con PySide6/Qt.
- Paquete Python 3.11 distribuido desde source/wheel.
- Escaneo read-only con mutagen.
- Parser orientado a metadata de Mixed In Key.
- Persistencia SQLite para la biblioteca escaneada.
- Recomendación por estrategias.
- Scoring explicable por transición.
- Exportación a Serato crate y worklists para completar metadata.
- **Internacionalización completa (i18n) en inglés y español** con cambio de idioma en tiempo de ejecución.
- **Columna de duración** leída desde los headers de los archivos de audio.
- **Ícono personalizado** para dock de macOS y bundles PyInstaller.
- **Audio preview integrado** — reproducir tracks directamente desde la tabla de librería sin salir de la app.
- **Persistencia de playlists** — guardar, editar, renombrar y re-exportar playlists desde la pantalla "My Playlists".
- **Exportación multi-software** — exportar playlists a Rekordbox XML, Traktor NML y VirtualDJ list XML además de Serato crates.
- **Modo Live Assistant** — vista de performance con sugerencias en tiempo real, alertas de riesgo e historial de set.
- Manual desktop QA obligatorio antes de cualquier claim de release.

Para conceptos de harmonic scoring, movimientos Camelot, intención de estrategias y no-objetivos actuales, ver [HARMONIC_MIXING.md](HARMONIC_MIXING.md).

## Flujo DJ principal

### 1. Preparar metadata fuera de XfinAudio

XfinAudio espera que el DJ prepare metadata usando herramientas existentes, especialmente Mixed In Key y Serato.

Campos importantes:

- Título
- Artista
- BPM
- Camelot key
- Nivel de energía
- Género
- Tags / subgénero / mood / metadata tipo DJ zone
- **Duración** (leída automáticamente desde los headers del archivo)

XfinAudio no detecta BPM ni key desde la forma de onda. Lee metadata que ya existe.

### 2. Escanear la carpeta de música

La app escanea recursivamente archivos soportados:

- `.aif`
- `.aiff`
- `.flac`
- `.m4a`
- `.mp3`
- `.wav`

El escaneo es de solo lectura. No modifica archivos de audio.

Durante el scan, la app:

- Lee tags usando mutagen.
- Normaliza metadata de Mixed In Key.
- Marca cada track como `complete` o `incomplete`.
- Registra qué campos obligatorios faltan.
- Persiste resultados en SQLite propio de la app.
- Muestra progreso para mantener la UI responsive.
- Permite cancelar de forma cooperativa y segura.

### 3. Navegar y filtrar la biblioteca

La app carga la biblioteca guardada al iniciar. Si existe una carpeta escaneada previamente, la restaura para que el siguiente scan funcione como refresh.

La navegación incluye:

- Búsqueda por canción.
- Ordenamiento por columnas (doble-click en header).
- Reordenamiento de columnas (drag en header).
- Filtro por estado completo/incompleto.
- Filtro por campo faltante: BPM, Key y Energy.
- Columna visible de Missing.
- Columnas de Genre y Tags/Subgenre.
- **Columna de Duration** (formateada como `M:SS`).
- Selección segura por path aunque haya sorting/filtering.

### 4. Seleccionar una o varias canciones ancla

La generación de playlist está intencionalmente anclada por la intención del DJ.

- Una canción completa seleccionada se convierte en el inicio de la playlist.
- Varias canciones completas seleccionadas se convierten en el orden manual inicial.
- Las canciones incompletas se excluyen de recomendaciones.
- Las canciones seleccionadas se preservan mientras la app construye alrededor.

Esto es clave: XfinAudio no debería inventar un set ignorando el punto de partida del DJ.

### 5. Elegir una estrategia

El DJ elige una estrategia como `harmonic_journey`, `warmup`, `build`, `peak_time`, `chill`, `same_energy` o `same_vibe`.

Cada estrategia cambia pesos, filtros o intención de ordenamiento.

### 6. Revisar antes de exportar

Después de recomendar, la app muestra:

- Tracks ordenados.
- Estrategia usada.
- Score de transición entre canción y canción.
- Key score.
- BPM score.
- Energy score.
- Tag score.
- Final score.
- Warnings.
- Resumen de calidad.

El DJ debe revisar esto antes de exportar. No es automatización ciega.

### 7. Previsualizar tracks antes de exportar (opcional)

Usar el reproductor integrado para escuchar tracks directamente desde la tabla de librería. Click en el botón de play de cualquier fila para previsualizar. El reproductor coordina para que solo suene un track a la vez, y el volumen se persiste entre sesiones.

### 8. Guardar la playlist (opcional)

Si la playlist debe conservarse para más tarde, usar la pantalla **My Playlists** para guardarla con un nombre personalizado. Las playlists guardadas se pueden reabrir, editar vía drag-and-drop, renombrar o eliminar. También se pueden re-exportar a cualquier software DJ soportado sin regenerar.

### 9. Exportar a software DJ

XfinAudio exporta a **Serato**, **Rekordbox**, **Traktor** y **VirtualDJ**.

Elegir el software objetivo desde la pantalla de export. Cada exporter produce el formato nativo esperado por la plataforma objetivo:

- **Serato**: crate files bajo `_Serato_/Subcrates` con jerarquía `%%`.
- **Rekordbox**: XML `DJ_PLAYLISTS` 1.0.0.
- **Traktor**: NML v19 con collection y playlist nodes.
- **VirtualDJ**: XML `VirtualFolder` con entradas artist-title.

Todas las exportaciones son agrupadas por estrategia, con timestamp y no destructivas.

Ejemplo lógico en Serato:

```text
XfinAudio
└── Build
    └── 20260606-030500 - build - Stayin Alive - 2 tracks
```

Archivo real bajo `Subcrates`:

```text
XfinAudio%%Build%%20260606-030500 - build - Stayin Alive - 2 tracks.crate
```

### 10. Mejorar metadata y refrescar

XfinAudio también exporta worklists de metadata:

```text
XfinAudio%%Metadata%%Incomplete%%...
XfinAudio%%Metadata%%Missing BPM%%...
XfinAudio%%Metadata%%Missing Key%%...
XfinAudio%%Metadata%%Missing Energy%%...
```

Loop esperado:

1. Filtrar por `Incomplete` o por un campo faltante específico.
2. Exportar el crate de worklist a Serato.
3. Completar la metadata faltante en Serato u otra herramienta.
4. Volver a XfinAudio.
5. Hacer click en `Scan Metadata` sobre la misma carpeta.
6. Confirmar el delta: incompletas antes → incompletas después; cantidad corregida.

## Técnicas usadas

### Arquitectura metadata-first

XfinAudio es deliberadamente metadata-first. Evita meterse en DSP/audio analysis caro, lento o fuera de alcance legal, y se concentra en los campos que los DJs ya administran.

Lee:

- BPM desde tags comunes de BPM.
- Camelot key desde campos tipo Mixed In Key, campos estándar de key o fallback en el título.
- Energy desde campos tipo Mixed In Key, grouping, publisher/comment o fallback en el título.
- Genre desde tags estándar.
- Tags desde genre, mood, subgenre, DJ zone y genre category.
- **Duración desde headers de audio** (`info.length` de mutagen), formateada como `M:SS`.

### Contrato de parsing Mixed In Key

El parser normaliza diccionarios de tags crudos en un modelo estable:

```text
TrackRecord
├── title
├── artist
├── bpm
├── camelot_key
├── energy_level
├── duration
├── genre
├── tags
├── metadata_status
├── missing_required_fields
├── source_fields
└── raw_metadata
```

Un track es completo solamente cuando tiene BPM, Camelot key y energy. La duración se muestra pero no es requerida para completitud.

### Scoring determinístico por transición

Cada transición se puntúa con componentes transparentes:

| Componente | Qué mide |
|---|---|
| Harmonic score | Compatibilidad Camelot entre track izquierdo y derecho. |
| BPM score | Distancia porcentual de BPM usando curva fuzzy. |
| Energy score | Distancia entre niveles de energía estilo Mixed In Key. |
| Tag score | Overlap entre género, subgénero, mood y tags. |

El score final es un promedio ponderado de los componentes disponibles. Si falta metadata obligatoria, la app emite warnings en vez de fingir confiabilidad.

### Lógica armónica Camelot

La capa armónica parsea keys como `11B`, valida el rango Camelot y puntúa movimientos musicalmente razonables. También soporta normalización por pitch/key shift durante el scoring, permitiendo evaluar una transición como si uno de los lados estuviera desplazado por semitonos.

Esto importa porque un ajuste de pitch/key puede volver viable una transición aunque las keys originales parezcan menos compatibles.

### Regla BPM: máximo 3% entre canciones generadas adyacentes

Las canciones generadas adyacentes se filtran para que una transición no supere el 3% de diferencia de BPM.

Esta regla existe porque el score BPM no alcanza por sí solo. Una secuencia puede verse bien en promedio pero contener un salto local imposible. XfinAudio elimina tracks generados que rompen esa regla y reporta warning.

Los anchors/órdenes seleccionados manualmente por el DJ siguen siendo controles respetados; la regla protege la continuidad generada.

### Perfiles de estrategia

Las estrategias son perfiles de política, no prompts aleatorios. Cada estrategia define:

- Nombre.
- Nombre visible.
- Descripción.
- Pesos harmonic/BPM/energy/tag.
- Rango opcional de energía.
- Rango opcional de BPM.
- Tolerancia opcional de energía.
- Hint opcional de ordenamiento.
- Requisito opcional de metadata de vibe.

Eso vuelve la app testeable, explicable y mantenible.

### Reducción de candidatos para velocidad desktop

La app limita el pool interactivo de recomendación para que una biblioteca grande siga siendo usable en UI desktop.

El pool conserva tracks prioritarios seleccionados y luego favorece candidatos compatibles por términos de vibe y cercanía a los anchors. Así evita bloquear la app y mantiene la intención musical del DJ.

### Workers en background para UI responsive

Operaciones largas corren fuera del thread de Qt:

- El scan de metadata corre en un worker thread.
- La recomendación corre en un worker thread.
- La UI deshabilita acciones conflictivas durante el trabajo.
- La UI restaura controles válidos al terminar o fallar.
- La cancelación del scan es cooperativa y segura.

### Persistencia SQLite

La app persiste tracks escaneados en una base SQLite propia, usando el path absoluto como clave.

El repositorio hace upsert por path, así un refresh actualiza metadata de los mismos archivos en vez de duplicar records. Esto es esencial para el loop de mejora de metadata.

### Persistencia de settings

La app guarda preferencias como:

- Carpeta segura de exportación.
- Última carpeta escaneada.
- **Idioma de UI** (Auto / English / Español).

Guardar la última carpeta escaneada convierte el siguiente scan en un refresh real.

### Internacionalización (i18n)

XfinAudio usa el sistema `QTranslator` de Qt para traducción completa en tiempo de ejecución:

- Todas las cadenas de UI están marcadas con `self.tr()` / `QCoreApplication.translate()`.
- El idioma fuente es inglés; las traducciones al español se distribuyen como archivos `.qm` compilados.
- El idioma se puede cambiar en **Ajustes → Idioma** (requiere reiniciar la app).
- Flujo de traducción: marcar cadenas → ejecutar `scripts/update_translations.py` → editar fuente `.ts` o ejecutar `scripts/fill_spanish_translations.py` → archivos `.qm` compilados automáticamente.

### Generación de Serato crates

XfinAudio construye bytes determinísticos de Serato crate usando un subset TLV soportado:

- Record de versión.
- Records ordenados de tracks.
- Payload de paths en UTF-16BE.
- Validación contra paths esperados.

La escritura requiere confirmación explícita, crea backup cuando reemplaza un target existente y soporta rollback.

### Export explicable

La app puede exportar artefactos determinísticos:

- JSON de recomendación.
- CSV de playlist.
- M3U.
- JSON de quality report.
- JSON y CSV del DJ Readiness report.

El JSON incluye el modelo de explicación para revisar no solo la playlist, sino por qué existe cada transición.

## Características de la app

### Manejo de biblioteca desktop

- Elegir carpeta.
- Escanear metadata.
- Cancelar scan.
- Cargar biblioteca guardada al iniciar.
- Persistir última carpeta escaneada.
- Mostrar conteo complete/incomplete.
- Mostrar delta luego de refrescar.
- Filtrar por estado de metadata.
- Filtrar por campo obligatorio faltante.
- Buscar por título de canción.
- Ordenar columnas (doble-click en header).
- Reordenar columnas (drag en header).
- Mostrar title, artist, BPM, key, energy, **duration**, missing fields, genre, tags/subgenre, status y path.

### Flujo de recomendación

- Requiere seleccionar al menos un track completo.
- Soporta track inicial seleccionado.
- Soporta múltiples tracks seleccionados como orden manual inicial.
- Usa solo tracks completos.
- Respeta controles del DJ.
- Reduce candidatos para velocidad interactiva.
- Aplica perfil de estrategia.
- Soporta planificación DJ Prep Copilot con variantes comparables Safe, Balanced y Adventurous.
- Muestra un panel desktop Prep Copilot comparando readiness, cantidad de tracks, warnings, target track count y genre focus.
- Colorea las celdas de readiness del Prep Copilot, permite doble-click para aplicar una variante rápido y muestra la variante aplicada cerca de export.
- Aplica la variante Prep Copilot seleccionada al flujo principal de review, DJ Readiness, transición y export Serato.
- Exporta variantes Prep Copilot aplicadas a crates Serato no destructivos agrupados por estrategia y variante.
- Previsualiza destino exacto de export Serato, cantidad de tracks, variante, comportamiento de escritura y readiness antes de escribir el crate.
- Escribe reportes sidecar DJ Readiness JSON/CSV junto a cada crate Serato exportado para auditoría.
- Muestra historial reciente de export Serato con paths de crate, readiness JSON y readiness CSV.
- Corre recomendación fuera del thread de UI.
- Muestra resultado ordenado y scores de transición.

### Flujo de revisión y calidad

- Tabla de transición.
- Key score.
- BPM score.
- Energy score.
- Tag score.
- Final score.
- Warnings legibles.
- Resumen con track count, transition count, average score y warning count.
- Estado DJ Readiness: `Ready`, `Needs Review` o `Blocked`.
- Panel DJ Readiness con columnas `Check`, `Status` y `Detail`, más badges visuales por estado.
- Export del DJ Readiness report a JSON y CSV en la carpeta segura configurada para auditoría y preparación.
- Bloqueos operativos para saltos BPM imposibles, metadata obligatoria faltante y paths que Serato no puede resolver.
- Validación Serato round-trip después de exportar: los bytes del crate deben coincidir con el plan y los archivos referenciados deben existir en disco.
- Guía de exportación para revisar antes de mandar a Serato.

### Flujo de exportación a software DJ

- Detecta bibliotecas Serato utilizables en home y volúmenes montados.
- Selecciona la biblioteca Serato que mejor coincide con los paths de tracks.
- Prefiere el root correcto del volumen externo.
- Convierte paths absolutos de macOS a paths relativos de crate Serato.
- Exporta recomendaciones agrupadas por estrategia a Serato.
- Exporta worklists complete/incomplete a Serato.
- Exporta worklists Missing BPM, Missing Key y Missing Energy a Serato.
- Exporta a **Rekordbox XML**, **Traktor NML** y **VirtualDJ list XML**.
- Muestra historial de exportaciones dentro de la app.
- Evita sobrescribir crates generados mediante timestamp y sufijo único.

### Vista previa de audio

- Reproductor integrado con Qt Multimedia.
- Play/pause por track directamente desde la tabla de librería.
- Coordinación de reproductor único: iniciar una preview nueva detiene la actual.
- Control de volumen persistido en settings.
- Limpieza automática al cambiar de track o cerrar la app.

### Persistencia de playlists

- Guardar playlists generadas en base SQLite propia de la app.
- Navegar, renombrar y eliminar playlists guardadas desde la pantalla **My Playlists**.
- Editor drag-and-drop: reordenar tracks, agregar desde librería, eliminar por selección.
- Re-exportar playlists guardadas a cualquier software DJ soportado.

### Exportación multi-software

- Exportar playlists a **Serato**, **Rekordbox**, **Traktor** y **VirtualDJ**.
- Selector de software en la pantalla de export con labels dinámicos.
- Rekordbox: XML `DJ_PLAYLISTS` 1.0.0 con metadata de tracks.
- Traktor: NML v19 con entradas de colección y nodos de playlist.
- VirtualDJ: XML `VirtualFolder` con entradas artist-title.
- Retrocompatible: Serato sigue siendo el path por defecto.

### Modo Live Assistant

- Vista de performance para uso en cabina: **Now Playing**, **Next Suggestions**, **Set History**.
- Alertas de riesgo en tiempo real por saltos de BPM, choques de key y caídas de energía.
- Carga con un click del siguiente track al pipeline de sugerencias.
- Atajos de teclado: `Esc` para limpiar, `Space` para cargar siguiente, `1`/`2`/`3` para aceptar sugerencias.

### Ajustes y localización

- **Diálogo de Ajustes** con selector de idioma (Auto / English / Español).
- **Carpeta segura de exportación** configurable.
- **Información de biblioteca** mostrando carpeta escaneada y conteos de tracks.
- El cambio de idioma requiere reiniciar la app y muestra el prompt correspondiente.

### Seguridad y release

- Scan de audio read-only.
- Escrituras solo en base/settings/export propios de la app.
- Plan de Serato crate antes de escribir.
- Escritura confirmada únicamente.
- Backup si reemplaza un crate existente.
- Validación post-write.
- Soporte de rollback.
- Checks automáticos de release/readiness.
- Manual desktop QA explícitamente requerido.

## Estrategias de recomendación

| Estrategia | Intención | Comportamiento principal |
|---|---|---|
| `harmonic_journey` | Viaje armónico suave. | Prioriza compatibilidad Camelot manteniendo BPM y energía suaves. |
| `warmup` | Apertura controlada. | Enfoca tracks de energía baja/media y subida progresiva. |
| `build` | Levantar la pista gradualmente. | Prefiere energía ascendente considerando harmonic/BPM/tag. |
| `peak_time` | Momento de alta energía. | Filtra hacia energía 7-10 y ordena por energía fuerte. |
| `chill` | Secuencia más baja/introspectiva. | Prefiere menor energía y BPM hasta 118. |
| `same_energy` | Intensidad estable. | Pesa fuerte la energía y mantiene una banda estable. |
| `same_vibe` | Género/tag compartido. | Pesa fuerte el overlap de género/tags y hace fallback si falta metadata de vibe. |

## Modelo de exportación a software DJ

XfinAudio soporta exportación a **Serato**, **Rekordbox**, **Traktor** y **VirtualDJ**.

### Crates Serato

XfinAudio no modifica live Serato database V2 files. Escribe archivos Serato crate bajo `_Serato_/Subcrates`.

La app usa un explicit safe export/backup/validation flow:

1. Construir un plan dry-run.
2. Validar que el destino sea una carpeta `_Serato_` con `Subcrates`.
3. Convertir paths a formato relativo correcto para crate.
4. Construir bytes determinísticos de crate.
5. Requerir confirmación explícita de escritura.
6. Hacer backup si existe un crate target.
7. Escribir el crate.
8. Validar que los bytes escritos coinciden con el plan.
9. Informar acción de rollback.

Los crates generados de playlist no se reemplazan cada vez. Se agrupan por estrategia y timestamp.

Los crates de worklist de metadata también se agrupan por propósito y timestamp.

### Rekordbox, Traktor y VirtualDJ

Para targets que no son Serato, XfinAudio escribe archivos XML estándar en el formato esperado por cada plataforma:

- **Rekordbox**: XML `DJ_PLAYLISTS` 1.0.0 con metadata de tracks (Título, Artista, BPM, Key, Energía, Género).
- **Traktor**: NML v19 XML con entradas de colección y nodos de playlist.
- **VirtualDJ**: XML `VirtualFolder` con entradas `song` usando formato `artist - title`.

Estas exportaciones siguen la misma convención de agrupación por estrategia, timestamp y no destructiva que los crates Serato. El DJ selecciona el software objetivo desde un dropdown en la pantalla de export.

## Estado del proyecto

- **Autor y mantenedor:** [Freddy Molina](https://github.com/FmBlueSystem) — [BlueSystem.io](https://bluesystem.io), División de Audio.
- Licencia: open source bajo GPL-3.0-only. Ver `LICENSE` y `docs/open-source-license.md`.
- Modelo de distribución: XfinAudio se distribuye como paquete Python instalable (source/wheel). El usuario instala con `pip`, `pipx` o `uv tool`; el resolver descarga PySide6 y mutagen desde PyPI bajo sus propias licencias.
- **Bundle .app para macOS**: Se incluye un spec de PyInstaller bajo `packaging/pyinstaller/` para construir un bundle `.app` local. El bundle incluye plugins de Qt Multimedia y librerías FFmpeg para audio preview. Los bundles no firmados sirven para uso personal; la distribución firmada/notarizada requiere Apple Developer ID y revisión legal separada.
- **Suite de tests**: 734 tests, todos pasando. Se aplica TDD estricto para todos los cambios.
- Plataforma: validado en macOS con Python 3.11. Las dependencias son cross-platform, pero Linux y Windows todavía no están validados.
- Checklist de publicación: seguir `docs/repository-publication-checklist.md` antes de convertir un árbol local en repo público.

## Postura de seguridad y no-objetivos

XfinAudio es intencionalmente no destructivo:

- No modifica archivos de audio.
- No renderiza, mezcla, time-stretchea, pitch-shiftea ni analiza waveforms.
- No hace key detection, BPM detection, beat tracking ni cue/phrase detection.
- No modifica live Serato database V2 files.
- La app solo escribe en su base, settings y archivos de export propios.
- Los Serato crate writes pasan únicamente por el explicit safe export/backup/validation flow documentado.

No-objetivos:

- Reemplazar Serato DJ Pro.
- Reemplazar Mixed In Key.
- Reemplazar el oído o experiencia del DJ.
- Auto-generar un set final sin revisión.
- Editar archivos de audio.
- Publicar un binario macOS firmado antes de completar signing, notarization, revisión de licencias y QA manual.

## Instalación

XfinAudio se distribuye como paquete Python, no como binario firmado. Se puede instalar como herramienta aislada desde el repositorio:

```bash
uv tool install git+https://github.com/FmBlueSystem/XfinAudio.git
# o
pipx install git+https://github.com/FmBlueSystem/XfinAudio.git
```

Luego lanzar la app:

```bash
xfinaudio
```

### Construir un bundle .app para macOS (opcional)

Para uso personal o pruebas, puedes construir un bundle `.app` local con PyInstaller:

```bash
uv run python -m PyInstaller packaging/pyinstaller/xfinaudio.spec \
  --clean --noconfirm \
  --distpath packaging/pyinstaller/dist \
  --workpath packaging/pyinstaller/build
```

El resultado en `packaging/pyinstaller/dist/XfinAudio.app` se puede lanzar con:

```bash
open packaging/pyinstaller/dist/XfinAudio.app
```

> **Nota:** Los bundles `.app` no firmados pueden mostrar una advertencia de seguridad al primer lanzamiento. Ve a **Ajustes del Sistema → Privacidad y Seguridad** y haz click en **Abrir de todas formas**.

Publicar el paquete en PyPI para permitir `pipx install xfinaudio` es un paso posterior opcional que requiere cuenta y API token de PyPI; no requiere cambios de código.

## Inicio rápido para desarrollo

Requisitos: Python 3.11 y `uv`.

```bash
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Lanzar la app local para QA manual:

```bash
uv run xfinaudio
```

Actualizar traducciones después de agregar nuevas cadenas traducibles:

```bash
uv run python scripts/update_translations.py
uv run python scripts/fill_spanish_translations.py
```

## Compuertas de release

Antes de afirmar cualquier release, ejecutar gates automáticos y registrar gates manuales según `docs/release-readiness-smoke.md`:

```bash
uv run python scripts/release_gate_check.py --run
uv run python scripts/smoke_release_readiness.py
```

Manual desktop QA sigue siendo obligatorio para flujos reales de usuario. La redistribución como `.app`/DMG firmado para macOS requiere Apple Developer ID, notarization y revisión legal separada.

## Marcas registradas

XfinAudio es un proyecto independiente y no está afiliado, respaldado ni patrocinado por ninguna empresa de terceros cuyos productos o marcas se mencionan.

- **Mixed In Key** es una marca de Mixed In Key LLC.
- **Serato**, **Serato DJ Pro** y marcas relacionadas son marcas comerciales o marcas registradas de Serato Limited.
- **Camelot**, **Camelot Wheel** y **Camelot System** son marcas de Mixed In Key LLC.
- **Open Key Notation** es un estándar abierto.

Todas las demás marcas comerciales, nombres comerciales y logotipos mencionados son propiedad de sus respectivos dueños.

## Licencia y dependencias

El código fuente se distribuye bajo GPL-3.0-only. La redistribución debe cumplir GPLv3 y obligaciones de dependencias de terceros.

No legal advice or legal clearance is implied by this repository documentation. La redistribución binaria/app bundle requiere revisión legal para PySide6/Qt, mutagen y otras dependencias. Ver `NOTICE.md`, `docs/open-source-license.md` y `docs/third-party-license-inventory.md`.
