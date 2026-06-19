"""Legacy desktop shell compatibility facade.

Keep this module as a temporary compatibility import surface while the desktop
shell cleanup continues. New cleanup work should prefer the narrower modules:
`shell_layout_compat` for layout method grafting and `shell_state_compat` for
legacy MainWindow AppState read/write compatibility.
"""

from __future__ import annotations

from xfinaudio.desktop.shell_layout_compat import LEGACY_LAYOUT_METHODS, install_legacy_layout_methods
from xfinaudio.desktop.shell_state_compat import (
    LEGACY_APP_STATE_WRITE_ATTRIBUTES,
    is_missing_legacy_attribute,
    try_get_legacy_app_state_attribute,
    try_set_legacy_app_state_attribute,
)

__all__ = [
    "LEGACY_APP_STATE_WRITE_ATTRIBUTES",
    "LEGACY_LAYOUT_METHODS",
    "install_legacy_layout_methods",
    "is_missing_legacy_attribute",
    "try_get_legacy_app_state_attribute",
    "try_set_legacy_app_state_attribute",
]
