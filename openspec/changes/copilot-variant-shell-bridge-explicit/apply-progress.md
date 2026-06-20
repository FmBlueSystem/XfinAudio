# Apply Progress: Copilot variant shell bridge explicit

Status: verified

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_prep_copilot_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `_on_copilot_variant_applied` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow._on_copilot_variant_applied(index)` delegating to `PrepCopilotController.on_variant_applied(index)`.
- Removed `_on_copilot_variant_applied` from `LEGACY_LAYOUT_METHODS`.
- Updated stale shell compatibility example to use the remaining spectral grafts.
- Updated architecture docs and elimination-plan progress.

Focused commands:

```bash
uv run pytest tests/test_main_window_shell_compat.py -q
# 18 passed

uv run pytest tests/test_main_window.py -q -k "prep_copilot or copilot_variant or applied_copilot_variant_badge"
# 11 passed, 100 deselected
```

The legacy layout graft map now has 5 methods, all spectral completion methods.
