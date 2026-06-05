# UI Empty States and Warning Clarity

Date: 2026-06-03

## Scope

This product-polish pass improves the desktop MVP guidance around the scan, recommendation, and safe export review flow.

Implemented:

- Initial empty-state labels in `MainWindow` for choosing a Mixed In Key processed folder, scanning before recommending, and reviewing recommendations before export.
- Guidance updates after folder selection, successful scan, and successful recommendation.
- A pure `format_recommendation_warning()` helper that converts raw recommendation warnings into desktop-friendly review text.
- Recommendation table warning cells now display formatted warning text while preserving raw domain warnings in `last_playlist_explanation`.

## Out of scope

This change does not add recommendation algorithms, DSP, audio analysis, audio rendering, audio mutation, export workflow implementation in desktop, or live Serato writes.

## Verification

Focused RED evidence before implementation:

```text
uv run pytest -v tests/test_main_window.py
5 failed, 4 passed
```

Focused GREEN evidence after implementation:

```text
uv run pytest -v tests/test_main_window.py
9 passed
```

Full-suite and lint evidence are recorded in `docs/release-candidate-evidence.md`.
