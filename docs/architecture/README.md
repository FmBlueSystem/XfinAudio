# Architecture Notes — Reading Guide

This directory holds the architecture notes written for the **XfinAudio 2.2.0 Qt
desktop**. That desktop was removed in `4e31a3a`
(`refactor(project)!: remove Qt legacy desktop and PySide6 dependency`), so every
note here is a **historical record** of the tree it describes, not an instruction
for the current one. Each note says so in a banner and names that commit.

## Where the live shape is documented

- **Core (Python)**: `src/xfinaudio/` — `library/` (scanning and read-only
  repository), `recommendation/` (strategies, variants, optimizer),
  `quality/` (DJ readiness), `exporting/` (playlist files and Serato crates),
  `metadata/`, `audio/` (loudness) and `headless/` (`xfinaudio.headless`, the
  JSON-lines server the desktop shell drives).
- **Desktop shell**: `desktop-electron/` (Electron + strict TypeScript). Its
  source guide is `desktop-electron/README.md`.
- **Runtime contracts**: `docs/architecture/layered-architecture.md` still
  explains the layering intent (presentation, application/use cases, domain,
  ports, infrastructure), which the current split keeps: the Electron renderer
  is presentation, `headless/` and `application/` carry use cases, and the domain
  packages above own product rules.

## Notes in this directory

- `functional-inventory.md` — feature-to-module inventory and boundary rules
  (historical: written against `xfinaudio.desktop` and the PySide6 screens).
- `layered-architecture.md` — layer map and the reviewable slices it proposed
  (historical: the presentation layer it maps is the removed Qt desktop).
- `responsibility-separation-operating-instruction.md` — record of the
  responsibility-separation chain and its follow-up path (historical: it names
  `xfinaudio.desktop` transition helpers and `AppState`).
- `shell-layout-compat-elimination-plan.md` — the plan that eliminated
  `shell_layout_compat.py` (historical: that module and its graft map were
  removed with the Qt desktop in `4e31a3a`).

Do not follow the code paths in these notes; follow the packages listed above and
the SDD records under `openspec/changes/`.
