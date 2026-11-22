"""One generation reads the whole library once, then only its own tracks (S15).

The fixtures are real FLAC files, so every identity here is a real read: the scanned
fixtures are 2 s long and `tagged_flac` writes a 240 s stream, which makes a "different
recording at the same path" out of a plain tag replacement. A library track the plan's
variants do not list may change while the command runs; a track they do list may not.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import xfinaudio.headless.backend as module
from tests.test_headless_ai_context import FIXTURES
from tests.test_headless_backend import tagged_flac
from xfinaudio.headless.backend import BackendError, HeadlessBackend
from xfinaudio.headless.common import _inside
from xfinaudio.headless.generated_review import GeneratedReview

# The two refusals a generation may answer with, exactly as they are today.
STALE_PREPARATION = "Library sources or settings changed during preparation; regenerate"
STALE_CONTEXT = "The generation context changed; generate a current plan"
CHANGED = ("deleted", "different_recording")


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "music"
    shutil.copytree(FIXTURES, root)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(root)})
    return backend, root


@pytest.fixture
def reads(monkeypatch):
    """Every library read the review makes, by the exact paths it was asked to read."""
    recorded: list[frozenset[str] | None] = []
    build = GeneratedReview._build_sources

    def recording(self, checked, *args, **kwargs):
        recorded.append(checked)
        return build(self, checked, *args, **kwargs)

    monkeypatch.setattr(GeneratedReview, "_build_sources", recording)
    return recorded


def variant_paths(backend: HeadlessBackend) -> set[str]:
    """Every track the plan's variants list: the most a generation's final check reads."""
    assert backend.plan is not None
    return {track.path for variant in backend.plan.variants for track in variant.recommendation.ordered_tracks}


def listed(backend: HeadlessBackend) -> set[str]:
    assert backend.review is not None
    return {track.path for track in backend.review.recommendation.ordered_tracks}


def records(backend: HeadlessBackend):
    return backend.repository.list_tracks()


def mutate(path: Path, case: str) -> None:
    if case == "deleted":
        path.unlink()
    elif case == "moved":
        path.rename(path.with_name("moved-" + path.name))
    elif case == "unreadable":
        path.write_bytes(b"not audio after the scan")
    else:
        tagged_flac(path, 99)


def test_a_generation_reads_the_whole_library_once(library, reads) -> None:
    backend, _ = library
    result = backend.execute("prep.generate", {"targetTrackCount": 4})

    assert len(result["tracks"]) == 4
    assert sum(checked is None for checked in reads) == 1
    # The plan's own final check does read the tracks again, and every later read it makes
    # names only tracks of the plan's variants.
    assert reads[1] and set(reads[1]) <= variant_paths(backend)
    assert all(set(checked) <= variant_paths(backend) for checked in reads[1:])


def test_a_selection_reads_only_the_chosen_variant(library, reads) -> None:
    backend, _ = library
    generated = backend.execute("prep.generate", {"targetTrackCount": 4})
    reads.clear()

    selected = backend.execute("prep.select", {"planId": generated["planId"], "variant": "safe"})

    assert selected["variant"] == "safe"
    assert sum(checked is None for checked in reads) == 0
    assert reads and all(set(checked) <= listed(backend) for checked in reads)


@pytest.mark.parametrize("case", ["deleted", "moved", "unreadable", *CHANGED[1:]])
def test_a_track_that_is_not_its_scanned_recording_enters_no_variant(library, case) -> None:
    backend, root = library
    target = sorted(root.glob("*.flac"))[0]
    mutate(target, case)

    result = backend.execute("prep.generate", {"targetTrackCount": 4})

    assert len(result["tracks"]) == 4
    assert str(target) not in variant_paths(backend)
    assert str(target) not in backend.review_actions.sources


@pytest.mark.parametrize("case", CHANGED)
def test_a_variant_track_that_changes_during_a_generation_is_refused(library, monkeypatch, case) -> None:
    backend, _ = library
    generate = module.generate_plan
    changed: list[Path] = []

    def change_a_variant_track(*args, **kwargs):
        plan = generate(*args, **kwargs)
        path = Path(plan.variants[1].recommendation.ordered_tracks[0].path)
        mutate(path, case)
        changed.append(path)
        return plan

    monkeypatch.setattr(module, "generate_plan", change_a_variant_track)

    with pytest.raises(BackendError) as refused:
        backend.execute("prep.generate", {"targetTrackCount": 4})

    assert str(refused.value) == STALE_PREPARATION
    assert refused.value.code == "stale_plan"
    assert changed
    assert backend.review is None and backend.plan is None


@pytest.mark.parametrize("case", CHANGED)
def test_a_chosen_variant_track_that_changes_during_a_selection_is_refused(library, monkeypatch, case) -> None:
    backend, _ = library
    generated = backend.execute("prep.generate", {"targetTrackCount": 4})
    build = module.build_prep_copilot_variant_application
    changed: list[Path] = []

    def change_the_chosen_variant(variant):
        application = build(variant)
        if variant.name == "safe" and not changed:
            path = Path(application.recommendation.ordered_tracks[0].path)
            mutate(path, case)
            changed.append(path)
        return application

    monkeypatch.setattr(module, "build_prep_copilot_variant_application", change_the_chosen_variant)

    with pytest.raises(BackendError) as refused:
        backend.execute("prep.select", {"planId": generated["planId"], "variant": "safe"})

    assert str(refused.value) == STALE_CONTEXT
    assert refused.value.code == "stale_plan"
    assert changed
    assert backend.review is None and backend.review_id is None


@pytest.mark.parametrize("case", CHANGED)
def test_a_change_to_a_track_in_no_variant_does_not_fail_a_generation(library, monkeypatch, case) -> None:
    backend, _ = library
    generate = module.generate_plan
    changed: list[Path] = []

    def change_an_unlisted_track(*args, **kwargs):
        plan = generate(*args, **kwargs)
        unused = next(
            record
            for record in records(backend)
            if record.path
            not in {track.path for variant in plan.variants for track in variant.recommendation.ordered_tracks}
        )
        mutate(Path(unused.path), case)
        changed.append(Path(unused.path))
        return plan

    monkeypatch.setattr(module, "generate_plan", change_an_unlisted_track)

    result = backend.execute("prep.generate", {"targetTrackCount": 4})

    assert len(result["tracks"]) == 4
    assert changed and str(changed[0]) not in variant_paths(backend)


@pytest.mark.parametrize("case", CHANGED)
def test_a_change_to_a_track_in_no_variant_does_not_fail_a_selection(library, monkeypatch, case) -> None:
    backend, _ = library
    generated = backend.execute("prep.generate", {"targetTrackCount": 4})
    build = module.build_prep_copilot_variant_application
    changed: list[Path] = []

    def change_an_unlisted_track(variant):
        application = build(variant)
        unused = next(record for record in records(backend) if record.path not in variant_paths(backend))
        if not changed:
            mutate(Path(unused.path), case)
            changed.append(Path(unused.path))
        return application

    monkeypatch.setattr(module, "build_prep_copilot_variant_application", change_an_unlisted_track)

    selected = backend.execute("prep.select", {"planId": generated["planId"], "variant": "adventurous"})

    assert selected["variant"] == "adventurous"
    assert changed and str(changed[0]) not in variant_paths(backend)


def test_saving_exporting_and_reviewing_still_verify_their_own_tracks(library, tmp_path) -> None:
    """PRESERVE: every command outside the two touched ones verifies exactly as before."""
    backend, _ = library
    serato = tmp_path / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)
    destination = backend.execute("serato.registerDestination", {"seratoRoot": str(serato)})
    result = backend.execute("prep.generate", {"targetTrackCount": 4})
    source = {"kind": "review", "reviewId": result["reviewId"]}
    destination_id = destination["destinationId"]

    saved = backend.execute("playlist.save", {"name": "Untouched", "reviewId": result["reviewId"]})
    preview = backend.execute("serato.preview", {"source": source, "destinationId": destination_id})
    details = backend.execute("review.details", {"reviewId": result["reviewId"]})

    assert saved["trackCount"] == 4
    assert preview["canCommit"] is True and preview["trackCount"] == 4
    assert details["reviewId"] == result["reviewId"]

    Path(backend.review.recommendation.ordered_tracks[1].path).unlink()

    with pytest.raises(BackendError) as save:
        backend.execute("playlist.save", {"name": "Changed", "reviewId": result["reviewId"]})
    with pytest.raises(BackendError) as reviewing:
        backend.execute("review.details", {"reviewId": result["reviewId"]})
    blocked = backend.execute("serato.preview", {"source": source, "destinationId": destination_id})

    assert (save.value.code, reviewing.value.code) == ("stale_review", "stale_review")
    assert blocked["canCommit"] is False
    assert "Review sources or settings changed; generate a new review" in blocked["blockers"]


def previous_inside(path: Path, root: Path) -> bool:
    """`_inside` before S15: the same path resolved once for each of its two questions."""
    try:
        return path.resolve(strict=True).is_relative_to(root) and path.resolve(strict=True) == path
    except (OSError, RuntimeError):
        return False


def test_inside_answers_like_the_two_resolution_version_and_resolves_once(tmp_path) -> None:
    root = tmp_path / "music"
    root.mkdir()
    existing = root / "track.flac"
    existing.write_bytes(b"a scanned track")
    outside = tmp_path / "elsewhere.flac"
    outside.write_bytes(b"another track")
    linked = tmp_path / "linked.flac"
    linked.symlink_to(existing)
    (tmp_path / "linked-folder").symlink_to(root)
    cases = {
        "existing": (existing, True),
        "the root itself": (root, True),
        "missing": (root / "missing.flac", False),
        "a symlink to a scanned track": (linked, False),
        "a path through a symlinked folder": (tmp_path / "linked-folder" / "track.flac", False),
        "outside the root": (outside, False),
        "a path that only resolves inside": (root / ".." / "music" / "track.flac", False),
        "an unresolvable folder": (root / "gone" / "track.flac", False),
    }
    for name, (path, expected) in cases.items():
        assert _inside(path, root) is expected, name
        assert previous_inside(path, root) is expected, name
        assert _inside(path, root) == previous_inside(path, root), name

    with pytest.MonkeyPatch.context() as patched:
        resolutions: list[Path] = []
        resolve = Path.resolve

        def counting(self, *args, **kwargs):
            resolutions.append(self)
            return resolve(self, *args, **kwargs)

        patched.setattr(Path, "resolve", counting)
        assert _inside(existing, root) is True

        assert resolutions == [existing]
