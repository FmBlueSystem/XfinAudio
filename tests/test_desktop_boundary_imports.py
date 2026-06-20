from __future__ import annotations

from pathlib import Path


def test_desktop_does_not_export_recommendation_candidate_policy() -> None:
    assert not Path("src/xfinaudio/desktop/recommendation_presenter.py").exists()

    this_file = Path(__file__).resolve()
    references = [
        path
        for root in (Path("src"), Path("tests"))
        for path in root.rglob("*.py")
        if path.resolve() != this_file and "from xfinaudio.desktop.recommendation_presenter" in path.read_text()
    ]
    assert references == []
