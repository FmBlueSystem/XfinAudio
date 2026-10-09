"""TDD RED: automatic Serato destination discovery (issue #366).

The export flow must locate a usable `_Serato_` folder without a folder picker.
Candidates, in order: `_Serato_` under each scanned library root, then
`<home>/Music/_Serato_` — the latter only when it shares the library's single
source volume, because `serato.preview` blocks cross-volume destinations.
"""

from pathlib import Path

import pytest

from tests.test_headless_backend import tagged_flac
from xfinaudio.headless.backend import HeadlessBackend
from xfinaudio.headless.serato_discovery import suggest_destination


def _serato_folder(base: Path) -> Path:
    folder = base / "_Serato_"
    (folder / "Subcrates").mkdir(parents=True, exist_ok=True)
    return folder


def test_suggests_serato_folder_under_scanned_library_root(tmp_path: Path) -> None:
    library = tmp_path / "music"
    library.mkdir()
    expected = _serato_folder(library)

    assert suggest_destination([library], home=tmp_path / "home") == expected.resolve()


def test_falls_back_to_home_music_serato_on_the_library_volume(tmp_path: Path) -> None:
    library = tmp_path / "music"
    library.mkdir()
    home = tmp_path / "home"
    expected = _serato_folder(home / "Music")

    def same_volume(_path: Path) -> str:
        return "one-volume"

    assert suggest_destination([library], home=home, volume_of=same_volume) == expected.resolve()


def test_home_fallback_is_skipped_when_library_volume_differs(tmp_path: Path) -> None:
    library = tmp_path / "music"
    library.mkdir()
    home = tmp_path / "home"
    _serato_folder(home / "Music")

    def volumes(path: Path) -> str:
        return "library" if str(path).startswith(str(library)) else "home"

    assert suggest_destination([library], home=home, volume_of=volumes) is None


def test_returns_none_when_no_usable_serato_folder_exists(tmp_path: Path) -> None:
    library = tmp_path / "music"
    library.mkdir()

    assert suggest_destination([library], home=tmp_path / "home") is None


def test_serato_folder_without_subcrates_is_not_usable(tmp_path: Path) -> None:
    library = tmp_path / "music"
    library.mkdir()
    (library / "_Serato_").mkdir()

    assert suggest_destination([library], home=tmp_path / "home") is None


def test_suggestion_is_the_canonical_path_even_through_symlinks(tmp_path: Path) -> None:
    real_library = tmp_path / "real-music"
    real_library.mkdir()
    expected = _serato_folder(real_library)
    library = tmp_path / "linked-music"
    library.symlink_to(real_library)

    assert suggest_destination([library], home=tmp_path / "home") == expected.resolve()


def test_empty_roots_still_suggests_home_music_serato(tmp_path: Path) -> None:
    home = tmp_path / "home"
    expected = _serato_folder(home / "Music")

    assert suggest_destination([], home=home) == expected.resolve()


def test_first_library_root_with_serato_folder_wins(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    expected = _serato_folder(first)
    _serato_folder(second)

    assert suggest_destination([first, second], home=tmp_path / "home") == expected.resolve()


def test_library_root_without_serato_falls_through_to_next_root(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    expected = _serato_folder(second)

    assert suggest_destination([first, second], home=tmp_path / "home") == expected.resolve()


def test_suggestion_signature_rejects_missing_home(tmp_path: Path) -> None:
    library = tmp_path / "music"
    library.mkdir()
    with pytest.raises(TypeError):
        suggest_destination([library])  # type: ignore[call-arg]


def test_backend_suggests_serato_folder_under_scanned_root(tmp_path: Path) -> None:
    music = tmp_path / "music"
    music.mkdir()
    tagged_flac(music / "0.flac", 0)
    serato = music / "_Serato_"
    (serato / "Subcrates").mkdir(parents=True)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})

    assert backend.execute("serato.suggestDestination", {}) == {"suggestion": str(serato.resolve())}


def test_backend_suggestion_falls_back_to_home_music(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    music = tmp_path / "music"
    music.mkdir()
    tagged_flac(music / "0.flac", 0)
    home = tmp_path / "home"
    home_serato = home / "Music" / "_Serato_"
    (home_serato / "Subcrates").mkdir(parents=True)
    monkeypatch.setattr("xfinaudio.headless.serato_export.Path.home", lambda: home)
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})

    result = backend.execute("serato.suggestDestination", {})

    assert result == {"suggestion": str(home_serato.resolve())}


def test_backend_suggestion_is_none_without_usable_serato_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    music = tmp_path / "music"
    music.mkdir()
    tagged_flac(music / "0.flac", 0)
    monkeypatch.setattr("xfinaudio.headless.serato_export.Path.home", lambda: tmp_path / "home")
    backend = HeadlessBackend(tmp_path / "data")
    backend.execute("library.scan", {"root": str(music)})

    assert backend.execute("serato.suggestDestination", {}) == {"suggestion": None}
