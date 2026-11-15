"""Shared test setup."""

from __future__ import annotations

import pytest

from xfinaudio.headless import serato_export


@pytest.fixture(autouse=True)
def _serato_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exports never depend on whether Serato DJ happens to run on the test machine (S13)."""
    monkeypatch.setattr(serato_export, "serato_is_running", lambda: False)
