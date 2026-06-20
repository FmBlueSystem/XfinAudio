from __future__ import annotations

from pathlib import Path
from unittest.mock import patch


def test_application_formats_spectral_color_through_audio_formatter() -> None:
    from xfinaudio.application.spectral_profile_display import format_application_spectral_color
    from xfinaudio.audio.spectral_profile import SpectralProfile

    profile = SpectralProfile(red_ratio=0.1, green_ratio=0.2, blue_ratio=0.7, dominant_color="BLUE")

    with patch(
        "xfinaudio.application.spectral_profile_display._format_spectral_color", return_value="🔵 BLUE"
    ) as formatter:
        result = format_application_spectral_color(profile)

    formatter.assert_called_once_with(profile)
    assert result == "🔵 BLUE"


def test_desktop_uses_application_spectral_color_formatter() -> None:
    for path in (
        Path("src/xfinaudio/desktop/rendering.py"),
        Path("src/xfinaudio/desktop/library_view_model.py"),
        Path("src/xfinaudio/desktop/review_view_model.py"),
    ):
        source = path.read_text()
        assert "from xfinaudio.application.spectral_profile_display import format_application_spectral_color" in source
        assert "from xfinaudio.audio.spectral_profile import format_spectral_color" not in source
