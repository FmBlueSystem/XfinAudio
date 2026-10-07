"""Consent, freshness and local Apply use only dummy credentials and fake responses."""

from __future__ import annotations

import io
import json
from dataclasses import fields, is_dataclass
from uuid import uuid4

import pytest

from tests.test_headless_ai_context import improvement_selector
from tests.test_headless_ai_context import setup as setup
from xfinaudio.ai import nan_client
from xfinaudio.headless import ai_execution
from xfinaudio.headless.common import BackendError
from xfinaudio.library.models import TrackRecord
from xfinaudio.library.scan_service import ScanCancellationToken


class FakeTransport:
    def __init__(self):
        self.content = '{"genre":"House","bpm_min":120}'
        self.requests = []
        self.on_send = lambda: None

    def __call__(self, request, *, timeout):
        self.requests.append(request)
        self.on_send()
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": self.content}}]}).encode())


@pytest.fixture
def fixture(setup, tmp_path, monkeypatch):
    from xfinaudio.headless.optional_ai import OptionalAI

    def forbidden(*args, **kwargs):
        raise AssertionError("Real provider requests are forbidden")

    monkeypatch.setattr(nan_client, "_urlopen", forbidden)
    backend, selectors, root = setup
    transport = FakeTransport()
    return OptionalAI(backend, transport=transport), transport, backend, selectors, root


def call(facade, method, params=None, *, token=None, emit=None):
    return facade.execute(method, params or {}, token or ScanCancellationToken(), emit or (lambda _: None))


def configure(facade, root):
    path = root.resolve().parent / "dummy-selected.env"
    path.write_bytes(b"NAN_API_KEY=synthetic-test-only\n")
    status = call(facade, "ai.status")
    selected = call(facade, "ai.credential.set", {"revision": status["revision"], "path": str(path)})
    return call(facade, "ai.settings.update", {"revision": selected["revision"], "enabled": True}), path


def prepare(facade, surface="library", request="House", context=None):
    return call(facade, "ai.prepare", {"surface": surface, "request": request, "context": context or {}})


def run(facade, preview, **kwargs):
    return call(facade, "ai.run", {"previewId": preview["previewId"], "confirmed": True}, **kwargs)


def test_status_and_prepare_are_default_off_metadata_only(fixture, monkeypatch):
    facade, transport, backend, _, root = fixture
    status = call(facade, "ai.status")
    assert not status["enabled"] and not status["configured"]
    assert status["recipient"] == nan_client.DEFAULT_ENDPOINT and status["credentialLabel"] is None
    preview = prepare(facade, request=f"House {root}/private.flac")
    assert preview["disclosure"] and str(root) not in json.dumps(preview)
    assert preview["requestPreview"] != f"House {root}/private.flac"
    assert call(facade, "ai.confirmation", {"previewId": preview["previewId"]}) == preview
    with pytest.raises(BackendError) as failure:
        run(facade, preview)
    assert failure.value.code == "ai_disabled" and not transport.requests
    assert not (backend.data_dir / "settings.json").exists()


def test_credential_selection_does_not_read_contents_or_enable_ai(fixture, monkeypatch):
    import os

    facade, transport, _, _, root = fixture
    path = root.resolve().parent / "dummy-selected.env"
    path.write_bytes(b"not read during selection")
    revision = call(facade, "ai.status")["revision"]
    with monkeypatch.context() as guard:
        guard.setattr(os, "read", lambda *args: pytest.fail("Credential read without request confirmation"))
        selected = call(facade, "ai.credential.set", {"revision": revision, "path": str(path)})
        assert not selected["enabled"] and selected["configured"]
        preview = prepare(facade)
        assert any(path.name in item for item in preview["disclosure"])
        call(facade, "ai.confirmation", {"previewId": preview["previewId"]})
    assert str(path.parent) not in json.dumps(selected)
    enabled = call(facade, "ai.settings.update", {"revision": selected["revision"], "enabled": True})
    cleared = call(facade, "ai.credential.set", {"revision": enabled["revision"], "path": None})
    assert cleared["enabled"] and not cleared["configured"] and not transport.requests


@pytest.mark.parametrize("confirmed", [False, 1, "true", None])
def test_run_requires_exact_confirmation(fixture, confirmed):
    facade, transport, _, _, root = fixture
    configure(facade, root)
    preview = prepare(facade)
    with pytest.raises(BackendError):
        call(facade, "ai.run", {"previewId": preview["previewId"], "confirmed": confirmed})
    assert not transport.requests


def test_one_pending_preview_and_single_use_confirmed_run(fixture):
    facade, transport, _, _, root = fixture
    configure(facade, root)
    first, second = prepare(facade), prepare(facade)
    with pytest.raises(BackendError) as failure:
        run(facade, first)
    assert failure.value.code == "stale_ai"
    result = run(facade, second)
    assert result["cancelled"] is False and result["result"]["kind"] == "filters"
    with pytest.raises(BackendError) as replay:
        run(facade, second)
    assert replay.value.code == "stale_ai" and len(transport.requests) == 1


def test_apply_is_local_does_not_save_or_change_audio_and_does_not_trust_returned_mutations(fixture):
    facade, transport, backend, _, root = fixture
    configure(facade, root)
    before = {path: path.read_bytes() for path in root.iterdir()}
    playlists = backend.execute("playlist.list", {})
    records = backend.repository.list_tracks()
    settings = (backend.data_dir / "settings.json").read_bytes()
    progress = []
    result = run(facade, prepare(facade), emit=progress.append)["result"]
    result["proposal"]["genre"] = "caller-forged"
    applied = call(facade, "ai.apply", {"resultId": result["resultId"]})
    assert applied["surface"] == "library" and applied["data"]["filters"]["genre"] == "House"
    assert applied["data"]["trackIds"] and len(transport.requests) == 1
    assert all(item["phase"] == "ai" and set(item) <= {"phase", "processedCount", "totalCount"} for item in progress)
    assert backend.execute("playlist.list", {}) == playlists
    assert backend.repository.list_tracks() == records
    assert (backend.data_dir / "settings.json").read_bytes() == settings
    assert all(path.read_bytes() == content for path, content in before.items())


@pytest.mark.parametrize("stage", ["before", "progress", "during"])
def test_cancel_prevents_late_result_publication(fixture, stage):
    facade, transport, _, _, root = fixture
    configure(facade, root)
    preview = prepare(facade)
    token = ScanCancellationToken()
    if stage == "before":
        token.cancel()
    elif stage == "during":
        transport.on_send = token.cancel
    result = run(facade, preview, token=token, emit=lambda _: token.cancel() if stage == "progress" else None)
    assert result == {"cancelled": True, "result": None}
    assert len(transport.requests) == (1 if stage == "during" else 0)
    assert not facade.results


@pytest.mark.parametrize("stage", ["before_run", "during_run", "before_apply"])
@pytest.mark.parametrize("change", ["source", "settings", "credential"])
def test_stale_sources_settings_and_credentials_never_publish_or_apply(fixture, stage, change):
    facade, transport, backend, _, root = fixture
    _, credential_path = configure(facade, root)
    preview = prepare(facade)

    def mutate():
        if change == "source":
            (root / "track-1.flac").unlink()
        elif change == "settings":
            status = backend.preferences.get_loudness()
            backend.preferences.update_loudness({**status, "targetLufs": -18})
        else:
            credential_path.write_bytes(b"synthetic-replaced")

    if stage == "before_run":
        mutate()
    elif stage == "during_run":
        transport.on_send = mutate
    if stage == "before_apply":
        answer = run(facade, preview)["result"]
        mutate()
    with pytest.raises(BackendError) as failure:
        if stage == "before_apply":
            call(facade, "ai.apply", {"resultId": answer["resultId"]})
        else:
            run(facade, preview)
    assert failure.value.code == "stale_ai"
    if stage == "before_run":
        assert not transport.requests


def test_config_mutations_invalidate_pending_and_cached_answers(fixture):
    facade, _, _, _, root = fixture
    configure(facade, root)
    answer = run(facade, prepare(facade))["result"]
    preview = prepare(facade)
    status = call(facade, "ai.status")
    call(facade, "ai.settings.update", {"revision": status["revision"], "enabled": False})
    assert not facade.results
    for method, params in [
        ("ai.run", {"previewId": preview["previewId"], "confirmed": True}),
        ("ai.apply", {"resultId": answer["resultId"]}),
    ]:
        with pytest.raises(BackendError) as failure:
            call(facade, method, params)
        assert failure.value.code == "stale_ai"


@pytest.mark.parametrize("content", ["{}", '{"genre":"unknown"}', '{"energy_min":true}', "not JSON"])
def test_invalid_model_results_have_safe_code_and_no_cached_answer(fixture, content):
    facade, transport, _, _, root = fixture
    configure(facade, root)
    transport.content = content
    with pytest.raises(BackendError) as failure:
        run(facade, prepare(facade))
    assert failure.value.code == "invalid_ai_response" and not facade.results
    assert content not in str(failure.value)


def test_transport_exception_does_not_expose_raw_secret_or_path(fixture):
    facade, transport, _, _, root = fixture
    _, path = configure(facade, root)

    def fail():
        raise RuntimeError(f"synthetic-test-only {path} RAW_PROVIDER_RESPONSE")

    transport.on_send = fail
    with pytest.raises(BackendError) as failure:
        run(facade, prepare(facade))
    assert not any(item in str(failure.value) for item in (str(path), "synthetic-test-only", "RAW_PROVIDER_RESPONSE"))
    assert not facade.results


def test_result_cache_is_bounded_and_keeps_current_older_answers(fixture):
    facade, transport, _, _, root = fixture
    configure(facade, root)
    results = [run(facade, prepare(facade))["result"] for _ in range(17)]
    assert len(facade.results) == 16
    with pytest.raises(BackendError):
        call(facade, "ai.apply", {"resultId": results[0]["resultId"]})
    assert call(facade, "ai.apply", {"resultId": results[1]["resultId"]})["surface"] == "library"

    def assert_answer_only(value):
        assert not isinstance(value, TrackRecord)
        if is_dataclass(value):
            for field in fields(value):
                assert_answer_only(getattr(value, field.name))
        elif isinstance(value, dict):
            for item in value.values():
                assert_answer_only(item)
        elif isinstance(value, (tuple, list)):
            for item in value:
                assert_answer_only(item)

    # Each cached answer keeps the request-scoped context used to revalidate Apply;
    # the retained answers themselves stay metadata-free and bounded.
    for completed in facade.results.values():
        assert_answer_only(completed.answer)
    assert len(transport.requests) == 17


@pytest.mark.parametrize("change", ["request", "surface", "scope", "invalid_request"])
def test_new_request_reference_revokes_completed_results_without_transmission(fixture, change):
    facade, transport, _, selectors, root = fixture
    configure(facade, root)
    if change == "scope":
        transport.content = '{"action":"find","selected_ids":["s0"]}'
        first = prepare(facade, "saved", "Find a set", selectors["saved"])
    else:
        first = prepare(facade, request="House above 120 BPM")
    answer = run(facade, first)["result"]
    if change == "request":
        prepare(facade, request="Only tracks below 100 BPM")
    elif change == "surface":
        prepare(facade, "prep", "Prepare four House tracks")
    elif change == "scope":
        prepare(facade, "saved", "Find a set", {"playlistIds": selectors["saved"]["playlistIds"][:1]})
    else:
        with pytest.raises(BackendError):
            prepare(facade, request="x" * 2001)
    with pytest.raises(BackendError) as stale:
        call(facade, "ai.apply", {"resultId": answer["resultId"]})
    assert stale.value.code == "stale_ai"
    assert not facade.results and len(transport.requests) == 1


def test_switching_back_to_an_old_request_does_not_revive_its_completed_result(fixture):
    facade, transport, _, _, root = fixture
    configure(facade, root)
    old = run(facade, prepare(facade, request="House above 120 BPM"))["result"]
    prepare(facade, request="Only tracks below 100 BPM")
    prepare(facade, request="House above 120 BPM")
    with pytest.raises(BackendError) as stale:
        call(facade, "ai.apply", {"resultId": old["resultId"]})
    assert stale.value.code == "stale_ai" and len(transport.requests) == 1


def test_prepare_during_inflight_request_rejects_old_completion(fixture):
    facade, transport, _, _, root = fixture
    configure(facade, root)
    first = prepare(facade, request="House above 120 BPM")
    transport.on_send = lambda: prepare(facade, request="Only tracks below 100 BPM")
    with pytest.raises(BackendError) as stale:
        run(facade, first)
    assert stale.value.code == "stale_ai"
    assert not facade.results and len(transport.requests) == 1


@pytest.mark.parametrize(
    "surface,prompt,content",
    [
        ("prep", "Warmup", '{"name":"Warmup","strategy":"warmup","target_track_count":4}'),
        ("editor", "Shorten to 2", '{"operation":"shorten_tracks","target":2}'),
        ("saved", "Compare sets", '{"action":"compare","selected_ids":["s0","s1"]}'),
        ("review", "", "Synthetic commentary about the local set."),
        ("metadata", "", '{"commentary":"Missing fields need review.","fact_ids":["m0"]}'),
        ("live", "", '{"commentary":"Candidate c0 is locally ranked.","fact_ids":["c0"]}'),
        ("connection", "Reply with OK. XfinAudio connection test.", "OK"),
    ],
)
def test_all_remaining_original_surfaces_and_local_apply(fixture, surface, prompt, content):
    facade, transport, _, selectors, root = fixture
    configure(facade, root)
    transport.content = content
    answer = run(facade, prepare(facade, surface, prompt, selectors.get(surface)))["result"]
    assert answer["surface"] == surface and len(transport.requests) == 1
    if answer["canApply"]:
        assert call(facade, "ai.apply", {"resultId": answer["resultId"]})["surface"] == surface
    else:
        with pytest.raises(BackendError):
            call(facade, "ai.apply", {"resultId": answer["resultId"]})


@pytest.mark.parametrize(
    "method,params",
    [
        ("ai.status", {"path": "/private"}),
        ("ai.prepare", {"surface": [], "request": "x", "context": {}}),
        ("ai.prepare", {"surface": "library", "request": "x", "context": {}, "transport": "bad"}),
        ("ai.prepare", {"surface": "library", "request": "x", "context": {}, "timeout": 120}),
        ("ai.run", {"previewId": str(uuid4()), "confirmed": True, "timeout": 120}),
        ("ai.confirmation", {"previewId": "bad"}),
        ("ai.run", {"previewId": str(uuid4()), "confirmed": True}),
        ("ai.apply", {"resultId": "bad"}),
        ("ai.credential.set", {"revision": "0" * 64, "path": "relative.env"}),
        ("unknown", {}),
    ],
)
def test_untrusted_fields_fail_without_network(fixture, method, params):
    facade, transport, _, _, _ = fixture
    with pytest.raises(BackendError):
        call(facade, method, params)
    assert not transport.requests


# --- I2b: stable editor improvement disclosure and freshness ------------------


def test_editor_improvement_prepare_discloses_without_contacting_provider(fixture):
    facade, transport, backend, _, _ = fixture
    selector, opened = improvement_selector(backend, include_replacements=True)
    preview = call(facade, "ai.prepare", {"surface": "editor", "request": "Sube la energía", "context": selector})
    assert transport.requests == []
    assert preview["surface"] == "editor" and preview["recipient"] == nan_client.DEFAULT_ENDPOINT
    assert str(len(opened["tracks"])) in preview["disclosure"][0]
    assert "pseudónimos" in " ".join(preview["disclosure"])
    assert call(facade, "ai.confirmation", {"previewId": preview["previewId"]}) == preview
    assert transport.requests == []


def test_editor_improvement_freshness_accepts_identical_selector_and_rejects_library_change(fixture):
    facade, _, backend, _, root = fixture
    selector, _ = improvement_selector(backend)
    preview = call(facade, "ai.prepare", {"surface": "editor", "request": "Mejora el orden", "context": selector})
    assert call(facade, "ai.confirmation", {"previewId": preview["previewId"]}) == preview
    (root / "track-1.flac").unlink()
    with pytest.raises(BackendError) as error:
        call(facade, "ai.confirmation", {"previewId": preview["previewId"]})
    assert error.value.code == "stale_ai"


def test_editor_improvement_freshness_rejects_changed_saved_revision(fixture):
    facade, _, backend, _, _ = fixture
    selector, _ = improvement_selector(backend)
    preview = call(facade, "ai.prepare", {"surface": "editor", "request": "Mejora el orden", "context": selector})
    backend.playlists.update_name(backend.playlists.list_summaries()[0].id, "External rename")
    with pytest.raises(BackendError) as error:
        call(facade, "ai.confirmation", {"previewId": preview["previewId"]})
    assert error.value.code == "stale_ai"


# --- I2c: prepare-time token snapshot, execution, and explicit Apply binding ---


@pytest.fixture
def offline_setup(setup, monkeypatch):
    """The I2c improvement tests inject a fake transport; the real opener stays forbidden."""

    def forbidden(*args, **kwargs):
        raise AssertionError("Real provider requests are forbidden")

    monkeypatch.setattr(nan_client, "_urlopen", forbidden)
    backend, _, root = setup
    return backend, root


class ImprovementTransport:
    """Fake transport that can only answer with tokens read from the request payload."""

    def __init__(self, order=None, rationale: str | None = "Orden local sugerido."):
        self.requests = []
        self.order = order
        self.rationale = rationale
        self.on_send = lambda: None

    def __call__(self, request, *, timeout):
        body = json.loads(request.data.decode("utf-8"))
        payload = json.loads(body["messages"][-1]["content"])
        candidates = payload["context"]["candidates"]
        tokens = [item["token"] for item in candidates]
        self.requests.append(payload)
        self.on_send()
        content = {"orderedTrackIds": self.order(tokens, candidates) if self.order else list(reversed(tokens))}
        if self.rationale is not None:
            content["rationale"] = self.rationale
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": json.dumps(content)}}]}).encode())


def improvement_facade(backend, root, transport):
    from xfinaudio.headless.optional_ai import OptionalAI

    facade = OptionalAI(backend, transport=transport)
    configure(facade, root)
    return facade


def prepare_improvement(facade, selector, request="Mejora el orden"):
    return call(facade, "ai.prepare", {"surface": "editor", "request": request, "context": selector})


def test_editor_improvement_run_sends_only_tokens_and_apply_binds_preview(offline_setup):
    backend, root = offline_setup
    selector, opened = improvement_selector(backend)
    before_playlist = backend.playlists.get_by_id(opened["playlistId"])
    audio = {path: path.read_bytes() for path in root.iterdir()}
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)

    preview = prepare_improvement(facade, selector)
    assert transport.requests == []
    assert call(facade, "ai.confirmation", {"previewId": preview["previewId"]}) == preview
    assert transport.requests == []
    assert "draftIds" not in json.dumps(preview)
    answer = run(facade, preview)["result"]
    assert answer["surface"] == "editor" and answer["kind"] == "improvement" and answer["canApply"]

    payload = transport.requests[0]
    assert set(payload) == {"request", "context"}
    assert set(payload["context"]) == {"candidates"}
    assert payload["request"] == "Mejora el orden"
    allowed = {"token", "title", "artist", "genre", "bpm", "key", "energy", "duration", "status", "missingFields"}
    body = json.dumps(payload)
    assert str(root) not in body and "path" not in body
    assert all(set(item) == allowed for item in payload["context"]["candidates"])
    assert all(draft_id not in body for draft_id in selector["draftIds"])
    assert all(len(item["token"]) == 16 for item in payload["context"]["candidates"])

    applied = call(facade, "ai.apply", {"resultId": answer["resultId"]})
    data = applied["data"]
    assert applied["surface"] == "editor"
    assert data["proposalId"] and len(data["digest"]) == 64
    assert [track["id"] for track in data["before"]] == selector["draftIds"]
    assert [track["id"] for track in data["after"]] == list(reversed(selector["draftIds"]))
    assert data["addedIds"] == [] and data["removedIds"] == []
    assert data["assessment"]["readiness"] in {"ready", "needs_review"}
    assert all("path" not in track for track in (*data["before"], *data["after"]))
    assert backend.playlists.get_by_id(opened["playlistId"]) == before_playlist
    assert backend.editor.session is not None and backend.editor.session.proposal is not None
    assert all(path.read_bytes() == content for path, content in audio.items())


def test_editor_improvement_apply_keeps_prepare_time_token_snapshot(offline_setup):
    from xfinaudio.headless.ai_context import build_context

    backend, root = offline_setup
    selector, _ = improvement_selector(backend)
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)
    answer = run(facade, prepare_improvement(facade, selector))["result"]
    completed = facade.results[answer["resultId"]]
    original = completed.context.data["candidates"]
    fresh = build_context(backend, "editor", selector, "Mejora el orden")
    assert fresh.revision == completed.context.revision
    assert fresh.data["candidates"].tokens != original.tokens

    applied = call(facade, "ai.apply", {"resultId": answer["resultId"]})["data"]
    bound = backend.editor.session.proposal
    assert bound is not None
    assert bound.source_tokens == original.draft_tokens
    assert bound.order_tokens == tuple(answer["proposal"]["orderedTrackIds"])
    assert [track["id"] for track in applied["before"]] == selector["draftIds"]


def test_editor_improvement_apply_previews_authorized_replacement_without_saving(offline_setup):
    backend, root = offline_setup
    selector, opened = improvement_selector(backend, include_replacements=True)
    before_playlist = backend.playlists.get_by_id(opened["playlistId"])
    draft_count = len(selector["draftIds"])

    def order(tokens, candidates):
        draft, pool = tokens[:draft_count], tokens[draft_count:]
        assert pool
        return [draft[0], pool[0], *draft[1:]]

    transport = ImprovementTransport(order=order)
    facade = improvement_facade(backend, root, transport)
    answer = run(facade, prepare_improvement(facade, selector))["result"]
    applied = call(facade, "ai.apply", {"resultId": answer["resultId"]})["data"]
    after_ids = [track["id"] for track in applied["after"]]
    assert len(after_ids) == draft_count + 1
    assert applied["addedIds"] == [after_ids[1]] and applied["removedIds"] == []
    assert after_ids[0] == selector["draftIds"][0] and after_ids[2:] == selector["draftIds"][1:]
    assert after_ids[1] not in selector["draftIds"]
    assert backend.editor.session is not None and backend.editor.session.proposal is not None
    assert backend.playlists.get_by_id(opened["playlistId"]) == before_playlist


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param(lambda tokens: [*tokens[:-1], "0" * 16], id="unknown-token"),
        pytest.param(lambda tokens: [tokens[0], tokens[0], *tokens[1:]], id="duplicate-token"),
        pytest.param(lambda tokens: [*tokens[:-1], "a" * 64], id="stable-id"),
        pytest.param(lambda tokens: [*tokens[:-1], tokens[0][:15]], id="short-token"),
        pytest.param(lambda tokens: tokens[0], id="non-list"),
    ],
)
def test_editor_improvement_invalid_token_responses_produce_no_edit(offline_setup, bad):
    backend, root = offline_setup
    selector, opened = improvement_selector(backend)
    before_playlist = backend.playlists.get_by_id(opened["playlistId"])
    transport = ImprovementTransport(order=lambda tokens, candidates: bad(tokens))
    facade = improvement_facade(backend, root, transport)
    with pytest.raises(BackendError) as failure:
        run(facade, prepare_improvement(facade, selector))
    assert failure.value.code == "invalid_ai_response"
    assert not facade.results
    assert backend.editor.session is not None and backend.editor.session.proposal is None
    assert backend.playlists.get_by_id(opened["playlistId"]) == before_playlist


@pytest.mark.parametrize(
    "rationale",
    [
        pytest.param("control\x00character", id="control-character"),
        pytest.param("x" * 401, id="over-400"),
        pytest.param("see /Users/private/secret.flac", id="path"),
    ],
)
def test_editor_improvement_invalid_rationale_produces_no_edit(offline_setup, rationale):
    backend, root = offline_setup
    selector, opened = improvement_selector(backend)
    before_playlist = backend.playlists.get_by_id(opened["playlistId"])
    transport = ImprovementTransport(rationale=rationale)
    facade = improvement_facade(backend, root, transport)
    with pytest.raises(BackendError) as failure:
        run(facade, prepare_improvement(facade, selector))
    assert failure.value.code == "invalid_ai_response"
    assert not facade.results
    assert backend.editor.session is not None and backend.editor.session.proposal is None
    assert backend.playlists.get_by_id(opened["playlistId"]) == before_playlist


@pytest.mark.parametrize("stage", ["before_send", "after_receive", "apply"])
@pytest.mark.parametrize("change", ["saved", "library"])
def test_editor_improvement_stale_revision_never_binds(offline_setup, stage, change):
    backend, root = offline_setup
    selector, opened = improvement_selector(backend)
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)

    def mutate():
        if change == "saved":
            backend.playlists.update_name(opened["playlistId"], "External rename")
        else:
            (root / "track-1.flac").unlink()

    preview = prepare_improvement(facade, selector)
    if stage == "before_send":
        mutate()
    elif stage == "after_receive":
        transport.on_send = mutate
    if stage == "apply":
        answer = run(facade, preview)["result"]
        mutate()
        with pytest.raises(BackendError) as failure:
            call(facade, "ai.apply", {"resultId": answer["resultId"]})
    else:
        with pytest.raises(BackendError) as failure:
            run(facade, preview)
    assert failure.value.code == "stale_ai"
    assert not facade.results
    assert backend.editor.session is not None and backend.editor.session.proposal is None


def test_editor_improvement_repeated_prepare_does_not_revive_old_result(offline_setup):
    backend, root = offline_setup
    selector, _ = improvement_selector(backend)
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)
    first = run(facade, prepare_improvement(facade, selector))["result"]
    prepare_improvement(facade, selector)
    with pytest.raises(BackendError) as failure:
        call(facade, "ai.apply", {"resultId": first["resultId"]})
    assert failure.value.code == "stale_ai"
    assert not facade.results
    assert backend.editor.session is not None and backend.editor.session.proposal is None
    assert len(transport.requests) == 1


def test_editor_improvement_session_swap_rejects_apply(offline_setup):
    backend, root = offline_setup
    selector, opened = improvement_selector(backend)
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)
    answer = run(facade, prepare_improvement(facade, selector))["result"]
    backend.execute("playlist.edit.discard", {"editId": opened["editId"]})
    with pytest.raises(BackendError) as failure:
        call(facade, "ai.apply", {"resultId": answer["resultId"]})
    assert failure.value.code == "stale_ai"
    assert backend.editor.session is not None and backend.editor.session.proposal is None


def test_editor_improvement_denied_confirmation_never_transmits_or_binds(offline_setup):
    backend, root = offline_setup
    selector, _ = improvement_selector(backend)
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)
    preview = prepare_improvement(facade, selector)
    with pytest.raises(BackendError) as failure:
        call(facade, "ai.run", {"previewId": preview["previewId"], "confirmed": False})
    assert failure.value.code == "confirmation_required"
    assert transport.requests == []
    assert backend.editor.session is not None and backend.editor.session.proposal is None


@pytest.mark.parametrize(
    "stage,expected_code",
    [
        pytest.param("assessment", "invalid_edit", id="assessment-failure"),
        pytest.param("tracks", "ai_unavailable", id="render-failure"),
    ],
)
def test_editor_improvement_failed_preview_never_leaves_a_bound_proposal(
    offline_setup, monkeypatch, stage, expected_code
):
    """A failing assessment or before/after render must not bind a proposal.

    Binding is the only mutation of the edit session, so every path that can fail has
    to be computed first: a failure after binding would leave a proposal the renderer
    never saw and that `playlist.edit.save_improvement` would happily persist.
    """
    backend, root = offline_setup
    selector, opened = improvement_selector(backend)
    before_playlist = backend.playlists.get_by_id(opened["playlistId"])
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)
    answer = run(facade, prepare_improvement(facade, selector))["result"]

    def fail(*args, **kwargs):
        raise ValueError("Scan this saved set first: real track metadata is required for musical validation.")

    if stage == "assessment":
        monkeypatch.setattr(ai_execution, "assess_playlist_edit", fail)
    else:
        monkeypatch.setattr(backend.editor, "_tracks", fail)

    with pytest.raises(BackendError) as failure:
        call(facade, "ai.apply", {"resultId": answer["resultId"]})
    assert failure.value.code == expected_code
    assert backend.editor.session is not None and backend.editor.session.proposal is None
    assert backend.playlists.get_by_id(opened["playlistId"]) == before_playlist


@pytest.mark.parametrize(
    "content,expected",
    [
        ('{"operation":"shorten_tracks","target":2}', "shorten to 2 tracks"),
        ('{"operation":"shorten_minutes","target":90}', "shorten to 90 minutes"),
        ('{"operation":"rising_energy"}', "raise energy"),
        ('{"operation":"falling_energy"}', "lower energy"),
    ],
)
def test_legacy_editor_four_operation_apply_is_unchanged(fixture, content, expected):
    facade, transport, backend, selectors, root = fixture
    configure(facade, root)
    transport.content = content
    answer = run(facade, prepare(facade, "editor", "Acorta a 2 temas", selectors["editor"]))["result"]
    assert answer["kind"] == "editor_request"
    assert call(facade, "ai.apply", {"resultId": answer["resultId"]}) == {
        "surface": "editor",
        "data": {"request": expected},
    }
    assert backend.editor.session is not None and backend.editor.session.proposal is None
    assert "candidates" not in transport.requests[0].data.decode("utf-8")


# --- F6: provider-free exact payload inspection -------------------------------


def test_payload_inspection_returns_the_exact_retained_body_without_any_request(fixture):
    facade, transport, backend, _, root = fixture
    preview = prepare(facade, request="House bpm 120-130")
    assert transport.requests == []
    with pytest.raises(BackendError) as missing:
        call(facade, "ai.payload", {"previewId": str(uuid4())})
    assert missing.value.code == "stale_ai"

    inspected = call(facade, "ai.payload", {"previewId": preview["previewId"]})
    assert transport.requests == []
    assert inspected["previewId"] == preview["previewId"] and inspected["surface"] == "library"
    assert inspected["recipient"] == nan_client.DEFAULT_ENDPOINT
    assert inspected["request"] == "House bpm 120-130"
    assert inspected["truncated"] is False and inspected["bytes"] == len(inspected["body"].encode("utf-8"))
    body = json.loads(inspected["body"])
    assert body["model"] and [message["role"] for message in body["messages"]] == ["system", "user"]
    payload = json.loads(body["messages"][-1]["content"])
    assert set(payload) == {"request", "context"} and set(payload["context"]) == {"genres"}
    assert str(root) not in inspected["body"] and "path" not in json.dumps(payload)
    # Read-only: the retained pending state and the bounded result history are untouched.
    assert facade.preview is not None and facade.preview.id == preview["previewId"]
    assert facade.results == {}
    assert call(facade, "ai.confirmation", {"previewId": preview["previewId"]}) == preview


def test_payload_inspection_never_reads_credentials_and_never_needs_consent(fixture, monkeypatch):
    import os

    facade, transport, _, _, root = fixture
    _, path = configure(facade, root)
    preview = prepare(facade)
    with monkeypatch.context() as guard:
        guard.setattr(os, "read", lambda *args: pytest.fail("Credential read without a confirmed request"))
        inspected = call(facade, "ai.payload", {"previewId": preview["previewId"]})
    assert transport.requests == []
    assert path.name not in inspected["body"] and str(path) not in json.dumps(inspected)


def test_payload_inspection_fails_stale_when_the_context_changed(fixture):
    facade, _, backend, _, root = fixture
    selector, _ = improvement_selector(backend)
    preview = call(facade, "ai.prepare", {"surface": "editor", "request": "Mejora el orden", "context": selector})
    (root / "track-1.flac").unlink()
    with pytest.raises(BackendError) as failure:
        call(facade, "ai.payload", {"previewId": preview["previewId"]})
    assert failure.value.code == "stale_ai"


def test_payload_inspection_serializes_exactly_the_retained_improvement_candidates(offline_setup):
    backend, root = offline_setup
    selector, _ = improvement_selector(backend)
    transport = ImprovementTransport()
    facade = improvement_facade(backend, root, transport)
    preview = prepare_improvement(facade, selector)
    assert facade.preview is not None
    retained = facade.preview.context.data["candidates"]

    inspected = call(facade, "ai.payload", {"previewId": preview["previewId"]})
    assert transport.requests == []
    body = inspected["body"]
    payload = json.loads(json.loads(body)["messages"][-1]["content"])
    assert set(payload) == {"request", "context"} and set(payload["context"]) == {"candidates"}
    candidates = payload["context"]["candidates"]
    assert [item["token"] for item in candidates] == list(retained.tokens)
    allowed = {"token", "title", "artist", "genre", "bpm", "key", "energy", "duration", "status", "missingFields"}
    assert all(set(item) == allowed for item in candidates)
    context_json = json.dumps(payload)
    assert str(root) not in context_json and "path" not in context_json
    assert all(draft_id not in context_json for draft_id in selector["draftIds"])
    assert facade.preview.context.data["candidates"] is retained


def test_payload_inspection_truncates_honestly_at_the_outbound_cap(fixture, monkeypatch):
    from xfinaudio.headless import optional_ai as module

    facade, transport, _, _, _ = fixture
    preview = prepare(facade)
    monkeypatch.setattr(module, "MAX_PAYLOAD_PREVIEW_BYTES", 64)
    inspected = call(facade, "ai.payload", {"previewId": preview["previewId"]})
    assert inspected["truncated"] is True
    assert inspected["bytes"] > 64
    assert len(inspected["body"].encode("utf-8")) <= 64
    assert transport.requests == []


# --- F9: the model's bounded rationale reaches the user as prose --------------


def test_improvement_result_shows_the_bounded_rationale_as_prose(offline_setup):
    backend, root = offline_setup
    selector, _ = improvement_selector(backend)
    transport = ImprovementTransport(rationale="Menos saltos de energía entre pistas.")
    facade = improvement_facade(backend, root, transport)
    answer = run(facade, prepare_improvement(facade, selector))["result"]
    assert answer["kind"] == "improvement" and answer["canApply"]
    assert answer["text"] == "Menos saltos de energía entre pistas."


def test_improvement_result_without_rationale_keeps_the_fixed_local_review_text(offline_setup):
    backend, root = offline_setup
    selector, _ = improvement_selector(backend)
    transport = ImprovementTransport(rationale=None)
    facade = improvement_facade(backend, root, transport)
    answer = run(facade, prepare_improvement(facade, selector))["result"]
    assert answer["text"] == "Revisa el orden propuesto y su evaluación local antes de aplicarlo al borrador."
