"""Original-engine review parity, revision and source safety on disposable tracks."""

import json
from pathlib import Path

import pytest

from tests.test_headless_prep_parity import identity, seeded
from xfinaudio.headless.common import BackendError
from xfinaudio.recommendation.playlist_service import recommendation_reordered, recommendation_with_replacement


def generated(tmp_path, **params):
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, **params})
    return backend, records, result


def test_review_exposes_all_real_transition_components_and_readiness(tmp_path):
    backend, _, result = generated(tmp_path)
    details = backend.execute("review.details", {"reviewId": result["reviewId"]})
    assert (
        details["transitions"][0]["components"] == backend.review.recommendation.transition_scores[0].component_scores
    )
    assert details["readinessChecks"] == [check.model_dump() for check in backend.review.readiness_report.checks]
    assert len(details["transitions"]) == len(result["tracks"]) - 1
    assert "Local engine" in details["engineFacts"]
    assert str(tmp_path) not in json.dumps(details)


def test_compare_is_pure_and_remove_reuses_replacement_then_invalidates_old_id(tmp_path):
    backend, records, result = generated(tmp_path)
    original = backend.review.recommendation
    target = result["tracks"][1]["id"]
    expected = recommendation_with_replacement(
        original,
        original.ordered_tracks[1].path,
        records,
        spectral_cohesion=backend.preferences.spectral_cohesion(),
        loudness_band=backend.preferences.loudness_band(),
    )
    comparison = backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": target})
    assert backend.review.recommendation == original
    assert backend.review_id == result["reviewId"]
    assert comparison["replacement"]["id"] == identity(
        next(t for t in expected.ordered_tracks if t not in original.ordered_tracks)
    )
    updated = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": target})
    assert backend.review.recommendation == expected
    assert updated["reviewId"] != result["reviewId"]
    assert len(updated["tracks"]) == 4
    with pytest.raises(BackendError, match="current"):
        backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": target})


def test_reorder_rescores_and_preserves_save_order(tmp_path):
    backend, _, result = generated(tmp_path)
    original = backend.review.recommendation
    ids = [t["id"] for t in result["tracks"]][::-1]
    expected = recommendation_reordered(
        original,
        [t.path for t in original.ordered_tracks][::-1],
        spectral_cohesion=backend.preferences.spectral_cohesion(),
    )
    updated = backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": ids})
    assert backend.review.recommendation == expected
    assert [t["id"] for t in updated["tracks"]] == ids
    saved = backend.execute("playlist.save", {"reviewId": updated["reviewId"], "name": "Edited"})
    assert [t["id"] for t in backend.execute("playlist.open", {"playlistId": saved["id"]})["tracks"]] == ids


def test_protected_tracks_and_exact_permutations_are_enforced(tmp_path):
    backend, records = seeded(tmp_path, 8)
    result = backend.execute(
        "prep.generate",
        {"targetTrackCount": 4, "startTrackId": identity(records[0]), "requiredTrackIds": [identity(records[1])]},
    )
    for track in records[:2]:
        with pytest.raises(BackendError) as error:
            backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": identity(track)})
        assert error.value.code == "protected_track"
    for ids in [[t["id"] for t in result["tracks"]][::-1], [result["tracks"][0]["id"]] * 4]:
        with pytest.raises(BackendError):
            backend.execute("review.reorder", {"reviewId": result["reviewId"], "trackIds": ids})
    assert backend.review_id == result["reviewId"]


def test_changed_source_cannot_be_edited_or_saved(tmp_path):
    backend, _, result = generated(tmp_path)
    Path(backend.review.recommendation.ordered_tracks[0].path).write_bytes(b"changed")
    for method, fields in [
        ("review.details", {}),
        ("review.remove", {"trackId": result["tracks"][1]["id"]}),
        ("playlist.save", {"name": "Stale"}),
    ]:
        with pytest.raises(BackendError) as error:
            backend.execute(method, {"reviewId": result["reviewId"], **fields})
        assert error.value.code == "stale_review"


def test_removal_without_eligible_backfill_is_honest_and_never_resurrects_removed(tmp_path):
    backend, records = seeded(tmp_path, 4)
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    first = result["tracks"][1]["id"]
    updated = backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": first})
    assert len(updated["tracks"]) == 3
    updated = backend.execute("review.remove", {"reviewId": updated["reviewId"], "trackId": updated["tracks"][1]["id"]})
    assert len(updated["tracks"]) == 2
    assert first not in [track["id"] for track in updated["tracks"]]


def test_export_source_revalidates_bound_review_file_identity_without_writing(tmp_path):
    from xfinaudio.headless.serato_source import load_source

    backend, _, result = generated(tmp_path)
    assert load_source(backend, {"kind": "review", "reviewId": result["reviewId"]}).readiness != "blocked"
    Path(backend.review.recommendation.ordered_tracks[0].path).write_bytes(b"changed after review")
    source = load_source(backend, {"kind": "review", "reviewId": result["reviewId"]})
    assert source.readiness == "blocked"
    assert any("Review sources" in blocker for blocker in source.blockers)


def test_details_marks_protected_controls_for_renderer(tmp_path):
    backend, records = seeded(tmp_path, 8)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "requiredTrackIds": [identity(records[0])]})
    assert result["protectedTrackIds"] == [identity(records[0])]


def test_candidate_changed_during_assessment_does_not_publish_partial_edit(tmp_path, monkeypatch):
    backend, _, result = generated(tmp_path)
    original = backend.review
    assess = backend.review_actions._assess

    def change_source(proposed):
        candidate = next(
            track for track in proposed.ordered_tracks if track not in original.recommendation.ordered_tracks
        )
        Path(candidate.path).write_bytes(b"changed during assessment")
        return assess(proposed)

    monkeypatch.setattr(backend.review_actions, "_assess", change_source)
    with pytest.raises(BackendError) as error:
        backend.execute("review.remove", {"reviewId": result["reviewId"], "trackId": result["tracks"][1]["id"]})
    assert error.value.code == "stale_review"
    assert backend.review_id == result["reviewId"]
    assert backend.review is original


def test_policy_change_rejects_prior_review_and_does_not_edit(tmp_path):
    backend, _, result = generated(tmp_path)
    settings = backend.preferences.get_profiles()
    backend.preferences.update_profiles({"revision": settings["revision"], "spectralCohesion": 0.9})
    with pytest.raises(BackendError) as error:
        backend.execute("review.compare", {"reviewId": result["reviewId"], "trackId": result["tracks"][1]["id"]})
    assert error.value.code == "stale_review"
    assert backend.review_id == result["reviewId"]


def test_required_track_gate_remains_blocking_after_reorder(tmp_path):
    backend, records = seeded(tmp_path, 8)
    changed = records[-1].model_copy(update={"bpm": 180})
    backend.repository.save_scan_results([*records[:-1], changed])
    result = backend.execute(
        "prep.generate", {"targetTrackCount": 4, "requiredTrackIds": [identity(records[0]), identity(records[-1])]}
    )
    assert result["readiness"] == "blocked"
    updated = backend.execute(
        "review.reorder", {"reviewId": result["reviewId"], "trackIds": [track["id"] for track in result["tracks"]]}
    )
    assert updated["readiness"] == "blocked"
    assert any(
        check["label"] == "Required tracks" and check["status"] == "blocked" for check in updated["readinessChecks"]
    )
    with pytest.raises(BackendError) as error:
        backend.execute("playlist.save", {"reviewId": updated["reviewId"], "name": "Blocked"})
    assert error.value.code == "blocked_review"


@pytest.mark.parametrize("change", ["bytes", "metadata", "policy"])
def test_cached_variant_cannot_launder_stale_generation_context(tmp_path, change):
    backend, _, result = generated(tmp_path)
    track = backend.review.recommendation.ordered_tracks[0]
    if change == "bytes":
        Path(track.path).write_bytes(b"changed since plan generation")
    elif change == "metadata":
        backend.repository.save_scan_results([track.model_copy(update={"bpm": 130})])
    else:
        settings = backend.preferences.get_profiles()
        backend.preferences.update_profiles({"revision": settings["revision"], "spectralCohesion": 0.9})
    with pytest.raises(BackendError) as error:
        backend.execute("prep.select", {"planId": result["planId"], "variant": "safe"})
    assert error.value.code == "stale_plan"
    assert backend.review is None


def test_generation_source_changed_during_engine_cannot_be_bound_as_fresh(tmp_path, monkeypatch):
    import xfinaudio.headless.backend as module

    backend, records = seeded(tmp_path, 8)
    generate = module.generate_plan

    def change_after_generation(*args, **kwargs):
        plan = generate(*args, **kwargs)
        Path(records[0].path).write_bytes(b"changed while generating")
        return plan

    monkeypatch.setattr(module, "generate_plan", change_after_generation)
    with pytest.raises(BackendError) as error:
        backend.execute("prep.generate", {"targetTrackCount": 4})
    assert error.value.code == "stale_plan"
    assert backend.review is None


def test_source_changed_during_variant_application_leaves_no_partial_review(tmp_path, monkeypatch):
    import xfinaudio.headless.backend as module

    backend, records, result = generated(tmp_path)
    build = module.build_prep_copilot_variant_application

    def change_during_application(variant):
        application = build(variant)
        Path(records[0].path).write_bytes(b"changed during selection")
        return application

    monkeypatch.setattr(module, "build_prep_copilot_variant_application", change_during_application)
    with pytest.raises(BackendError) as error:
        backend.execute("prep.select", {"planId": result["planId"], "variant": "safe"})
    assert error.value.code == "stale_plan"
    assert backend.review is None
    assert backend.review_id is None
