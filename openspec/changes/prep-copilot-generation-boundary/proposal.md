# Prep Copilot Generation Application Boundary

Move Prep Copilot plan generation behind an application use case so desktop collects UI input but does not construct domain intents or call recommendation planning directly.

In scope: application generation request/result, desktop delegation, focused tests, SDD evidence.
Out of scope: selected variant application, algorithm changes, DSP/audio mutation, export formats, live Serato DB V2 writes.

Success: `desktop.prep_copilot` no longer imports `DJSetIntent` or `build_prep_copilot_plan`; behavior and UI rendering remain unchanged; full gates pass.
