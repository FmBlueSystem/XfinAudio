"""Real language adapters receive only their documented facts through an offline fake transport."""

import io
import json
import shutil
from pathlib import Path

import pytest
from mutagen.flac import FLAC

from xfinaudio.ai.nan_client import request_context
from xfinaudio.application.playlist_improvement import (
    MAX_DRAFT_TRACKS,
    MAX_REPLACEMENT_CANDIDATES,
)
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


def improvement_selector(backend, *, include_replacements: bool = False):
    """Open the first saved playlist and describe its ordered public draft ids."""
    playlist_id = backend.playlists.list_summaries()[0].id
    opened = backend.execute("playlist.edit.open", {"playlistId": playlist_id})
    return (
        {
            "editId": opened["editId"],
            "draftIds": [track["id"] for track in opened["tracks"]],
            "includeReplacements": include_replacements,
        },
        opened,
    )


# --- I2b: stable editor improvement context and disclosure --------------------


def test_editor_improvement_context_discloses_exact_counts_fields_and_pseudonyms(setup):
    backend, _, root = setup
    selector, opened = improvement_selector(backend, include_replacements=True)
    context = build_context(backend, "editor", selector, "Sube la energía del cierre")
    disclosure = " ".join(context.disclosure)
    candidates = context.data["candidates"]
    assert context.surface == "editor" and context.selector == selector
    assert len(candidates.draft_tokens) == len(opened["tracks"])
    assert 0 < len(candidates.replacement_tokens) <= MAX_REPLACEMENT_CANDIDATES
    assert str(len(candidates.draft_tokens)) in context.disclosure[0]
    assert str(len(candidates.replacement_tokens)) in context.disclosure[0]
    assert "incluidas" in context.disclosure[0]
    for field in ("token", "title", "artist", "genre", "bpm", "key", "energy", "duration", "status", "missingFields"):
        assert field in disclosure
    assert "pseudónimos" in disclosure and "no anonimato" in disclosure
    assert "títulos" in disclosure and "artistas" in disclosure
    assert "rutas" in disclosure and "audio" in disclosure and "credenciales" in disclosure
    assert "aprobación" in disclosure
    assert str(root) not in json.dumps(list(context.disclosure))


def test_editor_improvement_without_replacements_reports_zero_and_excluded(setup):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend, include_replacements=False)
    context = build_context(backend, "editor", selector, "Reordena el set")
    assert context.data["candidates"].replacement_tokens == ()
    assert "0" in context.disclosure[0]
    assert "excluidas" in context.disclosure[0]


def test_editor_improvement_revision_is_stable_and_never_contains_tokens(setup):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend, include_replacements=True)
    first = build_context(backend, "editor", selector, "Mejora el orden")
    second = build_context(backend, "editor", selector, "Mejora el orden")
    assert first.revision == second.revision
    assert all(token not in first.revision for token in first.data["candidates"].tokens)


def test_editor_improvement_revision_tracks_draft_order_and_library_state(setup):
    backend, _, root = setup
    selector, _ = improvement_selector(backend)
    before = build_context(backend, "editor", selector, "Mejora el orden")
    reordered = {**selector, "draftIds": list(reversed(selector["draftIds"]))}
    assert build_context(backend, "editor", reordered, "Mejora el orden").revision != before.revision
    (root / "track-1.flac").unlink()
    assert build_context(backend, "editor", selector, "Mejora el orden").revision != before.revision


def test_editor_improvement_over_cap_draft_fails_before_candidate_allocation(setup, monkeypatch):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend)

    def forbidden(*args, **kwargs):
        raise AssertionError("candidate allocation must not run for an over-cap draft")

    monkeypatch.setattr(backend.editor, "improvement_candidates", forbidden)
    over_cap = {**selector, "draftIds": [f"{index:064x}" for index in range(MAX_DRAFT_TRACKS + 1)]}
    with pytest.raises(BackendError) as error:
        build_context(backend, "editor", over_cap, "Mejora el orden")
    assert error.value.code == "ai_context_too_large"


@pytest.mark.parametrize(
    "draft_ids,code",
    [
        ("not-a-list", "invalid_params"),
        ([], "invalid_params"),
        (["0" * 64], "invalid_params"),
        (["not-hex-" + "0" * 56, "1" * 64], "invalid_params"),
        (["0" * 63, "1" * 64], "invalid_params"),
        (["0" * 64, "0" * 64], "invalid_edit"),
    ],
)
def test_editor_improvement_rejects_malformed_draft_ids(setup, draft_ids, code):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend)
    bad = {**selector, "draftIds": draft_ids}
    with pytest.raises(BackendError) as error:
        build_context(backend, "editor", bad, "Mejora el orden")
    assert error.value.code == code


@pytest.mark.parametrize("value", [0, 1, "true", None])
def test_editor_improvement_requires_boolean_replacements(setup, value):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend)
    bad = {**selector, "includeReplacements": value}
    with pytest.raises(BackendError) as error:
        build_context(backend, "editor", bad, "Mejora el orden")
    assert error.value.code == "invalid_params"


def test_editor_improvement_selector_shape_is_exact(setup):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend)
    draft_ids = selector["draftIds"]
    for bad in (
        {"editId": selector["editId"], "draftIds": draft_ids},
        {"editId": selector["editId"], "includeReplacements": False},
        {"editId": selector["editId"], "draftIds": draft_ids, "includeReplacements": False, "extra": 1},
        {"editId": selector["editId"], "draftIds": draft_ids, "includeReplacements": False, "revision": "0" * 64},
    ):
        with pytest.raises(BackendError) as error:
            build_context(backend, "editor", bad, "Mejora el orden")
        assert error.value.code == "invalid_params"


def test_editor_improvement_rejects_unknown_session_track_without_echo(setup):
    backend, _, root = setup
    selector, _ = improvement_selector(backend)
    forged = {**selector, "draftIds": [*selector["draftIds"], "f" * 64]}
    with pytest.raises(BackendError) as error:
        build_context(backend, "editor", forged, "Mejora el orden")
    assert error.value.code == "invalid_edit"
    assert str(root) not in str(error.value) and "f" * 64 not in str(error.value)


def test_editor_improvement_rejects_changed_saved_revision(setup):
    backend, _, _ = setup
    selector, opened = improvement_selector(backend)
    build_context(backend, "editor", selector, "Mejora el orden")
    backend.playlists.update_name(opened["playlistId"], "External rename")
    with pytest.raises(BackendError) as error:
        build_context(backend, "editor", selector, "Mejora el orden")
    assert error.value.code == "stale_edit"


def test_legacy_editor_selector_keeps_four_operation_disclosure(setup):
    backend, _, root = setup
    _, opened = improvement_selector(backend)
    context = build_context(backend, "editor", {"editId": opened["editId"]}, "Acorta a 2 temas")
    assert context.disclosure == (
        "Solo tu petición de edición, sin rutas.",
        "No se envían títulos, listas de pistas ni audio. La propuesta requiere previsualización local.",
    )
    assert "candidates" not in context.data
    assert str(root) not in json.dumps(list(context.disclosure))


def test_editor_improvement_preserves_submitted_draft_order(setup):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend)
    first = build_context(backend, "editor", selector, "Mejora el orden")
    reversed_selector = {**selector, "draftIds": list(reversed(selector["draftIds"]))}
    second = build_context(backend, "editor", reversed_selector, "Mejora el orden")
    first_paths = [first.data["candidates"].paths_by_token[token] for token in first.data["candidates"].draft_tokens]
    second_paths = [second.data["candidates"].paths_by_token[token] for token in second.data["candidates"].draft_tokens]
    assert second_paths == list(reversed(first_paths))


def test_editor_improvement_redacts_request_paths(setup):
    backend, _, root = setup
    selector, _ = improvement_selector(backend)
    target = root / "track-1.flac"
    context = build_context(backend, "editor", selector, f"Improve {target}")
    assert str(target) not in context.request


def test_editor_improvement_revision_changes_with_replacement_opt_in(setup):
    backend, _, _ = setup
    selector, _ = improvement_selector(backend)
    without = {**selector, "includeReplacements": False}
    with_pool = {**selector, "includeReplacements": True}
    assert (
        build_context(backend, "editor", without, "x").revision
        != build_context(backend, "editor", with_pool, "x").revision
    )
