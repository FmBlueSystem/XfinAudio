# Feature: v2 Visual Celebration — integral refresh + 2 UX gaps

## Goal

Celebrate version 2.0.0 with a comprehensive visual refresh of the desktop UI,
plus two UX gaps surfaced during use: the missing AI section in Settings (the
error message promises a UI that does not exist) and the absence of a playback
stop control outside the Library tab.

## Context

- Branch `feat/v2-visual-celebration` from `main@5ca3433` (version bump 2.0.0).
- Scout map (2026-09-28 session): central theme = `_DJ_VISUAL_STYLESHEET`
  (theme.py:38-217, 26 rules, "Spectrum" palette from v1.8.3).
- `tests/test_theme_dark_mode.py` pins 15 literal palette hex tokens + WCAG AA
  ratios + gradient/hover/focus/selection structure. Any palette change must
  update theme.py + test + THEME-NOTES.md in the same commit.
- Also pinned: `test_main_window.py:2116-2117` (`#2ce8f5`, `#ffb000`),
  `:2134` (exact selector string `QPushButton#seratoExportButton:disabled`),
  `:2383-2389` + `:2841` (status cell colors), `test_table_populators.py`,
  `test_library_screen_preview.py:155` (`#5a4be0`).
- User config already flipped: `~/.xfinaudio/settings.json`
  `ai.enabled=true`, `ai.env_file=/Users/freddymolina/Desktop/XfinAudio/apiIA.env`.

## Tasks

1. [x] T1 palette v2: DONE — commit c98aadd "Aurora" renewal; values-only in
       _DJ_VISUAL_STYLESHEET + dependent pinned tokens (test_theme_dark_mode
       _PALETTE, test_main_window accent, test_library_screen_preview highlight,
       library_screen_rendering row colors) + THEME-NOTES v2 section. Contrast
       all >= 4.5:1; 146 targeted tests green; pyright/ruff clean.
2. [x] T2 theme coverage for native-fallback widgets. DONE — commit on
       feat/v2-visual-celebration: +287 lines of additive rules in theme.py
       (QProgressBar, QScrollBar, QCheckBox, QSpinBox/QDoubleSpinBox, QSlider,
       QGroupBox, QMenu/QMenuBar, QToolBar, QComboBox popup, generic
       QListWidget/QListView, QPushButton:checked, sort indicators); chip
       inline style removed from library_screen_builder.py; test_r6 pins
       coverage. 213 targeted tests green; pyright/ruff clean.
3. [ ] T3 orphaned objectNames get real styles: readinessBadge (color states
       ready/needs_review/blocked), ai_narrate_button, ai_narrative_label,
       ai_narrate_status, copilot_ask_input/button/status, loudnessDetailPane/
       loudnessDetail/truePeakBadge, songSearch.
4. [ ] T4 single source of color truth: remove build_screen.py duplicate
       _READINESS_STATUS_* (import from theme.py), delete dead constants
       (theme.py:5, library_screen.py:22-24, review_screen.py:82-87), replace
       rogue #ff4444 (live_assistant_screen.py:64) and #061016 literals with
       theme tokens; route table_populators/library_screen_rendering status
       cell colors through shared constants.
5. [ ] T5 unified table presentation: extend visual_design.py table treatment
       (no gridlines, word-wrap off, 24px rows, hidden vertical header,
       alternating colors) to the 7 uncovered tables; fix export history
       min200-vs-max92 contradiction; playlist_editor zebra rows.
6. [ ] T6 spacing/layout unification: shared margins/spacing constants
       replacing 7 copies of (12,12,12,12)+spacing 8; live_assistant odd
       margins; fix stale "Version 1.0" style guidance-copy drift only where
       visual (5 copies of _RECOMMENDATION_READY_GUIDANCE stays out of scope).
7. [ ] T7 v2 celebration surfaces: window title "XfinAudio 2.0", About dialog
       reads real version (importlib.metadata, fallback to 2.0.0), status-bar
       version pill with the v2 warm-accent touch.
8. [ ] T8 Settings dialog AI section: enable-AI checkbox + env-file picker
       persisting into AiSettings; make the "Enable AI in Settings" error
       message true. Restart applies via seed_ai_environment (document in
       dialog).
9. [ ] T9 playback stop anywhere: stop button in the status_controls row (or
       equivalent always-visible surface) wired to _audio_player.stop();
       visible only while a source is loaded/playing.
10. [ ] T10 close-out: full suite `uv run pytest -q`, pyright, ruff; update
        THEME-NOTES.md with the v2 palette table; verify no regression in
        pinned visual tests; record evidence in this ledger.

## Evidence

- c98aadd feat(desktop): Aurora palette renewal for the v2 celebration (T1)
- 84b726d feat(desktop): theme coverage for all native-fallback widgets (T2)
