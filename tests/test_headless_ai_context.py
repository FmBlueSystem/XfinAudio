"""Real language adapters receive only their documented facts through an offline fake transport."""

import io
import json
import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from xfinaudio.ai.nan_client import request_context
from xfinaudio.headless.ai_context import apply_context, build_context, execute_context
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.common import BackendError

FIXTURES = Path(__file__).resolve().parents[1] / "desktop-electron/tests/fixtures/music"


@pytest.fixture
def setup(tmp_path):
    root = tmp_path / "music"
    shutil.copytree(FIXTURES, root)
    gap = root / "gap.flac"
    shutil.copyfile(root / "track-1.flac", gap)
    tags = FLAC(gap)
    tags.pop("initialkey", None)
    tags.save()
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    review = backend.execute("prep.generate", {"targetTrackCount": 4, "name": "Fixture review"})
    first = backend.execute("playlist.save", {"name": "First private name", "reviewId": review["reviewId"]})
    second = backend.execute("playlist.duplicate", {"playlistId": first["id"]})
    edit = backend.execute("playlist.edit.open", {"playlistId": first["id"]})
    live = backend.execute("live.open", {"reviewId": review["reviewId"]})
    return (
        backend,
        {
            "review": {"reviewId": review["reviewId"]},
            "editor": {"editId": edit["editId"]},
            "saved": {"playlistIds": [str(first["id"]), str(second["id"])]},
            "live": {"sessionId": live["sessionId"], "revision": live["revision"]},
        },
        root,
    )


@pytest.mark.parametrize(
    "surface,prompt,content,kind",
    [
        ("library", "House bpm 120-130", '{"genre":"House","bpm_min":120,"bpm_max":130}', "filters"),
        ("prep", "Warmup de 4 temas", '{"name":"Warmup","strategy":"warmup","target_track_count":4}', "intent"),
        ("editor", "Acorta a 2 temas", '{"operation":"shorten_tracks","target":2}', "editor_request"),
        (
            "saved",
            "Compara First private name y su copia",
            '{"action":"compare","selected_ids":["s0","s1"]}',
            "saved_selection",
        ),
        ("review", "", "Comentario sobre los datos locales.", "commentary"),
        (
            "metadata",
            "",
            '{"commentary":"Los campos ausentes requieren revisión local.","fact_ids":["m0"]}',
            "commentary",
        ),
        (
            "live",
            "",
            '{"commentary":"La candidata c0 tiene una puntuación local disponible.","fact_ids":["c0"]}',
            "commentary",
        ),
        ("connection", "Reply with OK. XfinAudio connection test.", "OK", "connection"),
    ],
)
def test_all_original_surfaces_use_offline_real_adapters(setup, surface, prompt, content, kind):
    backend, selectors, root = setup
    context = build_context(backend, surface, selectors.get(surface, {}), prompt)
    requests = []
    timeouts = []

    def transport(req, *, timeout):
        requests.append(req.data.decode())
        timeouts.append(timeout)
        return io.BytesIO(json.dumps({"choices": [{"message": {"content": content}}]}).encode())

    with request_context(enabled=True, key_provider=lambda: "dummy-test-only"):
        answer = execute_context(context, transport)
    assert answer["kind"] == kind
    assert len(requests) == 1
    assert timeouts == [{"prep": 60, "review": 120, "connection": 10}.get(surface, 30)]
    assert str(root) not in requests[0]
    if surface == "saved":
        assert "First private name" not in requests[0]
    if surface not in {"review", "prep"}:
        assert "Electron test" not in requests[0]
    if answer["canApply"]:
        applied = apply_context(backend, context, answer)
        assert applied["surface"] == surface
    else:
        assert answer["proposal"] is None
    assert backend.playlists.get_by_id(1).name == "First private name"


def test_metadata_omits_unavailable_lock_counts_and_discloses_missing_context(setup):
    backend, _, _ = setup
    context = build_context(backend, "metadata", {}, "")
    assert "locked_with_gaps" not in context.data["facts"][0]
    requests = []

    def transport(req, *, timeout):
        requests.append(json.loads(req.data))
        return io.BytesIO(
            json.dumps(
                {"choices": [{"message": {"content": '{"commentary":"Review missing fields.","fact_ids":["m0"]}'}}]}
            ).encode()
        )

    with request_context(enabled=True, key_provider=lambda: "dummy-test-only"):
        execute_context(context, transport)
    body = requests[0]
    facts = json.loads(body["messages"][-1]["content"])["context"]["facts"]
    assert "locked_with_gaps" not in facts[0]
    system = body["messages"][0]["content"]
    assert "No locked-track selection is supplied" in system
    assert "Actual repair priority is locked tracks first" not in system


def test_context_revision_rejects_external_source_changes(setup):
    backend, _, root = setup
    before = build_context(backend, "library", {}, "House")
    (root / "track-1.flac").unlink()
    after = build_context(backend, "library", {}, "House")
    assert before.revision != after.revision


@pytest.mark.parametrize(
    "surface,context,prompt",
    [
        ("unknown", {}, "text"),
        ("library", {"path": "/secret"}, "text"),
        ("review", {}, ""),
        ("editor", {"editId": "bad"}, "shorten"),
        ("live", {"sessionId": "bad", "revision": 0}, ""),
        ("connection", {}, "send my music"),
        ("metadata", {}, "private custom text"),
        ("library", {}, ""),
        ("saved", {"playlistIds": ["999"]}, "Find"),
    ],
)
def test_invalid_or_unavailable_context_never_reaches_provider(setup, surface, context, prompt):
    backend, _, _ = setup
    with pytest.raises((BackendError, ValueError)):
        build_context(backend, surface, context, prompt)


@pytest.mark.parametrize("surface,selector,prompt", [([], {}, "x"), ("saved", {"playlistIds": [{}]}, "x")])
def test_bad_nested_context_types_fail_as_typed_input_errors(setup, surface, selector, prompt):
    backend, _, _ = setup
    with pytest.raises(BackendError):
        build_context(backend, surface, selector, prompt)
