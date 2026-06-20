# Design

## Architecture

Add `xfinaudio.application.dj_readiness` as a thin application boundary around the existing quality-layer readiness builder. The application use case owns orchestration of inputs and optional Serato context. The quality layer keeps the business rules and data models.

`xfinaudio.desktop.dj_readiness_controller.DjReadinessController` will accept a readiness-builder callable with a default of the application use case. This keeps production wiring simple while making tests prove that desktop delegates instead of constructing readiness directly.

## Affected Files
- `src/xfinaudio/application/dj_readiness.py` — new application use case.
- `src/xfinaudio/application/__init__.py` — lazy export for the new boundary.
- `src/xfinaudio/desktop/dj_readiness_controller.py` — delegate through application callable.
- `tests/test_application_dj_readiness.py` — application use case tests.
- `tests/test_dj_readiness_controller.py` — desktop delegation test.

## Safety
- No audio files are read or mutated.
- No Serato DB V2 writes are introduced.
- Existing Serato crate validation remains optional and read-only at this boundary.

## Review Budget
Expected change is below 400 changed lines; no chained PR is required.
