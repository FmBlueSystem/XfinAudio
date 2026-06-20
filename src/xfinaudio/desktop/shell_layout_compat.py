"""Legacy desktop layout method compatibility surface."""

from __future__ import annotations

from xfinaudio.desktop import layout as _layout

LEGACY_LAYOUT_METHODS = {
    "generate_prep_copilot": _layout.generate_prep_copilot,
    "_apply_prep_copilot_item": _layout.apply_prep_copilot_item,
    "apply_selected_prep_copilot_variant": _layout.apply_selected_prep_copilot_variant,
    "recommend_playlist": _layout.recommend_playlist,
    "_begin_recommendation_state": _layout.begin_main_recommendation_state,
    "_end_recommendation_state": _layout.end_main_recommendation_state,
    "_start_recommendation_worker": _layout.start_main_recommendation_worker,
    "_finish_recommendation": _layout.finish_main_recommendation,
    "_fail_recommendation": _layout.fail_main_recommendation,
    "_populate_dj_readiness_table": _layout.populate_main_dj_readiness_table,
    "_on_recommend_requested": _layout.on_main_recommend_requested,
    "_on_copilot_variant_applied": _layout.on_main_copilot_variant_applied,
    "_selected_metadata_status_filter": _layout.selected_main_metadata_status_filter,
    "_selected_missing_metadata_filter": _layout.selected_main_missing_metadata_filter,
    "_metadata_status_records": _layout.metadata_main_status_records,
    "_metadata_missing_field_records": _layout.metadata_main_missing_field_records,
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
