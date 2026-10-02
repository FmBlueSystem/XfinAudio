# Design

Reuse application.strategy_catalog and recommendation.prep_copilot.DJSetIntent/build_prep_copilot_plan, with the existing application candidate-planning seams and bound colour anchor. Renderer receives only opaque track IDs; backend resolves them against the authorized current library. Retain the current plan under a UUID; prep.select validates plan identity and variant name, creates a current review ID, and leaves save explicit. All generation remains one cancellable job over the existing JSONL bridge. IPC schema mirrors backend bounds and denies extra fields.

Backend owns headless prep helpers/backend dispatch and new Python tests. Renderer owns renderer files and controller tests. Host main/preload/security are integrated separately. Existing Qt code and domain algorithms are unchanged unless a narrowly justified neutral extraction is independently specified.
