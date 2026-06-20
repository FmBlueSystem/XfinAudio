"""Legacy layout compatibility shims for :class:`~xfinaudio.desktop.main_window.MainWindow`."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

LEGACY_LAYOUT_METHODS = {}


def install_legacy_layout_methods(namespace: MutableMapping[str, Any] | type[Any]) -> None:
    """Install legacy layout methods on ``namespace``.

    The layout graft map is intentionally empty after the explicit shell-method
    migration. Keep this stable no-op until the final removal slice can delete
    the compatibility module and its import safely.
    """

    for name, method in LEGACY_LAYOUT_METHODS.items():
        if isinstance(namespace, MutableMapping):
            namespace.setdefault(name, method)
        elif not hasattr(namespace, name):
            setattr(namespace, name, method)
