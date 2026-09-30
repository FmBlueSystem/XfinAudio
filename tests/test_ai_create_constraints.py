"""Local hard constraints survive AI suggestions and invalid overlaps fail closed."""

import pytest

from xfinaudio.desktop.ai_create_constraints import confirmed_intent
from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation.controls import DJControls
from xfinaudio.recommendation.prep_copilot import DJSetIntent

TRACKS = [TrackRecord(path=p) for p in ("a", "b", "c")]


def test_merge_preserves_locks_exclusions_and_selected_order():
    controls = DJControls(locked_paths={"b"}, excluded_paths={"c"}, start_path="a", manual_order_paths=["a", "b"])
    result = confirmed_intent(DJSetIntent(name="Set"), controls, TRACKS)
    assert result.required_paths == ["a", "b"]
    assert result.start_path == "a"
    assert result.excluded_paths == {"c"}


@pytest.mark.parametrize(
    "intent",
    [
        DJSetIntent(name="Bad", required_paths=["missing"]),
        DJSetIntent(name="Bad", required_paths=["c"]),
        DJSetIntent(name="Bad", start_path="c"),
        DJSetIntent(name="Bad", required_paths=["a", "b", "c"], target_track_count=2),
    ],
)
def test_invalid_or_conflicting_ai_constraints_cannot_plan(intent):
    with pytest.raises(ValueError):
        confirmed_intent(intent, DJControls(excluded_paths={"c"}), TRACKS)
