from types import SimpleNamespace
from typing import Any

from tests.test_prep_copilot import spectral_track
from xfinaudio.config.settings import AppSettings, LoudnessSettings
from xfinaudio.desktop.prep_copilot import PrepCopilotController
from xfinaudio.recommendation.loudness_policy import LoudnessBand


class _Index:
    def __init__(self, row: int) -> None:
        self._row = row

    def row(self) -> int:
        return self._row


class _Table:
    def selectedIndexes(self) -> list[_Index]:
        return [_Index(0)]

    def selectRow(self, row: int) -> None:
        self.selected = row

    def rowCount(self) -> int:
        return 1


def _label() -> Any:
    return SimpleNamespace(text="", tooltip="", setText=lambda text: None, setToolTip=lambda text: None)


def _unrouted(*_args: Any, **_kwargs: Any) -> Any:
    """Candidate route that must never be reached in the test that injects it."""
    raise AssertionError("this candidate route must not be reached")


class _State:
    def __init__(self, variant: Any) -> None:
        self._state = object()
        self.last_prep_copilot_plan = SimpleNamespace(variants=[variant])
        self._review_screen = SimpleNamespace(review_summary_label=_label(), dj_readiness_label=_label())
        self._export_screen = SimpleNamespace(export_guidance_label=_label())
        self.recommendation_calls: list[Any] = []
        self.transition_calls: list[Any] = []
        self.readiness_tables: list[Any] = []

    def tr(self, text: str) -> str:
        return text

    def _replace_app_state(self, updated_state: Any) -> None:
        self._state = updated_state

    def show_recommendation(self, tracks: Any, strategy_name: str, explanation: Any) -> None:
        self.recommendation_calls.append((tracks, strategy_name, explanation))

    def show_transition_review(self, explanation: Any) -> None:
        self.transition_calls.append(explanation)

    def _populate_dj_readiness_table(self, readiness: Any) -> None:
        self.readiness_tables.append(readiness)


def test_controller_delegates_selected_variant_application_to_injected_boundary(monkeypatch) -> None:
    strategy = SimpleNamespace(name="build")
    recommendation = SimpleNamespace(ordered_tracks=["track"], strategy=strategy)
    readiness = SimpleNamespace(summary="Ready — 0 blocker(s), 0 review item(s); max BPM jump 0.00%")
    quality_report = SimpleNamespace(
        track_count=1,
        transition_count=0,
        average_transition_score=0.0,
        warning_count=0,
    )
    variant = SimpleNamespace(name="balanced", recommendation=recommendation, readiness=readiness)
    application_result = SimpleNamespace(
        recommendation=recommendation,
        explanation=object(),
        quality_report=quality_report,
        readiness_report=readiness,
        variant_name="balanced",
    )
    build_screen = SimpleNamespace(copilot_table=_Table(), applied_copilot_variant_label=_label())
    state = _State(variant)
    builder_calls: list[Any] = []
    transition_calls: list[Any] = []
    status_messages: list[str] = []
    state_changes = 0

    def fake_apply_transition(state_arg, payload):
        transition_calls.append((state_arg, payload))
        return "updated-state"

    def on_state_changed() -> None:
        nonlocal state_changes
        state_changes += 1

    monkeypatch.setattr("xfinaudio.desktop.prep_copilot.apply_prep_copilot_variant", fake_apply_transition)
    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=object(),
        state=state,
        workflow_service=object(),
        on_state_changed=on_state_changed,
        on_status_message=status_messages.append,
        desktop_recommendation_records=_unrouted,
        desktop_color_anchor_candidate_context=_unrouted,
        variant_application_builder=lambda variant_arg: builder_calls.append(variant_arg) or application_result,
    )

    controller.apply_selected_variant()

    assert builder_calls == [variant]
    assert transition_calls[0][1].quality_report is quality_report
    assert state._state == "updated-state"
    assert state_changes == 1
    assert state.recommendation_calls == [(recommendation.ordered_tracks, "build", application_result.explanation)]
    assert state.transition_calls == [application_result.explanation]
    assert state.readiness_tables == [readiness]
    assert status_messages == ["Applied Prep Copilot variant: balanced"]


class _Input:
    def __init__(self, value: Any) -> None:
        self._value = value

    def text(self) -> str:
        return str(self._value)

    def value(self) -> int:
        return int(self._value)


class _Combo:
    def __init__(self, data: Any, text: str) -> None:
        self._data = data
        self._text = text

    def currentData(self) -> Any:
        return self._data

    def currentText(self) -> str:
        return self._text


def test_controller_generate_without_tracks_invalidates_the_copilot_signature_cache(monkeypatch) -> None:
    """Clearing the table directly must also invalidate BuildScreen's cached signature.

    The controls-None branch bypasses `_populate_copilot_table`, so a stale signature
    would make the next render of identical variants skip repopulation and leave the
    visible table empty while the plan state still held rows.
    """
    invalidations: list[bool] = []
    build_screen = SimpleNamespace(
        copilot_table=SimpleNamespace(setRowCount=lambda count: None),
        apply_variant_button=SimpleNamespace(setEnabled=lambda enabled: None),
        invalidate_copilot_cache=lambda: invalidations.append(True),
    )
    state = SimpleNamespace(
        _state=object(),
        tr=lambda text: text,
        _selected_track_controls=lambda: None,
        _replace_app_state=lambda updated_state: None,
    )
    status_messages: list[str] = []
    monkeypatch.setattr(
        "xfinaudio.desktop.prep_copilot.apply_prep_copilot_plan_cleared",
        lambda state_arg: "cleared-state",
    )
    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=object(),
        state=state,
        workflow_service=object(),
        on_state_changed=lambda: None,
        on_status_message=status_messages.append,
        desktop_recommendation_records=_unrouted,
        desktop_color_anchor_candidate_context=_unrouted,
    )

    controller.generate()

    assert invalidations == [True]
    assert status_messages == ["Select at least one complete track before generating Prep Copilot"]


def test_controller_delegates_plan_generation_to_injected_boundary(monkeypatch) -> None:
    controls = SimpleNamespace(start_path="/music/start.flac", manual_order_paths=["/music/start.flac"])
    records: list[Any] = [object()]
    generated_plan = SimpleNamespace(variants=[object(), object()])
    build_screen = SimpleNamespace(
        copilot_table=SimpleNamespace(
            setRowCount=lambda count: None,
            setHidden=lambda hidden: None,
        ),
        apply_variant_button=SimpleNamespace(setEnabled=lambda enabled: None),
        genre_focus_input=_Input("House"),
        strategy_combo=_Combo("build", "Build"),
        target_count_input=_Input(12),
    )
    build_vm = object()
    initial_state = object()
    state = SimpleNamespace(
        _state=initial_state,
        tr=lambda text: text,
        _selected_track_controls=lambda: controls,
        _replace_app_state=lambda updated_state: None,
        settings=AppSettings(loudness=LoudnessSettings(target_lufs=-14.0, tolerance_lu=0.5)),
    )
    generation_calls: list[tuple[Any, Any, LoudnessBand | None]] = []
    status_messages: list[str] = []
    state_changes = 0
    render_calls: list[tuple[Any, Any]] = []

    def render(build_vm_arg: Any, state_arg: Any) -> None:
        render_calls.append((build_vm_arg, state_arg))

    build_screen.render = render

    def on_state_changed() -> None:
        nonlocal state_changes
        state_changes += 1

    def generate_plan(
        records: Any,
        request: Any,
        *,
        color_anchor_path: str | None = None,
        loudness_band: LoudnessBand | None = None,
    ) -> Any:
        generation_calls.append((records, request, loudness_band))
        assert color_anchor_path is None
        return generated_plan

    transition_calls: list[tuple[Any, Any]] = []

    def fake_plan_generated(state_arg: Any, plan_arg: Any) -> str:
        transition_calls.append((state_arg, plan_arg))
        return "updated-state"

    monkeypatch.setattr("xfinaudio.desktop.prep_copilot.apply_prep_copilot_plan_generated", fake_plan_generated)
    routed_bands: list[LoudnessBand] = []

    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=build_vm,
        state=state,
        workflow_service=object(),
        on_state_changed=on_state_changed,
        on_status_message=status_messages.append,
        desktop_recommendation_records=lambda *_args, loudness_band: routed_bands.append(loudness_band) or records,
        desktop_color_anchor_candidate_context=_unrouted,
        plan_generation_builder=generate_plan,
    )

    controller.generate()

    assert generation_calls[0][0] is records
    request = generation_calls[0][1]
    assert request.strategy == "build"
    assert request.target_track_count == 12
    assert request.start_path == "/music/start.flac"
    assert request.required_paths == ["/music/start.flac"]
    assert request.genre_focus == "House"
    assert routed_bands == [LoudnessBand(-14.0, 0.5)]
    assert generation_calls[0][2] == LoudnessBand(-14.0, 0.5)
    assert status_messages == ["Generated 2 Prep Copilot variant(s)"]
    assert transition_calls == [(initial_state, generated_plan)]
    assert render_calls == [(build_vm, state._state)]
    assert state_changes == 1


def test_controller_routes_colour_strategies_through_the_bound_anchor_context(monkeypatch) -> None:
    """Colour strategies must reach the plan chain with the anchor identity bound.

    The plain records route drops `color_anchor_path`, so a variant that filters the
    anchor away would rebind a different one. Only the context route keeps the identity
    the pool was actually planned for.
    """
    from xfinaudio.application.recommendation_candidates import RecommendationCandidateContext

    controls = SimpleNamespace(start_path="/music/anchor.flac", manual_order_paths=["/music/anchor.flac"])
    context_records: list[Any] = [object()]
    generated_plan = SimpleNamespace(variants=[object()])
    build_screen = SimpleNamespace(
        copilot_table=SimpleNamespace(setRowCount=lambda count: None, setHidden=lambda hidden: None),
        apply_variant_button=SimpleNamespace(setEnabled=lambda enabled: None),
        genre_focus_input=_Input("House"),
        strategy_combo=_Combo("same_color", "Same Color"),
        target_count_input=_Input(10),
        render=lambda build_vm_arg, state_arg: None,
    )
    plain_route_calls: list[Any] = []
    context_route_calls: list[Any] = []
    generation_calls: list[tuple[Any, Any, Any]] = []

    def context_route(controls_arg: Any, strategy_arg: str) -> RecommendationCandidateContext:
        context_route_calls.append((controls_arg, strategy_arg))
        return RecommendationCandidateContext(records=context_records, color_anchor_path="/music/anchor.flac")

    state = SimpleNamespace(
        _state=object(),
        tr=lambda text: text,
        _selected_track_controls=lambda: controls,
        _replace_app_state=lambda updated_state: None,
    )

    def generate_plan(
        records: Any, request: Any, *, color_anchor_path: str | None = None, loudness_band: Any = None
    ) -> Any:
        generation_calls.append((records, request, color_anchor_path))
        return generated_plan

    monkeypatch.setattr(
        "xfinaudio.desktop.prep_copilot.apply_prep_copilot_plan_generated",
        lambda state_arg, plan_arg: "updated-state",
    )

    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=object(),
        state=state,
        workflow_service=object(),
        on_state_changed=lambda: None,
        on_status_message=lambda message: None,
        desktop_recommendation_records=lambda controls_arg, _strategy=None: (
            plain_route_calls.append(controls_arg) or []
        ),
        desktop_color_anchor_candidate_context=context_route,
        plan_generation_builder=generate_plan,
    )

    controller.generate()

    assert context_route_calls == [(controls, "same_color")]
    assert plain_route_calls == []
    assert generation_calls[0][0] is context_records
    assert generation_calls[0][2] == "/music/anchor.flac"


def test_controller_routes_colour_display_labels_through_the_bound_anchor_context(monkeypatch) -> None:
    """A combo with no item data must still reach the colour route by its display label.

    `currentData()` is empty for combos populated without user data, so the fallback
    yields the display label ("Same Color"). That label is not an internal strategy
    name, so an unnormalised membership test skips the colour branch and plans the set
    unanchored — the exact failure the bound-anchor chain exists to prevent.
    """
    from xfinaudio.application.recommendation_candidates import RecommendationCandidateContext

    controls = SimpleNamespace(start_path="/music/anchor.flac", manual_order_paths=["/music/anchor.flac"])
    context_records: list[Any] = [object()]
    generated_plan = SimpleNamespace(variants=[object()])
    build_screen = SimpleNamespace(
        copilot_table=SimpleNamespace(setRowCount=lambda count: None, setHidden=lambda hidden: None),
        apply_variant_button=SimpleNamespace(setEnabled=lambda enabled: None),
        genre_focus_input=_Input("House"),
        strategy_combo=_Combo(None, "Same Color"),
        target_count_input=_Input(10),
        render=lambda build_vm_arg, state_arg: None,
    )
    plain_route_calls: list[Any] = []
    context_route_calls: list[Any] = []
    generation_calls: list[tuple[Any, Any, Any]] = []

    def context_route(controls_arg: Any, strategy_arg: str) -> RecommendationCandidateContext:
        context_route_calls.append((controls_arg, strategy_arg))
        return RecommendationCandidateContext(records=context_records, color_anchor_path="/music/anchor.flac")

    state = SimpleNamespace(
        _state=object(),
        tr=lambda text: text,
        _selected_track_controls=lambda: controls,
        _replace_app_state=lambda updated_state: None,
    )

    def generate_plan(
        records: Any, request: Any, *, color_anchor_path: str | None = None, loudness_band: Any = None
    ) -> Any:
        generation_calls.append((records, request, color_anchor_path))
        return generated_plan

    monkeypatch.setattr(
        "xfinaudio.desktop.prep_copilot.apply_prep_copilot_plan_generated",
        lambda state_arg, plan_arg: "updated-state",
    )

    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=object(),
        state=state,
        workflow_service=object(),
        on_state_changed=lambda: None,
        on_status_message=lambda message: None,
        desktop_recommendation_records=lambda controls_arg, _strategy=None: (
            plain_route_calls.append(controls_arg) or []
        ),
        desktop_color_anchor_candidate_context=context_route,
        plan_generation_builder=generate_plan,
    )

    controller.generate()

    assert context_route_calls == [(controls, "same_color")]
    assert plain_route_calls == []
    assert generation_calls[0][0] is context_records
    assert generation_calls[0][1].strategy == "same_color"
    assert generation_calls[0][2] == "/music/anchor.flac"


def test_controller_lets_an_unbound_colour_anchor_fall_back_to_internal_resolution(monkeypatch) -> None:
    """A colour context that binds no anchor must plan normally, not fail closed.

    The candidate seam returns `color_anchor_path=None` whenever it cannot bind an
    anchor. That is not the fail-closed case — fail-closed means a path was supplied
    and could not be found. `None` has to keep flowing through the real generation
    chain so `recommend_playlist` resolves an anchor itself, exactly as the main
    desktop recommendation route does.
    """
    from xfinaudio.application.recommendation_candidates import RecommendationCandidateContext

    records = [
        spectral_track("/music/anchor.flac", "GREEN", genre="House", bpm=122, key="8A", energy=5),
        spectral_track("/music/green.flac", "GREEN", genre="House", bpm=123, key="9A", energy=6),
        spectral_track("/music/red.flac", "RED", genre="House", bpm=124, key="9A", energy=6),
    ]
    controls = SimpleNamespace(start_path="/music/anchor.flac", manual_order_paths=["/music/anchor.flac"])
    build_screen = SimpleNamespace(
        copilot_table=SimpleNamespace(setRowCount=lambda count: None, setHidden=lambda hidden: None),
        apply_variant_button=SimpleNamespace(setEnabled=lambda enabled: None),
        genre_focus_input=_Input(""),
        strategy_combo=_Combo("same_color", "Same Color"),
        target_count_input=_Input(3),
        render=lambda build_vm_arg, state_arg: None,
    )
    generated_plans: list[Any] = []

    state = SimpleNamespace(
        _state=object(),
        tr=lambda text: text,
        _selected_track_controls=lambda: controls,
        _replace_app_state=lambda updated_state: None,
    )

    def fake_plan_generated(state_arg: Any, plan_arg: Any) -> str:
        generated_plans.append(plan_arg)
        return "updated-state"

    monkeypatch.setattr("xfinaudio.desktop.prep_copilot.apply_prep_copilot_plan_generated", fake_plan_generated)

    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=object(),
        state=state,
        workflow_service=object(),
        on_state_changed=lambda: None,
        on_status_message=lambda message: None,
        desktop_recommendation_records=_unrouted,
        desktop_color_anchor_candidate_context=lambda controls_arg, strategy_arg: RecommendationCandidateContext(
            records=records, color_anchor_path=None
        ),
    )

    controller.generate()

    plan = generated_plans[0]
    assert [variant.name for variant in plan.variants] == ["safe", "balanced", "adventurous"]
    # Internal resolution bound the GREEN anchor and the gate ran: tracks came back,
    # and the off-colour candidate was excluded rather than everything failing closed.
    for variant in plan.variants:
        paths = [item.path for item in variant.recommendation.ordered_tracks]
        assert paths, f"{variant.name} variant failed closed instead of resolving an anchor"
        assert "/music/red.flac" not in paths


def _prefiltered_generate_harness(
    monkeypatch: Any, controls: Any, scanned: list[Any], records: list[Any], *, use_real_plan_chain: bool = False
):
    """Build a controller wired to capture the generation request and the plan.

    The default injects a capturing plan builder so the request can be asserted
    on; `use_real_plan_chain=True` runs the real application generation chain so
    the test can assert on real domain pool notes. Plans are captured either way
    through the applied-state transition.
    """
    generated_plan = SimpleNamespace(variants=[object()])
    plans: list[Any] = []
    generation_calls: list[Any] = []
    build_screen = SimpleNamespace(
        copilot_table=SimpleNamespace(setRowCount=lambda count: None, setHidden=lambda hidden: None),
        apply_variant_button=SimpleNamespace(setEnabled=lambda enabled: None),
        genre_focus_input=_Input(""),
        strategy_combo=_Combo("build", "Build"),
        target_count_input=_Input(10),
        render=lambda build_vm_arg, state_arg: None,
    )
    state = SimpleNamespace(
        _state=object(),
        tr=lambda text: text,
        _selected_track_controls=lambda: controls,
        _replace_app_state=lambda updated_state: None,
        scanned_records=scanned,
    )

    def generate_plan(records: Any, request: Any, *, color_anchor_path: Any = None, loudness_band: Any = None) -> Any:
        generation_calls.append((records, request))
        return generated_plan

    def fake_plan_generated(state_arg: Any, plan_arg: Any) -> str:
        plans.append(plan_arg)
        return "updated-state"

    monkeypatch.setattr("xfinaudio.desktop.prep_copilot.apply_prep_copilot_plan_generated", fake_plan_generated)
    builder_kwargs = {} if use_real_plan_chain else {"plan_generation_builder": generate_plan}
    controller = PrepCopilotController(
        build_screen=build_screen,
        build_vm=object(),
        state=state,
        workflow_service=object(),
        on_state_changed=lambda: None,
        on_status_message=lambda message: None,
        desktop_recommendation_records=lambda *_args, **_kwargs: records,
        desktop_color_anchor_candidate_context=_unrouted,
        **builder_kwargs,
    )
    return controller, generation_calls, plans


def test_controller_generate_reports_the_genre_prefilter_in_the_request(monkeypatch) -> None:
    """The genre combo shrinks the pool BEFORE the plan runs, so only the
    controller knows both sizes and must pass the missing pool note down."""
    from tests.test_prep_copilot import track

    records = [track("/music/disco.flac", genre="Disco")]
    scanned = [
        track("/music/disco.flac", genre="Disco"),
        track("/music/house.flac", genre="House"),
        track("/music/rock.flac", genre="Rock"),
        track("/music/incomplete.flac", genre="Rock", status="incomplete"),
    ]
    controls = SimpleNamespace(start_path="/music/disco.flac", manual_order_paths=["/music/disco.flac"], genre="Disco")
    controller, generation_calls, _ = _prefiltered_generate_harness(monkeypatch, controls, scanned, records)

    controller.generate()

    assert generation_calls[0][1].pool_note_preamble == ("Genre 'Disco' prefilter: 1 of 3 complete library track(s)")


def test_controller_generate_without_genre_sends_no_prefilter_note(monkeypatch) -> None:
    from tests.test_prep_copilot import track

    records = [track("/music/disco.flac", genre="Disco")]
    scanned = [track("/music/disco.flac", genre="Disco")]
    controls = SimpleNamespace(start_path="/music/disco.flac", manual_order_paths=["/music/disco.flac"])
    controller, generation_calls, _ = _prefiltered_generate_harness(monkeypatch, controls, scanned, records)

    controller.generate()

    assert generation_calls[0][1].pool_note_preamble is None


def test_controller_genre_prefilter_note_reaches_the_variant_pool_notes(monkeypatch) -> None:
    """The prefilter note must lead the real domain pool notes the table shows."""
    from tests.test_prep_copilot import track

    records = [track("/music/disco.flac", genre="Disco")]
    scanned = [
        track("/music/disco.flac", genre="Disco"),
        track("/music/house.flac", genre="House"),
        track("/music/rock.flac", genre="Rock"),
    ]
    controls = SimpleNamespace(start_path="/music/disco.flac", manual_order_paths=["/music/disco.flac"], genre="Disco")
    controller, _, plans = _prefiltered_generate_harness(
        monkeypatch, controls, scanned, records, use_real_plan_chain=True
    )

    controller.generate()

    assert plans, "the plan must be captured from the real generation chain"
    for variant in plans[0].variants:
        assert variant.pool_notes[0] == "Genre 'Disco' prefilter: 1 of 3 complete library track(s)"
        assert variant.pool_notes[1] == "Incoming pool: 1 track(s)"


def test_controller_generate_with_an_unshrunk_genre_pool_sends_no_prefilter_note(monkeypatch) -> None:
    """A genre filter that kept the whole library must not claim a shrink."""
    from tests.test_prep_copilot import track

    records = [track("/music/disco.flac", genre="Disco"), track("/music/disco2.flac", genre="Disco")]
    scanned = [track("/music/disco.flac", genre="Disco"), track("/music/disco2.flac", genre="Disco")]
    controls = SimpleNamespace(start_path="/music/disco.flac", manual_order_paths=["/music/disco.flac"], genre="Disco")
    controller, generation_calls, _ = _prefiltered_generate_harness(monkeypatch, controls, scanned, records)

    controller.generate()

    assert generation_calls[0][1].pool_note_preamble is None
