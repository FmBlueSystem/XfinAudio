"""Immutable batched profile publication matches existing single-result semantics."""

from xfinaudio.audio.danceability import DanceabilityProfile
from xfinaudio.audio.loudness import LoudnessProfile, LoudnessStatus
from xfinaudio.audio.spectral_profile import EdgeSpectralProfile, SpectralProfile
from xfinaudio.desktop import app_state_transitions as transitions
from xfinaudio.desktop.app_state import AppState
from xfinaudio.library.models import TrackRecord


def test_batch_matches_all_four_profile_transitions_and_preserves_original() -> None:
    records = [TrackRecord(path=f"/{i}.flac", title=f"Track {i}") for i in range(4)]
    state = AppState().with_scanned_records(records)
    spectral = SpectralProfile(red_ratio=1, green_ratio=0, blue_ratio=0, dominant_color="RED")
    dance = DanceabilityProfile(score=0.7, pulse_clarity=0.8, tempo_confidence=0.9, percussive_ratio=0.6)
    edge = EdgeSpectralProfile(intro=spectral, outro=spectral)
    loudness = LoudnessProfile(
        lufs_integrated=None,
        loudness_range_lra=None,
        true_peak_dbtp=None,
        status=LoudnessStatus.UNMEASURABLE,
        engine_fingerprint="synthetic",
    )
    expected = transitions.apply_spectral_profile(state, path=records[0].path, profile=spectral)
    expected = transitions.apply_danceability_profile(expected, path=records[0].path, profile=dance)
    expected = transitions.apply_edge_spectral_profile(expected, path=records[1].path, profile=edge)
    expected = transitions.apply_loudness_profile(expected, path=records[2].path, profile=loudness)
    apply_batch = getattr(transitions, "apply_profile_batch", None)
    assert callable(apply_batch), "batched profile transition is missing"

    actual = apply_batch(
        state,
        {
            records[0].path: {"spectral_profile": spectral, "danceability_profile": dance},
            records[1].path: {"edge_spectral_profile": edge},
            records[2].path: {"loudness_profile": loudness},
            "/unknown.flac": {"spectral_profile": spectral},
        },
    )

    assert actual == expected
    assert actual.scanned_records is not state.scanned_records
    assert actual.records_by_path is not state.records_by_path
    assert actual.scanned_records[3] is records[3]
    assert all(actual.records_by_path[r.path] is r for r in actual.scanned_records)
    assert all(r.spectral_profile is None and r.loudness_profile is None for r in records)
    assert "/unknown.flac" not in actual.records_by_path


def test_batch_copies_each_changed_record_once_and_preserves_snapshot_fields(monkeypatch) -> None:
    records = [TrackRecord(path=f"/{i}.flac") for i in range(1000)]
    state = AppState(is_completing_loudness=True, loudness_total_count=1000).with_scanned_records(records)
    copies = []
    original = TrackRecord.model_copy

    def counted_copy(self, **kwargs):
        copies.append(self.path)
        return original(self, **kwargs)

    monkeypatch.setattr(TrackRecord, "model_copy", counted_copy)
    apply_batch = getattr(transitions, "apply_profile_batch", None)
    assert callable(apply_batch), "batched profile transition is missing"
    actual = apply_batch(
        state,
        {r.path: {"spectral_profile": None, "danceability_profile": None} for r in records},
        state_updates={"loudness_progress_count": 1000},
    )

    assert len(copies) == len(records)
    assert actual.loudness_progress_count == actual.loudness_total_count == 1000
    assert actual.is_completing_loudness is True
    assert state.loudness_progress_count == 0
