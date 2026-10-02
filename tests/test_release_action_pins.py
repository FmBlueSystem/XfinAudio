"""Release workflow actions must use reviewed immutable upstream revisions."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APPROVED_PINS = {
    "actions/checkout": ("34e114876b0b11c390a56381ad16ebd13914f8d5", "v4.3.1"),
    "actions/setup-python": ("a26af69be951a213d495a4c3e4e4022e16d87065", "v5.6.0"),
    "actions/setup-node": ("2028fbc5c25fe9cf00d9f06a71cc4710d4507903", "v6.0.0"),
    "astral-sh/setup-uv": ("d0cc045d04ccac9d8b7881df0226f9e82c39688e", "v6.8.0"),
    "actions/upload-artifact": ("ea165f8d65b6e75b540449e92b4886f43607fa02", "v4.6.2"),
}
EXPECTED_ACTION_COUNTS = {
    "non-audio-release-gates.yml": {
        "actions/checkout": 2,
        "actions/setup-python": 1,
        "actions/setup-node": 1,
        "astral-sh/setup-uv": 2,
        "actions/upload-artifact": 2,
    },
    "publish-to-pypi.yml": {
        "actions/checkout": 1,
        "actions/setup-python": 1,
        "astral-sh/setup-uv": 1,
        "actions/upload-artifact": 1,
    },
}


@pytest.mark.parametrize("name", ["non-audio-release-gates.yml", "publish-to-pypi.yml"])
def test_release_actions_use_reviewed_commit_pins(name: str) -> None:
    workflow = (PROJECT_ROOT / ".github/workflows" / name).read_text()
    references = re.findall(r"^\s+uses:\s+(\S+)\s*(.*)$", workflow, re.MULTILINE)
    assert Counter(reference.rsplit("@", 1)[0] for reference, _ in references) == Counter(EXPECTED_ACTION_COUNTS[name])
    for reference, comment in references:
        action, revision = reference.rsplit("@", 1)
        expected_revision, version = APPROVED_PINS[action]
        assert revision == expected_revision
        assert re.fullmatch(r"[0-9a-f]{40}", revision)
        assert comment == f"# {version}"
