from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLAN_DOC = PROJECT_ROOT / "docs" / "macos-signing-notarization-dmg-plan.md"
PACKAGING_STRATEGY_DOC = PROJECT_ROOT / "docs" / "packaging-strategy.md"
RELEASE_CANDIDATE_EVIDENCE_DOC = PROJECT_ROOT / "docs" / "release-candidate-evidence.md"
OPEN_SOURCE_RELEASE_BACKLOG_DOC = PROJECT_ROOT / "docs" / "open-source-release-backlog.md"


def _doc_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_macos_distribution_plan_records_planning_only_status_and_non_goals() -> None:
    doc_text = _doc_text(PLAN_DOC)
    lower_text = doc_text.lower()

    assert "# macOS Developer ID signing, notarization, and DMG plan" in doc_text
    assert "Status: planning only / not executed" in doc_text
    assert (
        "No signing, notarization, DMG creation, publishing, or release artifact creation is performed by this plan."
        in doc_text
    )

    forbidden_claims = [
        "signing completed",
        "notarization completed",
        "notarized app is ready",
        "dmg completed",
        "installer completed",
        "release artifact created",
    ]
    for claim in forbidden_claims:
        assert claim not in lower_text


def test_macos_distribution_plan_lists_required_gates_and_verification_commands() -> None:
    doc_text = _doc_text(PLAN_DOC)

    required_fragments = [
        "Clean macOS account validation complete",
        "PyInstaller unexpected warnings: 0",
        "Release notes drafted",
        "Manual desktop QA evidence recorded",
        "Apple Developer Program membership and Team ID available",
        "Developer ID Application certificate available",
        "notarytool credentials configured securely",
        "codesign --verify --deep --strict --verbose=2",
        "spctl --assess --type execute --verbose",
        "xcrun notarytool submit",
        "--wait",
        "xcrun stapler staple",
        "xcrun stapler validate",
        "spctl --assess --type open --verbose",
    ]
    for fragment in required_fragments:
        assert fragment in doc_text


def test_macos_distribution_plan_covers_dmg_secrets_evidence_and_failure_triage() -> None:
    doc_text = _doc_text(PLAN_DOC)

    required_fragments = [
        "candidate tools: `hdiutil` first; `create-dmg` may be evaluated later",
        "Applications drag target",
        "must not mutate app-owned data or user library data",
        "mount, open, copy, and launch",
        (
            "Never commit Apple IDs, app-specific passwords, keychain profiles, certificates, "
            "private keys, or logs containing credentials."
        ),
        "Signing identity hash",
        "Notarization UUID",
        "Staple validation output",
        "Clean-account install/launch result",
        "Signing identity missing",
        "Hardened runtime or entitlements issue",
        "Notarization rejection",
        "Qt/PySide bundle issue",
        "Quarantine or Gatekeeper failure",
    ]
    for fragment in required_fragments:
        assert fragment in doc_text


def test_release_docs_reference_macos_distribution_plan_without_claiming_completion() -> None:
    strategy_text = _doc_text(PACKAGING_STRATEGY_DOC)
    evidence_text = _doc_text(RELEASE_CANDIDATE_EVIDENCE_DOC)

    assert "docs/macos-signing-notarization-dmg-plan.md" in strategy_text
    assert "docs/macos-signing-notarization-dmg-plan.md" in evidence_text
    assert "planning only / not executed" in strategy_text.lower()
    assert "signing, notarization, and dmg creation remain pending" in evidence_text.lower()


def test_open_source_backlog_keeps_signing_notarization_and_dmg_distribution_pending() -> None:
    backlog_text = _doc_text(OPEN_SOURCE_RELEASE_BACKLOG_DOC)
    lower_text = backlog_text.lower()

    required_rows = {
        "Developer ID signing plan": (
            "Pending: follow `docs/macos-signing-notarization-dmg-plan.md`; generated `.app` must be "
            "signed only after clean-account and warning gates pass."
        ),
        "Notarization plan": (
            "Pending: follow `docs/macos-signing-notarization-dmg-plan.md`; notarization and stapling must "
            "be verified before binary redistribution claims."
        ),
        "DMG distribution plan": (
            "Pending: follow `docs/macos-signing-notarization-dmg-plan.md`; DMG layout and "
            "mount/copy/launch checks remain unexecuted."
        ),
    }
    for item, acceptance in required_rows.items():
        row = next(line for line in backlog_text.splitlines() if f"| {item} |" in line)
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        assert cells == ["P1", item, acceptance]

    forbidden_claims = [
        "developer id signing | completed",
        "notarization plan | completed",
        "dmg distribution plan | completed",
        "installer completed",
        "notarized app is ready",
    ]
    for claim in forbidden_claims:
        assert claim not in lower_text
