# Apply Progress: Prep Copilot shell methods explicit

Status: complete

## RED

Command:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_prep_copilot_shell_methods_are_explicit_main_window_methods -q
```

Result: failed as expected because `generate_prep_copilot` was still present in `shell_layout_compat.LEGACY_LAYOUT_METHODS`.

## GREEN

Changes:
- Added explicit `MainWindow.generate_prep_copilot()` delegating to `PrepCopilotController.generate()`.
- Added explicit `MainWindow._apply_prep_copilot_item()` delegating to `PrepCopilotController.apply_item()`.
- Added explicit `MainWindow.apply_selected_prep_copilot_variant()` delegating to `PrepCopilotController.apply_selected_variant()`.
- Removed the three Prep Copilot names from `shell_layout_compat.LEGACY_LAYOUT_METHODS`.
- Updated architecture docs and elimination plan progress.

Focused commands:

```bash
uv run pytest -q tests/test_main_window_shell_compat.py -k prep
uv run pytest -q tests/test_main_window.py -k "prep_copilot"
```

Result: `1 passed, 16 deselected`; `8 passed, 103 deselected`.

The legacy layout graft map now has 14 methods, and the three Prep Copilot names are absent.


## VERIFY

Commands:

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

Result: all verification gates passed. The legacy layout graft map now has 14 methods, and the three Prep Copilot names are absent.
