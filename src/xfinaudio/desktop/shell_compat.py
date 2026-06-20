"""Legacy desktop shell compatibility facade.

Keep this module as a temporary compatibility import surface for legacy
MainWindow AppState read/write compatibility while the desktop shell cleanup
continues.
"""

from __future__ import annotations

from xfinaudio.desktop.shell_state_compat import (
    LEGACY_APP_STATE_WRITE_ATTRIBUTES,
    is_missing_legacy_attribute,
    try_get_legacy_app_state_attribute,
    try_set_legacy_app_state_attribute,
)

__all__ = [
    "LEGACY_APP_STATE_WRITE_ATTRIBUTES",
    "is_missing_legacy_attribute",
    "try_get_legacy_app_state_attribute",
    "try_set_legacy_app_state_attribute",
]
