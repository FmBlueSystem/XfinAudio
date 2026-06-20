# Design

## Architecture

Add `xfinaudio.application.prep_copilot` as a use-case boundary for applying a selected Prep Copilot variant. The use case composes existing explanation and quality-report builders and preserves the readiness report already attached to the variant.

`xfinaudio.desktop.prep_copilot.PrepCopilotController` will accept an injectable application callable with a default of this use case. The controller remains responsible for selection validation, state replacement, and UI rendering only.

## Affected Files
- `src/xfinaudio/application/prep_copilot.py` — new application use case and result model.
- `src/xfinaudio/application/__init__.py` — lazy exports.
- `src/xfinaudio/desktop/prep_copilot.py` — delegate variant application.
- `tests/test_application_prep_copilot.py` — application use-case tests.
- `tests/test_prep_copilot_controller.py` — desktop delegation tests.

## Safety
- No audio files are read or mutated.
- No DSP scope is added.
- No Serato DB V2 writes are introduced.

## Review Budget
Expected change is below 400 changed lines; no chained PR is required.
