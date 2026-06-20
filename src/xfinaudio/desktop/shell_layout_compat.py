"""Legacy desktop layout method compatibility surface."""

from __future__ import annotations

from xfinaudio.desktop import layout as _layout

LEGACY_LAYOUT_METHODS = {
    "_start_spectral_completion_worker": _layout.start_main_spectral_completion_worker,
    "_cancel_spectral_completion_worker": _layout.cancel_main_spectral_completion_worker,
    "_on_spectral_progress_updated": _layout.on_main_spectral_progress_updated,
    "_on_spectral_profile_ready": _layout.on_main_spectral_profile_ready,
    "_on_spectral_completion_finished": _layout.on_main_spectral_completion_finished,
}


def install_legacy_layout_methods(target_class: type) -> None:
    """Install legacy layout-backed methods on a MainWindow-compatible class."""
    for name, method in LEGACY_LAYOUT_METHODS.items():
        setattr(target_class, name, method)
