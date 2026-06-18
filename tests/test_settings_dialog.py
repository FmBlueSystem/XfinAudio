"""Tests for SettingsDialog reset action and genre enrichment panel."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit, QMessageBox, QPushButton

from xfinaudio.config.settings import AppSettings, ExportSettings
from xfinaudio.desktop.settings_dialog import SettingsDialog
from xfinaudio.genre.settings import (
    DEFAULT_LLM_TIEBREAKER_MODEL,
    DEFAULT_LLM_TIEBREAKER_URL,
    GenreEnrichmentSettings,
)


def test_settings_dialog_has_reset_button(qapp: QApplication) -> None:
    """The settings dialog exposes a Reset to Defaults button."""
    dialog = SettingsDialog(AppSettings())
    button = dialog.findChild(QPushButton, "reset_to_defaults_button")
    assert button is not None
    assert "reset" in button.text().lower()


def test_reset_button_emits_default_settings(qapp: QApplication, monkeypatch: Any) -> None:
    """Clicking the reset button emits settings_changed with AppSettings defaults."""
    custom = AppSettings(export=ExportSettings(safe_export_folder=Path("/custom")))
    dialog = SettingsDialog(custom)

    monkeypatch.setattr(
        QMessageBox,
        "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )

    captured: list[AppSettings] = []
    dialog.settings_changed.connect(captured.append)

    dialog._reset_to_defaults()

    assert len(captured) == 1
    assert captured[0] == AppSettings()
    assert captured[0].export.safe_export_folder is None


# ---------------------------------------------------------------------------
# Genre enrichment panel
# ---------------------------------------------------------------------------


def test_settings_dialog_has_genre_enrichment_group(qapp: QApplication) -> None:
    dialog = SettingsDialog(AppSettings())
    assert dialog._genre_enabled is not None
    assert not dialog._genre_enabled.isChecked()  # default off


def test_genre_enrichment_panel_starts_with_defaults(qapp: QApplication) -> None:
    dialog = SettingsDialog(AppSettings())
    # Default GenreEnrichmentSettings: enabled=False, no providers, no keys
    for key in ("lastfm", "spotify", "deezer"):
        assert not dialog._provider_toggles[key].isChecked()
        assert dialog._api_key_fields[key].text() == ""
    assert not dialog._llm_enabled.isChecked()
    assert dialog._llm_url.text() == DEFAULT_LLM_TIEBREAKER_URL
    assert dialog._llm_model.text() == DEFAULT_LLM_TIEBREAKER_MODEL


def test_genre_enrichment_panel_populates_from_existing_settings(qapp: QApplication) -> None:
    settings = AppSettings(
        genre_enrichment=GenreEnrichmentSettings(
            enabled=True,
            providers={"lastfm": True, "spotify": False, "deezer": True},
            api_keys={"lastfm": "sk-last", "spotify": "id:sec"},
            llm_tiebreaker_enabled=True,
            llm_tiebreaker_url="http://localhost:9999/api/generate",
            llm_tiebreaker_model="qwen",
        )
    )
    dialog = SettingsDialog(settings)
    assert dialog._genre_enabled.isChecked()
    assert dialog._provider_toggles["lastfm"].isChecked()
    assert not dialog._provider_toggles["spotify"].isChecked()
    assert dialog._provider_toggles["deezer"].isChecked()
    assert dialog._api_key_fields["lastfm"].text() == "sk-last"
    assert dialog._api_key_fields["spotify"].text() == "id:sec"
    assert dialog._llm_enabled.isChecked()
    assert dialog._llm_url.text() == "http://localhost:9999/api/generate"
    assert dialog._llm_model.text() == "qwen"


def test_genre_enrichment_panel_reads_back_via_current_settings(qapp: QApplication) -> None:
    """Editing widgets and calling _current_genre_settings() round-trips."""
    settings = AppSettings(genre_enrichment=GenreEnrichmentSettings())
    dialog = SettingsDialog(settings)
    dialog._genre_enabled.setChecked(True)
    dialog._provider_toggles["lastfm"].setChecked(True)
    dialog._api_key_fields["lastfm"].setText("sk-abc")
    dialog._llm_enabled.setChecked(True)
    dialog._llm_model.setText("mistral")

    snapshot = dialog._current_genre_settings()

    assert snapshot.enabled is True
    assert snapshot.providers == {"lastfm": True, "spotify": False, "deezer": False}
    assert snapshot.api_keys == {"lastfm": "sk-abc", "spotify": "", "deezer": ""}
    assert snapshot.llm_tiebreaker_enabled is True
    assert snapshot.llm_tiebreaker_model == "mistral"


def test_settings_dialog_accept_emits_updated_genre_settings(qapp: QApplication) -> None:
    """OK click emits settings_changed with the current genre enrichment state."""
    settings = AppSettings(genre_enrichment=GenreEnrichmentSettings())
    dialog = SettingsDialog(settings)
    dialog._genre_enabled.setChecked(True)
    dialog._provider_toggles["deezer"].setChecked(True)

    captured: list[AppSettings] = []
    dialog.settings_changed.connect(captured.append)

    dialog.accept()

    assert len(captured) == 1
    assert captured[0].genre_enrichment.enabled is True
    assert captured[0].genre_enrichment.providers["deezer"] is True
    assert captured[0].genre_enrichment.providers["lastfm"] is False


def test_settings_dialog_preserves_non_ui_genre_settings(qapp: QApplication) -> None:
    settings = AppSettings(
        genre_enrichment=GenreEnrichmentSettings(
            source_trust={"discogs": 0.7, "lastfm": 0.4},
            min_score_threshold=0.35,
            margin_threshold=0.25,
            low_confidence_floor=0.55,
        )
    )
    dialog = SettingsDialog(settings)
    captured: list[AppSettings] = []
    dialog.settings_changed.connect(captured.append)

    dialog.accept()

    genre_settings = captured[0].genre_enrichment
    assert genre_settings.source_trust == {"discogs": 0.7, "lastfm": 0.4}
    assert genre_settings.min_score_threshold == 0.35
    assert genre_settings.margin_threshold == 0.25
    assert genre_settings.low_confidence_floor == 0.55


def test_genre_enrichment_panel_defaults_to_inert_state(qapp: QApplication) -> None:
    """Fresh settings must produce a panel that is fully inert (Scenario 1.3)."""
    dialog = SettingsDialog(AppSettings())
    checkboxes = dialog.findChildren(QCheckBox)
    line_edits = dialog.findChildren(QLineEdit)

    # Master enable + 3 provider toggles + LLM enable = 5 checkboxes
    assert len(checkboxes) == 5
    assert all(not cb.isChecked() for cb in checkboxes)
    # 3 API key fields + URL + model = 5 line edits, all empty/default
    for le in line_edits:
        assert le.text() in {"", DEFAULT_LLM_TIEBREAKER_URL, DEFAULT_LLM_TIEBREAKER_MODEL}


def test_genre_enrichment_panel_api_key_fields_use_password_echo(qapp: QApplication) -> None:
    """API key fields use password echo so keys are not visible on screen."""
    dialog = SettingsDialog(AppSettings())
    for key in ("lastfm", "spotify", "deezer"):
        assert dialog._api_key_fields[key].echoMode() == QLineEdit.EchoMode.Password
