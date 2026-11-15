"""Review facts in the payload of prep.generate, prep.select and every review edit (S4)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.test_headless_prep_parity import seeded

# Every key the review payload answers today: the two new facts are additive.
PAYLOAD_KEYS = {
    "blockers",
    "canRedo",
    "canUndo",
    "engineFacts",
    "name",
    "planId",
    "protectedTrackIds",
    "qualityScore",
    "readiness",
    "readinessChecks",
    "readinessSummary",
    "reviewId",
    "tracks",
    "transitionScores",
    "transitions",
    "variant",
    "variants",
    "warnings",
}


def details(backend: Any, review: dict[str, Any]) -> dict[str, Any]:
    return backend.execute("review.details", {"reviewId": review["reviewId"]})


def assert_review_facts(backend: Any, review: dict[str, Any]) -> None:
    """Every payload answers the same facts review.details computes, without a new call."""
    current = details(backend, review)
    assert set(review) == PAYLOAD_KEYS
    assert review["transitionScores"] == [item["totalScore"] for item in current["transitions"]]
    assert len(review["transitionScores"]) == len(review["tracks"]) - 1
    assert all(0.0 <= score <= 1.0 for score in review["transitionScores"])
    assert review["readinessChecks"] == current["readinessChecks"]
    assert review["readinessChecks"] == [
        check.model_dump(mode="json") for check in backend.review.readiness_report.checks
    ]
    assert all(set(check) == {"label", "status", "detail"} for check in review["readinessChecks"])


def test_generate_answers_every_transition_score_and_readiness_check(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    assert_review_facts(backend, result)
    assert len(result["tracks"]) == 4


def test_select_answers_the_same_facts_as_generate(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path, 8)
    generated = backend.execute("prep.generate", {"targetTrackCount": 4})
    selected = backend.execute("prep.select", {"planId": generated["planId"], "variant": "safe"})
    assert_review_facts(backend, selected)
    assert selected["variant"] == "safe"


def test_every_review_edit_keeps_the_facts_matching_details(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path, 8)
    review = backend.execute("prep.generate", {"targetTrackCount": 4})
    assert_review_facts(backend, review)
    ids = [track["id"] for track in review["tracks"]]
    reordered = backend.execute("review.reorder", {"reviewId": review["reviewId"], "trackIds": ids[::-1]})
    assert_review_facts(backend, reordered)
    target = ids[0]
    removed = backend.execute("review.remove", {"reviewId": reordered["reviewId"], "trackId": target})
    assert_review_facts(backend, removed)
    undo = backend.execute("review.undo", {"reviewId": removed["reviewId"]})
    assert_review_facts(backend, undo)
    redo = backend.execute("review.redo", {"reviewId": undo["reviewId"]})
    assert_review_facts(backend, redo)
    candidate = next(track["id"] for track in redo["tracks"] if track["id"] not in redo["protectedTrackIds"])
    comparison = backend.execute("review.compare", {"reviewId": redo["reviewId"], "trackId": candidate})
    assert_review_facts(backend, redo)
    replaced = backend.execute(
        "review.replace",
        {"reviewId": redo["reviewId"], "trackId": candidate, "replacementId": comparison["replacement"]["id"]},
    )
    assert_review_facts(backend, replaced)
