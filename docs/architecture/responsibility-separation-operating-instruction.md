# Responsibility Separation Handoff

This document records the completed XfinAudio responsibility-separation chain and the safe follow-up path for future work.

## Current state

| Area | Status |
|---|---|
| Functional inventory | Present in `docs/architecture/functional-inventory.md`. |
| Recommendation boundary | Extracted into focused recommendation modules and AppState transition helpers. |
| Export boundary | Extracted into focused export planning/readiness/file-export modules. |
| AppState transition boundary | Centralized in `src/xfinaudio/desktop/app_state_transitions.py`. |
| Desktop responsibility | UI/adapters/orchestration only for the completed slices. |
| Final verified main | `2dac65c` (`refactor(state): extract library records loaded transition`). |

## Completed responsibility slices

| Boundary | Result |
|---|---|
| Recommendation completion | Completion state replacement moved into a pure AppState transition. |
| Scan recommendation reset | Scan-dependent recommendation state reset moved into a pure transition. |
| Playlist removal/restore | Removed/restored path state moved into pure transitions. |
| Prep Copilot variant | Applied variant state moved into a pure transition. |
| Track constraints | Locked/excluded track state moved into pure transitions. |
| Prep Copilot plan | Generated/cleared plan state moved into pure transitions. |
| Saved playlist export | Export recommendation replacement moved into a pure transition. |
| Library folder selection | Folder selection plus scan-context reset moved into a pure transition. |
| Library records loaded | Loaded records plus lookup-map rebuild moved into a pure transition. |

## What is intentionally left out

The remaining mutable assignments are not the same category as the completed business/state-policy seams:

| Surface | Classification |
|---|---|
| `AppController.refresh_state_fields()` | Runtime UI snapshot sync. |
| `ScanService` progress fields | Runtime scan progress/cancellation state. |
| `MainWindow.__setattr__` compatibility paths | Legacy adapter compatibility. |
| `LiveAssistantScreen` caches | Screen-local UI cache. |
| Older `layout.py` direct-state helpers | Legacy functions bypassed by controller-backed layout method mappings for the critical restore/clear paths. |

Do not keep refactoring these by inertia. Treat them as a separate runtime-state or legacy-cleanup initiative with its own proposal.

## Rules for future slices

1. Keep `xfinaudio.desktop` as UI/adapters/orchestration.
2. Move business rules, export decisions, recommendation policy, and durable state transitions into focused pure modules.
3. Add or update the failing unit test before production code.
4. Keep desktop code responsible for reading widgets, calling boundaries, rendering results, and showing errors.
5. Keep PRs under the 400-line review budget or split them into child PRs.
6. Do not mutate audio, add DSP scope, or write live Serato DB V2 files.

## Restart quick path

```bash
git status --short --branch
git rev-parse --short HEAD
git rev-parse --short origin/main
uv run python scripts/release_gate_check.py --run
```

Expected final baseline at the time of this handoff:

```text
main...origin/main
2dac65c refactor(state): extract library records loaded transition
```

## Static analysis follow-up

Use these checks before proposing another responsibility slice:

```bash
python - <<'PY'
from pathlib import Path
for path in sorted(Path('src/xfinaudio').rglob('*.py')):
    text = path.read_text(errors='ignore')
    if 'desktop' not in path.parts and 'PySide6' in text:
        print(path)
PY
```

Expected result: no output.

```bash
python - <<'PY'
from pathlib import Path
for path in sorted(Path('src/xfinaudio').rglob('*.py')):
    text = path.read_text(errors='ignore')
    if 'desktop' not in path.parts and 'xfinaudio.desktop' in text:
        print(path)
PY
```

Expected result: no output.

## Definition of done for future responsibility work

- [ ] OpenSpec artifacts exist for behavior/refactor work.
- [ ] A failing unit test is observed before production code changes.
- [ ] Pure modules own business/state policy.
- [ ] Desktop modules remain orchestration and rendering adapters.
- [ ] Focused tests pass.
- [ ] Full XfinAudio verification gate passes.
- [ ] PR is small enough for review or split into child PRs.
