# Verify Report: Scan entry shell methods explicit

Status: passed

## Requirement: Scan entry shell methods are explicit MainWindow methods

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py::test_scan_entry_shell_methods_are_explicit_main_window_methods -q
```

Result: `1 passed`.

## Requirement: Scan behavior remains delegated

Evidence:

```bash
uv run pytest tests/test_main_window_shell_compat.py tests/test_main_window.py tests/test_visual_integration.py -q
```

Result: `140 passed, 33 warnings`.

## Requirement: Remaining legacy layout grafting stays stable

Evidence:

```bash
uv run pytest -q
uv run pyright src tests
uv run pytest --cov --cov-fail-under=70 -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/release_gate_check.py --run
```

Result:
- `929 passed, 42 warnings`
- `0 errors, 0 warnings, 0 informations`
- `929 passed`, coverage `90.17%`
- `All checks passed!`
- `219 files already formatted`
- Release gate passed, including release readiness smoke, publication docs, artifact hygiene, source package hygiene, and PyInstaller check-only.

## Legacy graft map evidence

```bash
python - <<'PY'
import ast
from pathlib import Path
mod = ast.parse(Path('src/xfinaudio/desktop/shell_layout_compat.py').read_text())
keys = []
for node in mod.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == 'LEGACY_LAYOUT_METHODS':
                keys = [ast.literal_eval(key) for key in node.value.keys]
print('remaining_legacy_layout_methods', len(keys))
print('removed scan entry present?', any(key in keys for key in ['scan_selected_folder', '_begin_scan_state', 'cancel_scan', '_clear_scan_dependent_state']))
PY
```

Result:
- `remaining_legacy_layout_methods 28`
- `removed scan entry present? False`
