"""Cancellation is cooperative between candidate/variant preparation stages."""

from concurrent.futures import CancelledError

import pytest

from tests.test_prep_copilot import track
from xfinaudio.application.prep_copilot import PrepCopilotGenerationRequest, generate_prep_copilot_plan
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan


def test_prep_stops_before_next_variant_after_cancellation(monkeypatch):
    import xfinaudio.recommendation.prep_copilot as domain

    calls = []
    original = domain._build_variant

    def build(name, *args, **kwargs):
        calls.append(name)
        return original(name, *args, **kwargs)

    monkeypatch.setattr(domain, "_build_variant", build)

    def checkpoint(stage):
        if calls:
            raise CancelledError()

    with pytest.raises(CancelledError):
        build_prep_copilot_plan(
            [track("/a.flac"), track("/b.flac")],
            DJSetIntent(name="cancel", target_track_count=2),
            checkpoint=checkpoint,
        )
    assert calls == ["safe"]


def test_application_forwards_all_variant_progress_checkpoints():
    stages = []
    plan = generate_prep_copilot_plan(
        [track("/a.flac"), track("/b.flac")],
        PrepCopilotGenerationRequest(strategy="harmonic_journey", target_track_count=2),
        checkpoint=stages.append,
    )
    assert len(plan.variants) == 3
    assert stages == ["safe", "balanced", "adventurous", "complete"]
