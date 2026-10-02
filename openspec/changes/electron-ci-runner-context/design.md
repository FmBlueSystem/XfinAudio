# Design

Use step-level env for the existing XFIN_PYTHON runner-temp expression. Installation already uses runner.temp in a run step, where the context is permitted. Do not change dependency versions, gate commands, event triggers, permissions or test-selection policy. Add a regression for the configuration boundary. Reference: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts#context-availability .
