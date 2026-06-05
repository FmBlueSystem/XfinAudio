"""GitHub community template publication tests."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUG_REPORT = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md"
FEATURE_REQUEST = PROJECT_ROOT / ".github" / "ISSUE_TEMPLATE" / "feature_request.md"
PULL_REQUEST_TEMPLATE = PROJECT_ROOT / ".github" / "pull_request_template.md"
COMMUNITY_TEMPLATES = [BUG_REPORT, FEATURE_REQUEST, PULL_REQUEST_TEMPLATE]


def read(path: Path) -> str:
    """Read a GitHub community template as text."""
    return path.read_text(encoding="utf-8")


def assert_contains_all(text: str, fragments: list[str]) -> None:
    """Assert that all required fragments are present in text."""
    for fragment in fragments:
        assert fragment in text


def test_github_community_templates_exist() -> None:
    for path in COMMUNITY_TEMPLATES:
        assert path.exists(), f"Missing GitHub community template: {path.relative_to(PROJECT_ROOT)}"


def test_bug_report_template_requests_reproduction_environment_and_safety_evidence() -> None:
    text = read(BUG_REPORT)

    assert_contains_all(
        text,
        [
            "Environment",
            "Steps to reproduce",
            "Expected behavior",
            "Actual behavior",
            "Logs or evidence",
            "Safety constraints",
            "No audio mutation",
            "No live Serato database V2 mutation",
            "app-owned database, settings, or export files",
            "Do not attach private audio files",
        ],
    )


def test_feature_request_template_requests_scope_non_goals_safety_and_manual_qa() -> None:
    text = read(FEATURE_REQUEST)

    assert_contains_all(
        text,
        [
            "Scope",
            "Non-goals",
            "Safety impact",
            "Release impact",
            "GPL-3.0-only",
            "No audio mutation",
            "No live Serato database V2 mutation",
            "Manual QA",
            "real audio",
        ],
    )


def test_pull_request_template_requires_verification_license_safety_and_release_review() -> None:
    text = read(PULL_REQUEST_TEMPLATE)

    assert_contains_all(
        text,
        [
            "Tests run",
            "uv run pytest -q",
            "uv run ruff check .",
            "uv run ruff format --check .",
            "GPL-3.0-only",
            "open-source documentation",
            "No audio mutation",
            "No live Serato database V2 mutation",
            "No binary, release, or legal clearance claims",
            "Release gates",
            "non-audio-release-gates.yml",
        ],
    )
