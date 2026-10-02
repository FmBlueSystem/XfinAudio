"""Qt-free loudness preferences and real Prep policy propagation."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from typing import Any, TypedDict, cast

import pytest

from xfinaudio.config.settings import AppSettings
from xfinaudio.config.settings_repository import SettingsRepository
from xfinaudio.headless.common import BackendError
from xfinaudio.headless.preferences import MAX_SETTINGS_BYTES, SETTINGS_FIELDS, PreferencesService
from xfinaudio.recommendation.loudness_policy import DEFAULT_LOUDNESS_BAND, LoudnessBand


def service(tmp_path: Path) -> PreferencesService:
    tmp_path.mkdir(parents=True, exist_ok=True)
    return PreferencesService(cast(Any, SimpleNamespace(data_dir=tmp_path, roots=[])))


def update(preferences: PreferencesService, **changes: Any) -> dict[str, Any]:
    return preferences.update_loudness({**preferences.get_loudness(), **changes})


def test_loudness_defaults_are_original_policy_without_writing_settings(tmp_path: Path) -> None:
    preferences = service(tmp_path)
    actual = preferences.get_loudness()
    assert actual == {
        "revision": preferences.execute("settings.get", {})["revision"],
        "enabled": True,
        "targetLufs": -10.0,
        "toleranceLu": 2.0,
    }
    assert preferences.loudness_band() == DEFAULT_LOUDNESS_BAND
    assert not (tmp_path / "settings.json").exists()
    assert {"settings.get": set(), "settings.update": {"revision", "previewVolume", "watchLibrary"}} == SETTINGS_FIELDS
    assert preferences.execute("settings.get", {})["capabilities"]["loudnessWriteback"] is True


def test_update_is_persistent_immutable_and_preserves_unrelated_settings(tmp_path: Path) -> None:
    preferences = service(tmp_path)
    original = AppSettings().model_copy(
        update={
            "audio": AppSettings().audio.model_copy(update={"preview_volume": 0.2}),
            "ai": AppSettings().ai.model_copy(update={"env_file": Path("/private/never-read.env")}),
            "library": AppSettings().library.model_copy(update={"watch_for_changes": False}),
        }
    )
    preferences.repository.save(original)
    before = preferences.get_loudness()
    old_settings = preferences.settings
    actual = update(preferences, enabled=False, targetLufs=-18, toleranceLu=1.5)
    assert actual == {"revision": actual["revision"], "enabled": False, "targetLufs": -18.0, "toleranceLu": 1.5}
    assert actual["revision"] != before["revision"]
    assert service(tmp_path).get_loudness() == actual
    assert preferences.loudness_band() == LoudnessBand(-18, 1.5)
    persisted = SettingsRepository(tmp_path / "settings.json").load()
    assert persisted.model_copy(update={"loudness": original.loudness}) == original
    assert old_settings == original and preferences.settings is not old_settings
    assert "/private" not in json.dumps(actual) and "env_file" not in json.dumps(actual)
    assert set(persisted.loudness.model_dump()) == {"enabled", "target_lufs", "tolerance_lu"}


@pytest.mark.parametrize("target,tolerance", [(-30, 0), (0, 10), (-10.25, 2.75)])
def test_inclusive_loudness_limits_are_accepted(tmp_path: Path, target: float, tolerance: float) -> None:
    preferences = service(tmp_path)
    actual = update(preferences, targetLufs=target, toleranceLu=tolerance)
    assert actual["targetLufs"] == target and actual["toleranceLu"] == tolerance


@pytest.mark.parametrize(
    "patch",
    [
        {"enabled": 1},
        {"enabled": "true"},
        {"enabled": None},
        {"targetLufs": -30.1},
        {"targetLufs": 0.1},
        {"targetLufs": float("nan")},
        {"targetLufs": float("inf")},
        {"targetLufs": -(10**400)},
        {"targetLufs": True},
        {"targetLufs": "-10"},
        {"toleranceLu": -0.1},
        {"toleranceLu": 10.1},
        {"toleranceLu": float("nan")},
        {"toleranceLu": 10**400},
        {"toleranceLu": False},
        {"toleranceLu": "2"},
        {"revision": ""},
        {"revision": "A" * 64},
        {"revision": True},
        {"revision": None},
        {"writeTags": True},
        {"tagWritebackEnabled": False},
        {"path": "/private"},
    ],
)
def test_invalid_loudness_updates_never_write_settings(tmp_path: Path, patch: dict[str, Any]) -> None:
    preferences = service(tmp_path)
    before = preferences.get_loudness()
    with pytest.raises(BackendError) as failure:
        preferences.update_loudness({**before, **patch})
    assert failure.value.code == "invalid_params"
    assert preferences.get_loudness() == before
    assert not (tmp_path / "settings.json").exists()


@pytest.mark.parametrize("removed", ["revision", "enabled", "targetLufs", "toleranceLu"])
def test_loudness_update_requires_exact_fields(tmp_path: Path, removed: str) -> None:
    preferences = service(tmp_path)
    params = preferences.get_loudness()
    del params[removed]
    with pytest.raises(BackendError) as failure:
        preferences.update_loudness(params)
    assert failure.value.code == "invalid_params"


def test_stale_revision_reloads_external_changes_without_overwrite(tmp_path: Path) -> None:
    preferences = service(tmp_path)
    before = preferences.get_loudness()
    other = service(tmp_path)
    external = update(other, targetLufs=-22)
    with pytest.raises(BackendError) as failure:
        preferences.update_loudness({**before, "targetLufs": -15})
    assert failure.value.code == "stale_settings"
    assert preferences.get_loudness() == external
    assert preferences.loudness_band() == LoudnessBand(-22, 2)
    ordinary = preferences.execute("settings.get", {})
    preferences.execute(
        "settings.update", {"revision": ordinary["revision"], "previewVolume": 0.1, "watchLibrary": True}
    )
    with pytest.raises(BackendError) as stale:
        other.update_loudness({**external, "enabled": False})
    assert stale.value.code == "stale_settings"
    assert other.get_loudness()["targetLufs"] == -22


def test_concurrent_updates_use_existing_settings_lock(tmp_path: Path) -> None:
    left, right = service(tmp_path), service(tmp_path)
    before = left.get_loudness()
    assert right.get_loudness() == before
    barrier = Barrier(2)

    def write(preferences: PreferencesService, target: float) -> str:
        barrier.wait(timeout=5)
        try:
            preferences.update_loudness({**before, "targetLufs": target})
            return "saved"
        except BackendError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(write, left, -12)
        second = executor.submit(write, right, -18)
        assert sorted((first.result(timeout=5), second.result(timeout=5))) == ["saved", "stale_settings"]
    assert left.get_loudness() == right.get_loudness()


@pytest.mark.parametrize("contents", [b"broken json", b'{"settings_version":999}', b"[]"])
def test_corrupt_settings_keep_existing_recovery_and_paused_loudness(tmp_path: Path, contents: bytes) -> None:
    preferences = service(tmp_path)
    path = tmp_path / "settings.json"
    path.write_bytes(contents)
    actual = preferences.get_loudness()
    assert actual["enabled"] is False and actual["targetLufs"] == -10 and actual["toleranceLu"] == 2
    assert preferences.execute("settings.get", {})["recoveryWarning"] is True
    backups = list(tmp_path.glob("settings.json.recovery-*"))
    assert len(backups) == 1 and backups[0].read_bytes() == contents
    assert update(preferences, enabled=True)["enabled"] is True
    assert preferences.execute("settings.get", {})["recoveryWarning"] is False
    assert backups[0].read_bytes() == contents


@pytest.mark.parametrize("unsafe", ["settings.json", ".settings.lock", "oversized"])
def test_loudness_cannot_bypass_bounded_nofollow_settings(tmp_path: Path, unsafe: str) -> None:
    preferences = service(tmp_path / "data")
    victim = tmp_path / "external.json"
    victim.write_bytes(b'{"loudness":{"enabled":false}}')
    if unsafe == "oversized":
        with (tmp_path / "data" / "settings.json").open("wb") as handle:
            handle.truncate(MAX_SETTINGS_BYTES + 1)
    else:
        (tmp_path / "data" / unsafe).symlink_to(victim)
    with pytest.raises(BackendError) as failure:
        preferences.get_loudness()
    assert failure.value.code == "settings_unavailable"
    assert victim.read_bytes() == b'{"loudness":{"enabled":false}}'


@pytest.mark.parametrize("strategy", ["consistent_loudness", "same_color"])
@pytest.mark.parametrize("explicit_band", [False, True])
def test_prep_forwards_one_exact_band_to_candidate_route_and_domain_builder(
    monkeypatch, strategy: str, explicit_band: bool
) -> None:
    import xfinaudio.headless.prep as prep
    from xfinaudio.application.recommendation_candidates import RecommendationCandidateContext
    from xfinaudio.recommendation.prep_copilot import DJSetIntent

    band = LoudnessBand(-18, 0.75) if explicit_band else DEFAULT_LOUDNESS_BAND
    captured = []

    def candidates(**kwargs):
        captured.append(("candidates", kwargs["loudness_band"]))
        return []

    def context(**kwargs):
        captured.append(("context", kwargs["loudness_band"]))
        return RecommendationCandidateContext(records=[], color_anchor_path="bound-anchor")

    def build(records, intent, **kwargs):
        captured.append(("builder", kwargs["loudness_band"]))
        assert kwargs["color_anchor_path"] == ("bound-anchor" if strategy == "same_color" else None)
        return "domain-result"

    monkeypatch.setattr(prep, "plan_recommendation_candidates", candidates)
    monkeypatch.setattr(prep, "plan_recommendation_candidate_context", context)
    monkeypatch.setattr(prep, "build_prep_copilot_plan", build)

    class BandArguments(TypedDict, total=False):
        loudness_band: LoudnessBand

    kwargs: BandArguments = {"loudness_band": band} if explicit_band else {}
    assert (
        prep.generate_plan([], DJSetIntent(name="Set", strategy=strategy), lambda _: None, **kwargs) == "domain-result"
    )
    assert [name for name, _ in captured] == ["context" if strategy == "same_color" else "candidates", "builder"]
    assert all(actual is band for _, actual in captured)


def test_real_prep_filters_with_configured_band() -> None:
    from tests.test_playlist_service import loudness_track
    from xfinaudio.headless.prep import generate_plan
    from xfinaudio.recommendation.prep_copilot import DJSetIntent

    tracks = [loudness_track(f"/{i}.mp3", -18 if i < 3 else -10) for i in range(6)]
    intent = DJSetIntent(name="Set", strategy="consistent_loudness", target_track_count=3)
    plan = generate_plan(tracks, intent, lambda _: None, loudness_band=LoudnessBand(-18, 0.75))
    assert all(
        {t.path for t in variant.recommendation.ordered_tracks} == {"/0.mp3", "/1.mp3", "/2.mp3"}
        for variant in plan.variants
    )
    assert all(
        variant.recommendation.replacement_policy.loudness_band == LoudnessBand(-18, 0.75) for variant in plan.variants
    )
