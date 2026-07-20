"""Tests for recommendation service state-boundary behavior."""

from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from typing import Any, cast

from xfinaudio.desktop.app_state import AppState
from xfinaudio.desktop.recommendation_service import RecommendationService


class _Label:
    def __init__(self) -> None:
        self.text = ""

    def setText(self, text: str) -> None:  # noqa: N802 - Qt-compatible test double
        self.text = text


class _Button:
    def setEnabled(self, _enabled: bool) -> None:  # noqa: N802 - Qt-compatible test double
        pass


class _StrategyCombo:
    """Test double mirroring the data-backed QComboBox contract (text=display, data=internal)."""

    def __init__(self, items: list[tuple[str, str]], current_index: int = 0) -> None:
        self._items = items
        self._current_index = current_index
        self.find_text_calls: list[str] = []
        self.find_data_calls: list[str] = []

    def currentText(self) -> str:  # noqa: N802 - Qt-compatible test double
        return self._items[self._current_index][0]

    def currentData(self) -> str:  # noqa: N802 - Qt-compatible test double
        return self._items[self._current_index][1]

    def findText(self, text: str) -> int:  # noqa: N802 - Qt-compatible test double
        self.find_text_calls.append(text)
        for index, (item_text, _item_data) in enumerate(self._items):
            if item_text == text:
                return index
        return -1

    def findData(self, data: str) -> int:  # noqa: N802 - Qt-compatible test double
        self.find_data_calls.append(data)
        for index, (_item_text, item_data) in enumerate(self._items):
            if item_data == data:
                return index
        return -1

    def setCurrentIndex(self, index: int) -> None:  # noqa: N802 - Qt-compatible test double
        self._current_index = index


def _result() -> SimpleNamespace:
    return SimpleNamespace(
        recommendation=SimpleNamespace(ordered_tracks=[], strategy=SimpleNamespace(name="Test")),
        explanation=SimpleNamespace(transitions=[]),
        quality_report=SimpleNamespace(average_transition_score=0.0, warning_count=0),
    )


def _wire_service(
    service: RecommendationService,
    *,
    state: Callable[[], AppState] = AppState,
    set_state: Callable[[AppState], None] = lambda _state: None,
    set_applied_copilot_variant: Callable[[str | None], None] = lambda _variant: None,
    build_screen: Any | None = None,
) -> None:
    service.set_state_accessors(
        scanned_records=list,
        set_is_recommending=lambda _value: None,
        state=state,
        set_state=set_state,
    )
    service.set_ui(
        build_screen=build_screen if build_screen is not None else SimpleNamespace(recommend_button=_Button()),
        review_screen=SimpleNamespace(review_summary_label=_Label()),
        export_screen=SimpleNamespace(export_guidance_label=_Label()),
        library_screen=SimpleNamespace(scan_button=_Button()),
        status_label=_Label(),
        recommendation_guidance_label=_Label(),
        tr=lambda text: text,
    )
    service.set_actions(
        sync_state=lambda: None,
        clear_recommendation_review=lambda: None,
        show_recommendation=lambda *_args: None,
        show_transition_review=lambda _explanation: None,
        selected_track_controls=lambda: None,
        desktop_recommendation_records=lambda _controls, _strategy=None: [],
        set_recommendation_sections_expanded=lambda _expanded: None,
        set_applied_copilot_variant=set_applied_copilot_variant,
        show_dj_readiness=lambda *_args: None,
        refresh_idle_action_state=lambda: None,
    )


def test_on_completed_applies_transition_to_current_app_state() -> None:
    service = RecommendationService(cast(Any, object()))
    current_state = AppState(playlist_removed_paths=frozenset({"/current.flac"}), applied_variant_name="balanced")
    captured_states: list[AppState] = []
    _wire_service(service, state=lambda: current_state, set_state=captured_states.append)

    result = _result()
    service.on_completed(result)

    assert captured_states
    assert captured_states[-1] is not current_state
    assert captured_states[-1].last_recommendation is result.recommendation
    assert current_state.last_recommendation is None


def test_replace_app_state_does_not_break_recommendation_completion_accessor() -> None:
    from xfinaudio.desktop.window_factory import replace_app_state

    service = RecommendationService(cast(Any, object()))
    window = SimpleNamespace(_state=AppState(), _recommendation_service=service)
    _wire_service(service, state=lambda: window._state, set_state=lambda state: replace_app_state(window, state))
    replacement = AppState(playlist_removed_paths=frozenset({"/after-replace.flac"}), applied_variant_name="safe")

    result = _result()
    replace_app_state(window, replacement)
    service.on_completed(result)

    assert window._state is not replacement
    assert window._state.last_recommendation is result.recommendation
    assert window._state.playlist_removed_paths == frozenset()
    assert window._state.applied_variant_name is None


def test_on_completed_clears_applied_copilot_variant_badge_callback() -> None:
    service = RecommendationService(cast(Any, object()))
    cleared_variants: list[str | None] = []
    _wire_service(service, set_applied_copilot_variant=cleared_variants.append)

    service.on_completed(_result())

    assert cleared_variants == [None]


def test_replace_app_state_refreshes_library_controller_state() -> None:
    from xfinaudio.desktop.window_factory import replace_app_state

    original = AppState(scanned_records=[])
    replacement = AppState(scanned_records=[cast(Any, object())])
    library_controller = SimpleNamespace(_state=original)
    window = SimpleNamespace(_state=original, _library_controller=library_controller)

    replace_app_state(window, replacement)

    assert library_controller._state is replacement


def test_recommend_reads_strategy_via_current_data() -> None:
    """`recommend()` reads the strategy name from `currentData()`, not `currentText()`.

    Spec `strategy-selection-ux` -> "Downstream Consumers Keep Working".
    """
    service = RecommendationService(cast(Any, object()))
    combo = _StrategyCombo([("Same Color & Energy", "same_color_energy")])
    build_screen = SimpleNamespace(
        recommend_button=_Button(),
        strategy_combo=combo,
        spectral_cohesion_value=lambda: 50,
    )
    _wire_service(service, build_screen=build_screen)
    service._scanned_records = lambda: [cast(Any, object())]
    service._selected_track_controls = lambda: cast(Any, object())
    captured_strategies: list[str] = []

    def _fake_desktop_recommendation_records(_controls: Any, _strategy: str | None = None) -> list[Any]:
        assert _strategy is not None
        captured_strategies.append(_strategy)
        return []

    service._desktop_recommendation_records = _fake_desktop_recommendation_records
    started_strategies: list[str] = []

    def _fake_start_recommendation(
        _records: list[Any], strategy_name: str, controls: Any = None, spectral_cohesion: float = 0.0
    ) -> None:
        started_strategies.append(strategy_name)

    service.start_recommendation = _fake_start_recommendation

    service.recommend()

    assert captured_strategies == ["same_color_energy"]
    assert started_strategies == ["same_color_energy"]
    assert combo.currentText() != "same_color_energy"


def test_on_recommend_requested_selects_item_via_find_data() -> None:
    """`on_recommend_requested` locates the combo item via `findData`, not `findText`.

    Spec `strategy-selection-ux` -> "Downstream Consumers Keep Working".
    """
    service = RecommendationService(cast(Any, object()))
    combo = _StrategyCombo(
        [("Same Color", "same_color"), ("Same Color & Energy", "same_color_energy")],
        current_index=0,
    )
    build_screen = SimpleNamespace(
        recommend_button=_Button(),
        strategy_combo=combo,
        spectral_cohesion_value=lambda: 50,
    )
    _wire_service(service, build_screen=build_screen)
    service._scanned_records = lambda: [cast(Any, object())]
    service._selected_track_controls = lambda: cast(Any, object())
    service._desktop_recommendation_records = lambda _controls, _strategy=None: []
    service.start_recommendation = lambda *_args, **_kwargs: None

    service.on_recommend_requested("same_color_energy", [])

    assert combo.find_data_calls == ["same_color_energy"]
    assert combo.find_text_calls == []
    assert combo.currentData() == "same_color_energy"
