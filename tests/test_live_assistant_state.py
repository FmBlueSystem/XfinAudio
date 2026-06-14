"""Tests for LiveAssistantState — pure Python, no Qt."""

from datetime import datetime

import pytest

from xfinaudio.desktop.live_assistant_state import LiveAssistantState
from xfinaudio.library.models import TrackRecord


@pytest.fixture()
def track_a() -> TrackRecord:
    return TrackRecord(
        path="/a.flac",
        title="Track A",
        artist="Artist A",
        bpm=128.0,
        camelot_key="11B",
        energy_level=7,
        metadata_status="complete",
    )


@pytest.fixture()
def track_b() -> TrackRecord:
    return TrackRecord(
        path="/b.flac",
        title="Track B",
        artist="Artist B",
        bpm=129.0,
        camelot_key="12B",
        energy_level=7,
        metadata_status="complete",
    )


@pytest.fixture()
def track_c() -> TrackRecord:
    return TrackRecord(
        path="/c.flac",
        title="Track C",
        artist="Artist C",
        bpm=135.0,
        camelot_key="3A",
        energy_level=8,
        metadata_status="complete",
    )


class TestLiveAssistantState:
    def test_empty_state_has_no_current_track(self) -> None:
        state = LiveAssistantState()
        assert state.current_track is None
        assert state.history == []
        assert state.candidates == []
        assert state.alert_flags == []

    def test_set_current_track_updates_state(self, track_a: TrackRecord) -> None:
        state = LiveAssistantState()
        new_state = state.set_current_track(track_a)
        assert new_state.current_track == track_a
        assert new_state.history == []

    def test_load_next_moves_current_to_history_and_sets_new_current(
        self, track_a: TrackRecord, track_b: TrackRecord
    ) -> None:
        state = LiveAssistantState(current_track=track_a)
        loaded_at = datetime(2026, 6, 8, 14, 30, 0)
        new_state = state.load_next(track_b, loaded_at=loaded_at)

        assert new_state.current_track == track_b
        assert len(new_state.history) == 1
        assert new_state.history[0].track == track_a
        assert new_state.history[0].order == 1
        assert new_state.history[0].loaded_at == loaded_at

    def test_load_next_increments_order(self, track_a: TrackRecord, track_b: TrackRecord, track_c: TrackRecord) -> None:
        state = LiveAssistantState(current_track=track_a)
        state = state.load_next(track_b, loaded_at=datetime(2026, 6, 8, 14, 30, 0))
        state = state.load_next(track_c, loaded_at=datetime(2026, 6, 8, 14, 35, 0))

        assert state.current_track == track_c
        assert len(state.history) == 2
        assert state.history[0].order == 1
        assert state.history[1].order == 2

    def test_clear_resets_to_empty(self, track_a: TrackRecord, track_b: TrackRecord) -> None:
        state = LiveAssistantState(current_track=track_a)
        state = state.load_next(track_b, loaded_at=datetime(2026, 6, 8, 14, 30, 0))
        cleared = state.clear()

        assert cleared.current_track is None
        assert cleared.history == []
        assert cleared.candidates == []

    def test_generate_alerts_empty_when_no_current_track(self, track_b: TrackRecord) -> None:
        state = LiveAssistantState(candidates=[track_b])
        alerts = state.generate_alerts()
        assert alerts == []

    def test_generate_alerts_bpm_guardrail(self, track_a: TrackRecord, track_c: TrackRecord) -> None:
        # track_a: 128 BPM, track_c: 135 BPM → difference = 5.5%
        state = LiveAssistantState(current_track=track_a, candidates=[track_c])
        alerts = state.generate_alerts()

        bpm_alerts = [a for a in alerts if a.alert_type == "bpm_guardrail"]
        assert len(bpm_alerts) == 1
        assert bpm_alerts[0].track_path == track_c.path
        assert "BPM" in bpm_alerts[0].message

    def test_generate_alerts_key_clash(self, track_a: TrackRecord) -> None:
        # track_a: 11B, incompatible_track: 3A
        incompatible_track = TrackRecord(
            path="/d.flac",
            title="Track D",
            artist="Artist D",
            bpm=128.0,
            camelot_key="3A",
            energy_level=7,
            metadata_status="complete",
        )
        state = LiveAssistantState(current_track=track_a, candidates=[incompatible_track])
        alerts = state.generate_alerts()

        key_alerts = [a for a in alerts if a.alert_type == "key_clash"]
        assert len(key_alerts) == 1
        assert key_alerts[0].track_path == incompatible_track.path

    def test_generate_alerts_energy_jump(self, track_a: TrackRecord) -> None:
        # track_a: energy 7, low_energy: energy 4 → jump of 3
        low_energy = TrackRecord(
            path="/e.flac",
            title="Track E",
            artist="Artist E",
            bpm=128.0,
            camelot_key="11B",
            energy_level=4,
            metadata_status="complete",
        )
        state = LiveAssistantState(current_track=track_a, candidates=[low_energy])
        alerts = state.generate_alerts()

        energy_alerts = [a for a in alerts if a.alert_type == "energy_jump"]
        assert len(energy_alerts) == 1
        assert energy_alerts[0].track_path == low_energy.path

    def test_generate_alerts_no_alerts_for_safe_candidate(self, track_a: TrackRecord, track_b: TrackRecord) -> None:
        # track_b: 129 BPM (0.8% diff), 12B (compatible), energy 7 (same)
        state = LiveAssistantState(current_track=track_a, candidates=[track_b])
        alerts = state.generate_alerts()
        assert alerts == []

    def test_set_candidates_updates_candidate_list(self, track_a: TrackRecord, track_b: TrackRecord) -> None:
        state = LiveAssistantState(current_track=track_a)
        new_state = state.set_candidates([track_b])
        assert new_state.candidates == [track_b]
