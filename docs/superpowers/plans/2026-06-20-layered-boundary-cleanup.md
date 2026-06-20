# Layered Boundary Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move XfinAudio toward a cleaner layered minimum by reducing mixed responsibilities in `config`, then continuing with `library`, `exporting`, and `audio` through small SDD/TDD slices.

**Architecture:** `desktop` remains presentation/adapters, `application` orchestrates use cases, domain packages keep product rules, ports define replaceable contracts, and infrastructure owns concrete filesystem/audio/settings/persistence implementations. This plan starts with `config` because it is the smallest mixed layer: settings schema and settings persistence live together.

**Tech Stack:** Python 3.11, PySide6 desktop app, Pydantic settings models, pytest, pyright, ruff, gentle-ai OpenSpec.

---

## File Structure

- `src/xfinaudio/config/settings.py` — keep pure settings models and validation.
- `src/xfinaudio/config/ports.py` — create settings persistence protocol(s), no filesystem implementation.
- `src/xfinaudio/config/settings_repository.py` — keep concrete JSON filesystem repository, implement the port structurally.
- `src/xfinaudio/desktop/app_state.py` — import `SettingsRepositoryPort` from config instead of defining settings persistence protocol in desktop.
- `src/xfinaudio/desktop/settings_controller.py` — continue depending on the app state's settings persistence, no modal behavior changes.
- `tests/test_settings_ports.py` — prove config port is importable without desktop/PySide6 and that `SettingsRepository` satisfies it structurally.
- `docs/architecture/layered-architecture.md` — update the `config` assignment after the port exists.
- `openspec/changes/layered-config-boundary/` — SDD artifacts and verification.

## Task 1: Config settings port boundary

**Files:**
- Create: `src/xfinaudio/config/ports.py`
- Create: `tests/test_settings_ports.py`
- Modify: `src/xfinaudio/desktop/app_state.py`
- Modify: `docs/architecture/layered-architecture.md`
- Modify: `openspec/changes/layered-config-boundary/*`

- [ ] **Step 1: Write the failing test**

Create `tests/test_settings_ports.py`:

```python
from __future__ import annotations

from typing import get_type_hints

from xfinaudio.config.ports import SettingsRepositoryPort
from xfinaudio.config.settings import AppSettings
from xfinaudio.config.settings_repository import SettingsRepository


def test_settings_repository_port_is_desktop_free() -> None:
    hints = get_type_hints(SettingsRepositoryPort.load)

    assert hints["return"] is AppSettings
    assert "xfinaudio.desktop" not in SettingsRepositoryPort.__module__


def test_settings_repository_satisfies_settings_port(tmp_path) -> None:
    repo: SettingsRepositoryPort = SettingsRepository(tmp_path / "settings.json")

    repo.save(AppSettings())

    assert isinstance(repo.load(), AppSettings)
```

- [ ] **Step 2: Run RED test**

Run:

```bash
uv run pytest tests/test_settings_ports.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'xfinaudio.config.ports'`.

- [ ] **Step 3: Add config port**

Create `src/xfinaudio/config/ports.py`:

```python
"""Ports for settings persistence."""

from __future__ import annotations

from typing import Protocol

from xfinaudio.config.settings import AppSettings


class SettingsRepositoryPort(Protocol):
    """Persistence boundary for application settings."""

    def load(self) -> AppSettings:
        """Load persisted settings or defaults."""

    def save(self, settings: AppSettings) -> None:
        """Persist application settings."""
```

- [ ] **Step 4: Move desktop protocol dependency to config port**

In `src/xfinaudio/desktop/app_state.py`, replace the local `SettingsPersistence` protocol with an import alias:

```python
from xfinaudio.config.ports import SettingsRepositoryPort as SettingsPersistence
```

Remove the old `Protocol` import if no longer used.

- [ ] **Step 5: Run focused test**

Run:

```bash
uv run pytest tests/test_settings_ports.py tests/test_settings_controller.py tests/test_settings_repository.py -q
```

Expected: PASS.

- [ ] **Step 6: Update architecture docs**

In `docs/architecture/layered-architecture.md`, update `config` notes from “models and concrete settings repository live together” to indicate settings port is explicit and the JSON repository remains infrastructure.

- [ ] **Step 7: Run verification**

Run:

```bash
uv run pyright src/xfinaudio/config src/xfinaudio/desktop/app_state.py tests/test_settings_ports.py
uv run ruff check src/xfinaudio/config src/xfinaudio/desktop/app_state.py tests/test_settings_ports.py
uv run ruff format --check src/xfinaudio/config src/xfinaudio/desktop/app_state.py tests/test_settings_ports.py
```

Expected: all pass.

## Future Tasks After Config Boundary

- `library`: split repository ports and concrete persistence docs/tests further only where current use cases need substitution.
- `exporting`: move writer contracts behind application-level export orchestration without changing file formats.
- `audio`: isolate analyzer execution contracts from pure spectral policy without adding DSP scope.
- `desktop`: continue shrinking orchestration only after each domain/application boundary is available.

## Algorithm Improvement Gate

After a responsibility boundary is extracted into a pure module, inspect that module for business-rule algorithms that can be improved safely. Improvements must be measurable and covered by focused unit tests before implementation. Capture the current behavior as a baseline, change only the isolated algorithm or policy, compare the behavior after the change, and verify the UI remains a consumer rather than the owner of the rule.

Eligible future targets: `recommendation`, `quality`, `exporting`, `library`, and `audio` policy modules. Do not mix algorithm changes into infrastructure-only slices such as the current config boundary. Do not add DSP scope, mutate audio, write Serato DB V2 files, or change export formats while optimizing algorithms.

## Self-Review

- Spec coverage: Task 1 covers the first smallest mixed-layer target (`config`) and preserves safety constraints.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: `SettingsRepositoryPort` uses existing `AppSettings`; `SettingsRepository` already exposes compatible `load` and `save` methods.
