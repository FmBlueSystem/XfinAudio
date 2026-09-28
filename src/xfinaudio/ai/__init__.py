"""AI adapter surface for XfinAudio (Fase 0: Nan Builders spike).

Import the client from here so later phases (copilot, explainability, batch
tagging) depend on one narrow surface instead of reaching into the module.
"""

from __future__ import annotations

from xfinaudio.ai.intent_copilot import extract_intent
from xfinaudio.ai.nan_client import (
    NanConfigError,
    NanRequestError,
    chat,
    default_env_file_path,
    is_ai_enabled,
    load_api_key_from_env_file,
)
from xfinaudio.ai.set_narrator import narrate_set

__all__ = [
    "NanConfigError",
    "NanRequestError",
    "chat",
    "default_env_file_path",
    "extract_intent",
    "is_ai_enabled",
    "load_api_key_from_env_file",
    "narrate_set",
]
