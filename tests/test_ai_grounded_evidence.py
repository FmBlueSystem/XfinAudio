"""Metadata/Live AI commentary accepts aggregate evidence only, never actions."""

import json

import pytest

from tests.test_ai_intent_copilot import FakeTransport, message_text
from xfinaudio.ai.structured_assists import explain_grounded_evidence


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    monkeypatch.setenv("XFINAUDIO_AI_ENABLED", "1")
    monkeypatch.setenv("NAN_API_KEY", "synthetic-only")
    monkeypatch.setenv("XFINAUDIO_AI_ENV_FILE", str(tmp_path / "absent"))


def metadata():
    return [
        {"id": "m0", "track_count": 20, "missing_bpm": 2, "missing_key": 3, "missing_energy": 4, "locked_with_gaps": 1}
    ]


def live():
    return [{"id": "c0", "rank": 1, "score": 0.8, "bpm_delta": 1.5, "energy_delta": 1, "readiness": "ready"}]


@pytest.mark.parametrize(("kind", "facts"), [("metadata", metadata()), ("live", live())])
def test_grounded_commentary_calls_configured_adapter_with_only_whitelisted_facts(kind, facts):
    transport = FakeTransport(
        json.dumps({"commentary": "Review the supplied local evidence.", "fact_ids": [facts[0]["id"]]})
    )
    assert explain_grounded_evidence(kind, facts, transport=transport) == "Review the supplied local evidence."
    prompt = message_text(transport)
    assert "Never invent" in prompt
    assert "Never change" in prompt
    assert "private" not in prompt
    assert len(transport.requests) == 1


@pytest.mark.parametrize(
    "response",
    [
        {"commentary": "hello", "fact_ids": ["c99"]},
        {"commentary": "hello", "fact_ids": []},
        {"commentary": "hello", "fact_ids": ["m0", "m0"]},
        {"commentary": "", "fact_ids": ["m0"]},
        {"commentary": "x" * 1201, "fact_ids": ["m0"]},
        {"commentary": "read /private/secret.wav", "fact_ids": ["m0"]},
        {"commentary": "hello", "fact_ids": ["m0"], "write_tags": True},
    ],
)
def test_bad_commentary_rejected_without_mutating_or_echoing(response):
    with pytest.raises(ValueError, match="AI interpretation"):
        explain_grounded_evidence("metadata", metadata(), transport=FakeTransport(json.dumps(response)))


@pytest.mark.parametrize(
    ("kind", "facts"),
    [
        ("other", metadata()),
        ("metadata", []),
        ("metadata", [metadata()[0] | {"path": "/private"}]),
        ("metadata", [metadata()[0] | {"missing_bpm": 21}]),
        ("metadata", [metadata()[0] | {"track_count": True}]),
        ("live", [live()[0] | {"score": float("nan")}]),
        ("live", [live()[0] | {"title": "private title"}]),
        ("live", [live()[0] | {"readiness": "blocked"}]),
        ("live", live() * 2),
    ],
)
def test_untrusted_or_unready_input_fails_before_network(kind, facts):
    transport = FakeTransport("{}")
    with pytest.raises(ValueError):
        explain_grounded_evidence(kind, facts, transport=transport)
    assert not transport.requests


def test_commentary_cannot_hide_an_unknown_candidate_id_in_the_prose():
    transport = FakeTransport('{"commentary":"Choose c99 instead.","fact_ids":["c0"]}')
    with pytest.raises(ValueError, match="AI interpretation"):
        explain_grounded_evidence("live", live(), transport=transport)


def test_live_evidence_declares_percent_normalization_and_nondirectional_energy_gap():
    transport = FakeTransport('{"commentary":"Compare the supplied absolute gaps.","fact_ids":["c0"]}')
    explain_grounded_evidence("live", live(), transport=transport)
    prompt = message_text(transport)
    assert "percentage" in prompt and "half-time normalization" in prompt
    assert "absolute energy-level gap" in prompt
    assert "No increase or decrease direction is supplied" in prompt
    assert "not a probability" in prompt


def test_live_energy_gap_cannot_be_negative_directional_evidence():
    transport = FakeTransport("{}")
    with pytest.raises(ValueError):
        explain_grounded_evidence("live", [live()[0] | {"energy_delta": -2}], transport=transport)
    assert not transport.requests
