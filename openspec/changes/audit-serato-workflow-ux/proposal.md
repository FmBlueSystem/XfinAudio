# Audit: visible Serato preparation workflow

## Intent and scope
Repair confirmed fresh-session preparation, precision, metadata and compact-layout defects from the 2026-09-30 audit. Fix shared application assets so Spanish catalogs and the icon resolve in source, wheel and frozen layouts. Shared core UX and Serato only; no changes to other export destinations, DSP, loudness behavior, audio metadata or live Serato databases.

## Success and rollback
A fresh generated plan exposes its Apply action; prerequisites and pool explanations are visible; fractional BPM survives display; metadata opens on incomplete tracks; compact screens remain usable; real Spanish catalogs load. Revert individual slice commits to roll back.

## Delivery / review budget
The combined change exceeds 400 changed lines. Explicit chained-PR plan (local commits only; no PR/push authorized):
1. A: render-safe variant application and inline selected-variant reasons
2. B: source/installed/frozen asset resolver and package data
3. C: shared BPM display and actionable metadata defaults
4. D: generation prerequisites and direct library/metadata next step
5. E: compact layouts and narrow Color column regression
Each slice includes its focused tests and evidence. Parent runs the exact integrated release gate. Native macOS, VoiceOver and real Serato import remain separate validation.

## Risks
Changing defaults affects existing screen tests; retain explicit All selection and stable selection on rerender. Asset paths must preserve current frozen packaging mapping. Geometry evidence is offscreen Linux only.
