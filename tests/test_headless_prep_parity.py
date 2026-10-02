"""Real-domain Prep parity at the Qt-free, opaque-identity command boundary."""

from __future__ import annotations

import hashlib
import io
import json
import threading
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.test_headless_backend import tagged_flac
from tests.test_headless_protocol import messages, request
from xfinaudio.application.strategy_catalog import list_strategy_catalog
from xfinaudio.audio.spectral_profile import CURRENT_ANALYSIS_VERSION, SpectralProfile
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.server import JsonlServer
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken
from xfinaudio.recommendation.prep_copilot import DJSetIntent, build_prep_copilot_plan


def identity(record: TrackRecord) -> str:
    return hashlib.sha256(record.path.encode()).hexdigest()


def seeded(tmp_path: Path, count: int = 6) -> tuple[HeadlessBackend, list[TrackRecord]]:
    root = tmp_path / "music"
    root.mkdir()
    records = [
        TrackRecord(
            path=str(root / f"{index:03}.flac"),
            title=f"Track {index}",
            artist="Artist",
            bpm=120,
            camelot_key="8A",
            energy_level=5,
            duration=240,
            genre="House",
            metadata_status="complete",
        )
        for index in range(count)
    ]
    for record in records:
        Path(record.path).touch()
    backend = HeadlessBackend(tmp_path / "data")
    backend.roots = [root]
    backend.repository.save_scan_results(records)
    return backend, records


def test_catalog_matches_existing_domain_and_is_read_only(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    before = backend.execute("prep.generate", {"targetTrackCount": 3})
    result = backend.execute("prep.catalog", {})
    assert result == {
        "strategies": [
            {
                "name": s.name,
                "displayName": s.display_name,
                "description": s.description,
                "requiresVibeMetadata": s.requires_vibe_metadata,
            }
            for s in list_strategy_catalog()
        ]
    }
    assert backend.review_id == before["reviewId"]
    with pytest.raises(BackendError):
        backend.execute("prep.catalog", {"extra": True})


def test_generate_select_and_save_use_real_variants_and_fresh_review(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path)
    result = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Club"})
    assert str(UUID(result["planId"])) == result["planId"]
    expected = build_prep_copilot_plan(records, DJSetIntent(name="Club", target_track_count=4))
    assert result["variant"] == "balanced"
    assert [s["name"] for s in result["variants"]] == ["safe", "balanced", "adventurous"]
    previous_id = result["reviewId"]
    for variant in expected.variants:
        selected = backend.execute("prep.select", {"planId": result["planId"], "variant": variant.name})
        assert selected["reviewId"] != previous_id
        assert selected["planId"] == result["planId"]
        assert selected["variants"] == result["variants"]
        assert selected["name"] == "Club"
        assert selected["variant"] == variant.name
        assert [t["id"] for t in selected["tracks"]] == [identity(t) for t in variant.recommendation.ordered_tracks]
        assert selected["warnings"] == variant.warnings
        assert selected["blockers"] == variant.blockers
        summary = next(s for s in result["variants"] if s["name"] == variant.name)
        assert summary == {
            "name": variant.name,
            "description": variant.description,
            "trackCount": len(selected["tracks"]),
            "readiness": selected["readiness"],
            "warnings": selected["warnings"],
            "blockers": selected["blockers"],
            "qualityScore": selected["qualityScore"],
        }
        with pytest.raises(BackendError) as stale:
            backend.execute("playlist.save", {"name": "Old", "reviewId": previous_id})
        assert stale.value.code == "stale_review"
        saved = backend.execute("playlist.save", {"name": "Selected", "reviewId": selected["reviewId"]})
        assert backend.execute("playlist.open", {"playlistId": saved["id"]})["tracks"] == selected["tracks"]
        previous_id = selected["reviewId"]
    assert str(tmp_path) not in json.dumps(result)


def test_full_intent_reaches_domain_and_enforces_controls(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path)
    params = {
        "targetTrackCount": 5,
        "name": "Intent",
        "strategy": "same_energy",
        "targetMinutes": 8.5,
        "slotRole": "warmup",
        "genreFocus": "House",
        "startTrackId": identity(records[2]),
        "endTrackId": identity(records[4]),
        "requiredTrackIds": [identity(records[3])],
        "excludedTrackIds": [identity(records[0])],
    }
    result = backend.execute("prep.generate", params)
    intent = backend.plan.intent
    assert intent == DJSetIntent(
        name="Intent",
        strategy="same_energy",
        target_track_count=5,
        target_minutes=8.5,
        slot_role="warmup",
        genre_focus="House",
        start_path=records[2].path,
        end_path=records[4].path,
        required_paths=[records[3].path],
        excluded_paths={records[0].path},
    )
    paths = [t["id"] for t in result["tracks"]]
    assert paths[0] == params["startTrackId"] and paths[-1] == params["endTrackId"]
    assert identity(records[3]) in paths and identity(records[0]) not in paths


@pytest.mark.parametrize(
    "change",
    [
        {"strategy": "Harmonic Journey"},
        {"strategy": "unknown"},
        {"strategy": None},
        {"strategy": []},
        {"targetMinutes": 0},
        {"targetMinutes": -1},
        {"targetMinutes": 601},
        {"targetMinutes": True},
        {"targetMinutes": 10**3000},
        {"targetMinutes": float("nan")},
        {"targetMinutes": float("inf")},
        {"targetMinutes": "30"},
        {"slotRole": "build"},
        {"slotRole": []},
        {"genreFocus": "x" * 101},
        {"genreFocus": "x\x00y"},
        {"genreFocus": 1},
        {"startTrackId": "0" * 64},
        {"endTrackId": "../escape"},
        {"startTrackId": "A" * 64},
        {"requiredTrackIds": "0" * 64},
        {"excludedTrackIds": None},
        {"requiredTrackIds": ["0" * 64] * 101},
        {"excludedTrackIds": ["0" * 64]},
    ],
)
def test_intent_validation_rejects_untrusted_input(tmp_path: Path, change: dict) -> None:
    backend, _ = seeded(tmp_path)
    with pytest.raises(BackendError) as exc:
        backend.execute("prep.generate", {"targetTrackCount": 3, **change})
    assert exc.value.code == "invalid_params"
    assert str(tmp_path) not in str(exc.value)


@pytest.mark.parametrize(
    "kind", ["required_excluded", "start_excluded", "end_excluded", "same_anchors", "duplicates", "too_many"]
)
def test_control_conflicts_fail_before_generation(tmp_path: Path, kind: str) -> None:
    backend, records = seeded(tmp_path)
    ids = [identity(r) for r in records]
    changes = {
        "required_excluded": {"requiredTrackIds": [ids[0]], "excludedTrackIds": [ids[0]]},
        "start_excluded": {"startTrackId": ids[0], "excludedTrackIds": [ids[0]]},
        "end_excluded": {"endTrackId": ids[0], "excludedTrackIds": [ids[0]]},
        "same_anchors": {"startTrackId": ids[0], "endTrackId": ids[0]},
        "duplicates": {"requiredTrackIds": [ids[0], ids[0]]},
        "too_many": {"requiredTrackIds": ids[:4]},
    }
    with pytest.raises(BackendError) as exc:
        backend.execute("prep.generate", {"targetTrackCount": 3, **changes[kind]})
    assert exc.value.code == "invalid_params"


@pytest.mark.parametrize("next_action", ["generate", "invalid_generate", "scan", "cancel"])
def test_new_work_or_cancellation_invalidates_plan_and_review(tmp_path: Path, next_action: str) -> None:
    backend, _ = seeded(tmp_path)
    result = backend.execute("prep.generate", {"targetTrackCount": 3})
    if next_action == "generate":
        backend.execute("prep.generate", {"targetTrackCount": 2})
    elif next_action == "invalid_generate":
        with pytest.raises(BackendError):
            backend.execute("prep.generate", {"targetTrackCount": 0})
    elif next_action == "scan":
        backend.execute("library.scan", {"root": str(tmp_path / "music")})
    else:
        token = ScanCancellationToken()

        def cancel(data: dict) -> None:
            token.cancel()

        with pytest.raises(BackendError) as cancelled:
            backend.execute("prep.generate", {"targetTrackCount": 3}, cancellation_token=token, progress=cancel)
        assert cancelled.value.code == "cancelled"
    with pytest.raises(BackendError) as stale:
        backend.execute("prep.select", {"planId": result["planId"], "variant": "safe"})
    assert stale.value.code == "stale_plan"
    with pytest.raises(BackendError) as stale_review:
        backend.execute("playlist.save", {"name": "Old", "reviewId": result["reviewId"]})
    assert stale_review.value.code == "stale_review"


@pytest.mark.parametrize(
    "change", [{"planId": str(uuid4())}, {"planId": "invalid"}, {"variant": "unknown"}, {"variant": []}]
)
def test_bad_selection_cannot_leave_previous_review_saveable(tmp_path: Path, change: dict) -> None:
    backend, _ = seeded(tmp_path)
    result = backend.execute("prep.generate", {"targetTrackCount": 3})
    with pytest.raises(BackendError):
        backend.execute("prep.select", {"planId": result["planId"], "variant": "safe", **change})
    with pytest.raises(BackendError) as stale:
        backend.execute("playlist.save", {"name": "Old", "reviewId": result["reviewId"]})
    assert stale.value.code == "stale_review"


def test_candidate_prefilter_and_required_tracks_survive_pool_cap(tmp_path: Path) -> None:
    backend, records = seeded(tmp_path, 180)
    records = [r.model_copy(update={"energy_level": 9 if i < 160 else 4}) for i, r in enumerate(records)]
    backend.repository.save_scan_results(records)
    result = backend.execute(
        "prep.generate", {"targetTrackCount": 3, "strategy": "warmup", "requiredTrackIds": [identity(records[-1])]}
    )
    assert len(result["tracks"]) == 3
    assert identity(records[-1]) in [t["id"] for t in result["tracks"]]
    assert all(t["energy"] == 4 for t in result["tracks"])


@pytest.mark.parametrize("require_last", [False, True])
def test_color_bound_anchor_survives_dedupe_cap_and_exclusion(tmp_path: Path, require_last: bool) -> None:
    backend, records = seeded(tmp_path, 35)
    red = SpectralProfile(
        red_ratio=1,
        green_ratio=0,
        blue_ratio=0,
        centroid_hz=1000,
        rolloff_hz=2000,
        dominant_color="RED",
        analysis_version=CURRENT_ANALYSIS_VERSION,
    )
    blue = red.model_copy(update={"red_ratio": 0, "blue_ratio": 1, "dominant_color": "BLUE"})
    records = [r.model_copy(update={"spectral_profile": red if i == 0 else blue}) for i, r in enumerate(records)]
    records[1] = records[1].model_copy(update={"title": "Track 2 (Edit)"})
    backend.repository.save_scan_results(records)
    result = backend.execute(
        "prep.generate",
        {
            "targetTrackCount": 3,
            "strategy": "same_color",
            "requiredTrackIds": [identity(records[-1])] if require_last else [],
            "excludedTrackIds": [identity(records[0])],
        },
    )
    assert len(result["tracks"]) == 3
    assert identity(records[0]) not in [t["id"] for t in result["tracks"]]
    expected_anchor = records[-1] if require_last else records[1]
    assert backend.review.recommendation.replacement_policy.color_anchor_path == expected_anchor.path


@pytest.mark.parametrize(
    "strategy, fragment",
    [
        ("same_color", "prerequisite"),
        ("same_color_energy", "prerequisite"),
        ("consistent_loudness", "Loudness coverage"),
    ],
)
def test_missing_analysis_is_honest_and_never_computed(
    tmp_path: Path, strategy: str, fragment: str, monkeypatch
) -> None:
    import xfinaudio.library.scan_service as scanner

    def forbidden(*args, **kwargs):
        raise AssertionError("Prep must not analyze audio")

    monkeypatch.setattr(scanner, "analyze_paths", forbidden)
    backend, _ = seeded(tmp_path)
    result = backend.execute("prep.generate", {"targetTrackCount": 3, "strategy": strategy})
    assert any(fragment in warning for warning in result["warnings"])
    if strategy.startswith("same_color"):
        assert result["tracks"] == []
        assert result["readiness"] == "blocked"
        with pytest.raises(BackendError) as blocked:
            backend.execute("playlist.save", {"name": "Blocked", "reviewId": result["reviewId"]})
        assert blocked.value.code == "blocked_review"


def test_catalog_fast_path_during_generation(tmp_path: Path) -> None:
    started, release = threading.Event(), threading.Event()

    class SlowBackend(HeadlessBackend):
        def execute(self, method, params, *, cancellation_token=None, progress=None):
            if method == "prep.generate":
                started.set()
                assert release.wait(5)
                return {}
            return super().execute(method, params, cancellation_token=cancellation_token, progress=progress)

    output = io.StringIO()
    server = JsonlServer(SlowBackend(tmp_path), output)
    server.process_line(request("prep.generate", {"targetTrackCount": 3}))
    assert started.wait(5)
    try:
        server.process_line(request("prep.catalog"))
        assert messages(output)[0]["result"]["strategies"]
    finally:
        release.set()
        server.close()


def test_scan_and_all_prep_choices_leave_audio_bytes_unchanged(tmp_path: Path) -> None:
    root = tmp_path / "music"
    for i in range(3):
        tagged_flac(root / f"{i}.flac", i)
    before = {p: p.read_bytes() for p in root.iterdir()}
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    for strategy in backend.execute("prep.catalog", {})["strategies"]:
        result = backend.execute("prep.generate", {"targetTrackCount": 3, "strategy": strategy["name"]})
        for variant in result["variants"]:
            backend.execute("prep.select", {"planId": result["planId"], "variant": variant["name"]})
    assert all(p.read_bytes() == data for p, data in before.items())


@pytest.mark.parametrize("replacement", ["deleted", "external_symlink", "directory"])
def test_reopen_counts_physically_missing_or_unsafe_tracks(tmp_path: Path, replacement: str) -> None:
    backend, records = seeded(tmp_path, 3)
    result = backend.execute("prep.generate", {"targetTrackCount": 3})
    saved = backend.execute("playlist.save", {"name": "Set", "reviewId": result["reviewId"]})
    missing = Path(records[0].path)
    missing.unlink()
    if replacement == "external_symlink":
        outside = tmp_path / "private.flac"
        outside.write_bytes(b"never read")
        missing.symlink_to(outside)
    elif replacement == "directory":
        missing.mkdir()
    opened = backend.execute("playlist.open", {"playlistId": saved["id"]})
    assert opened["missingTrackCount"] == 1
    assert identity(records[0]) not in [t["id"] for t in opened["tracks"]]
    assert len(backend.repository.list_display_tracks()) == 3
    assert len(backend.playlists.get_by_id(saved["id"]).track_paths) == 3


def test_late_select_cancellation_invalidates_plan_and_review(tmp_path: Path) -> None:
    backend, _ = seeded(tmp_path)
    result = backend.execute("prep.generate", {"targetTrackCount": 3})
    execute = backend.execute

    def cancel_after_selection(method, params, *, cancellation_token=None, progress=None):
        result = execute(method, params, cancellation_token=cancellation_token, progress=progress)
        if method == "prep.select":
            cancellation_token.cancel()
        return result

    backend.execute = cancel_after_selection
    output = io.StringIO()
    server = JsonlServer(backend, output)
    server.process_line(request("prep.select", {"planId": result["planId"], "variant": "safe"}))
    with server._lock:
        active = server._active
    if active:
        active[2].join()
    assert messages(output)[-1]["error"]["code"] == "cancelled"
    assert backend.plan is None and backend.review is None


def test_metadata_report_command_uses_authorized_library_and_preserves_review(tmp_path: Path) -> None:
    from xfinaudio.headless.metadata_report import build_metadata_report

    backend, records = seeded(tmp_path)
    result = backend.execute("prep.generate", {"targetTrackCount": 3})
    output = io.StringIO()
    server = JsonlServer(backend, output)
    backend.repository.save_scan_results([TrackRecord(path=str(tmp_path / "private.flac"))])
    server.process_line(request("metadata.report"))
    with server._lock:
        active = server._active
    if active:
        active[2].join()
    assert messages(output)[-1]["result"] == build_metadata_report(records, locked_paths=frozenset())
    assert backend.review_id == result["reviewId"]
    with pytest.raises(BackendError):
        backend.execute("metadata.report", {"root": "/outside"})
