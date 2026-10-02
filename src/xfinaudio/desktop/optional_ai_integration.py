"""Single MainWindow hook for explicitly opted-in, independent AI surfaces."""

from __future__ import annotations

from typing import Any

from xfinaudio.ai import structured_assists
from xfinaudio.desktop.optional_ai_assist import OptionalAssistController
from xfinaudio.desktop.optional_ai_explanations import install_explanation_controls
from xfinaudio.desktop.optional_ai_saved import install_saved_control
from xfinaudio.desktop.optional_ai_surfaces import install_library_editor_controls


def install_optional_assist_controls(
    window: Any, *, services: Any = structured_assists
) -> dict[str, OptionalAssistController]:
    controls = install_library_editor_controls(window, services=services)
    controls["saved"] = install_saved_control(window, services=services)
    controls.update(install_explanation_controls(window, services=services))
    return controls
