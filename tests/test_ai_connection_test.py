"""The probe message is a literal shared with the Electron shell.

The connection probe used to be driven by a Qt dialog state machine in
``xfinaudio.ai.connection_test`` that turned transport failures into safe user
messages. The Qt desktop was removed in ``4e31a3a``; the live probe now runs in
``xfinaudio.headless.ai_execution`` on top of the same ``nan_client`` transport.
Only the synthetic message survived, because the Electron security layer
whitelists that exact string for the ``connection`` surface. A retired second
implementation would drift from it, so the module is guarded as a single
constant plus the two literals it has to match.
"""

from __future__ import annotations

from pathlib import Path

from xfinaudio.ai import connection_test

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDERER_REQUEST = PROJECT_ROOT / "desktop-electron" / "renderer" / "optional-ai.ts"
ELECTRON_SECURITY = PROJECT_ROOT / "desktop-electron" / "src" / "security.ts"
HEADLESS_EXECUTION = PROJECT_ROOT / "src" / "xfinaudio" / "headless" / "ai_execution.py"
EXPECTED_PROBE_MESSAGE = "Reply with OK. XfinAudio connection test."


def test_the_retired_qt_connection_dialog_surface_is_gone() -> None:
    """The dialog helpers have no caller, so a leftover copy would be dead code."""
    for name in ("ConnectionStatus", "endpoint_label", "configuration_status", "run_connection_test"):
        assert not hasattr(connection_test, name), f"{name} belongs to the removed Qt dialog"


def test_probe_message_is_the_literal_the_electron_shell_whitelists() -> None:
    assert connection_test.PROBE_MESSAGE == EXPECTED_PROBE_MESSAGE
    quoted = f"'{EXPECTED_PROBE_MESSAGE}'"
    assert quoted in RENDERER_REQUEST.read_text(encoding="utf-8")
    assert quoted in ELECTRON_SECURITY.read_text(encoding="utf-8")


def test_the_live_headless_probe_imports_this_constant_instead_of_copying_it() -> None:
    execution = HEADLESS_EXECUTION.read_text(encoding="utf-8")

    assert "from xfinaudio.ai.connection_test import PROBE_MESSAGE" in execution
    assert "nan_client.chat(PROBE_MESSAGE" in execution
    assert EXPECTED_PROBE_MESSAGE not in execution, "the probe text must have one definition"
