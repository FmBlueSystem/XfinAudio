"""Non-secret bridge between saved preferences and the existing AI adapter."""

from __future__ import annotations

import os
from pathlib import Path

from xfinaudio.ai.nan_client import ENABLED_ENV, ENV_FILE_ENV, is_ai_enabled
from xfinaudio.config.settings import AiSettings


def effective_ai_settings(settings: AiSettings) -> AiSettings:
    """Reflect explicit launcher overrides without reading any credential file."""
    override = os.environ.get(ENV_FILE_ENV, "").strip()
    return settings.model_copy(
        update={
            "enabled": is_ai_enabled() if ENABLED_ENV in os.environ else settings.enabled,
            "env_file": Path(override).expanduser() if override else settings.env_file,
        }
    )


def apply_ai_settings(settings: AiSettings) -> None:
    """Apply an explicitly saved preference to subsequent requests immediately.

    Startup still honors launcher overrides. Saving the dialog is an explicit
    user choice and replaces the runtime switches, including stale file paths.
    This never reads, writes or changes an API key.
    """
    os.environ[ENABLED_ENV] = "1" if settings.enabled else "0"
    if settings.env_file is None:
        os.environ.pop(ENV_FILE_ENV, None)
    else:
        os.environ[ENV_FILE_ENV] = str(settings.env_file)
