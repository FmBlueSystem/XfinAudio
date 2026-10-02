"""A stable incumbent is scored once per local-search pass."""

from unittest.mock import patch

from xfinaudio.library.models import TrackRecord
from xfinaudio.recommendation import optimizer


def test_two_opt_does_not_rescore_unchanged_incumbent_for_every_candidate() -> None:
    count = 6
    tracks = [TrackRecord(path=str(i)) for i in range(count)]
    matrix = [[0.0] * count for _ in range(count)]
    path = tuple(range(count))
    with patch.object(optimizer, "_path_score", wraps=optimizer._path_score) as scoring:
        result = optimizer._two_opt(path, matrix, tracks, start_fixed=False, end_fixed=False)
    assert result == path
    # All candidate reversals tie and lose lexicographically; there is one pass.
    candidates = count * (count - 1) // 2
    assert scoring.call_count <= candidates + 1
