# Prep Copilot Generation Application Boundary Design

Extend `xfinaudio.application.prep_copilot` with a generation request and `generate_prep_copilot_plan(...)`.
The request contains primitive/UI-derived values; the application constructs `DJSetIntent` and calls the recommendation planner.
`PrepCopilotController.generate()` keeps UI validation/input collection and state rendering, but delegates plan creation through an injectable generation builder.
