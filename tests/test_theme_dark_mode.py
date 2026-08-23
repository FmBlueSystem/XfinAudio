"""Dark mode refinement guarantees for the desktop theme.

Covers Phase 9 requirements:
- R1: text colors meet WCAG AA (>= 4.5:1) against their background
- R2: buttons use a subtle gradient for depth
- R3: all interactive elements expose a hover state
- R4: focusable elements expose a focus outline
"""

import re

from xfinaudio.desktop.theme import _DJ_VISUAL_STYLESHEET

_BACKGROUND = "#080c12"

# Spectrum palette key colors. Pinned so a future refresh is a deliberate edit
# here, not an accident somewhere in the stylesheet.
_PALETTE = {
    "window background": "#080c12",
    "panel surface": "#0f1721",
    "elevated surface": "#151f2b",
    "table background": "#0e161e",
    "table alternate row": "#121d27",
    "primary text": "#eaf4ff",
    "secondary text": "#cfe0f0",
    "muted text": "#93aac4",
    "signal cyan accent": "#2ce8f5",
    "primary sweep start": "#3ef0d2",
    "primary sweep end": "#00c2e6",
    "selection highlight": "#463ac4",
    "active selection highlight": "#5a4be0",
    "header text": "#63d3d8",
    "warm status amber": "#ffb000",
}


def _relative_luminance(hex_color: str) -> float:
    raw = hex_color.lstrip("#")
    channels = [int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)]

    def linearize(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    r, g, b = (linearize(channel) for channel in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(foreground: str, background: str) -> float:
    high = _relative_luminance(foreground)
    low = _relative_luminance(background)
    if low > high:
        high, low = low, high
    return (high + 0.05) / (low + 0.05)


def _blocks() -> dict[str, str]:
    blocks: dict[str, str] = {}
    for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", _DJ_VISUAL_STYLESHEET):
        selector = match.group(1).strip()
        blocks[selector] = match.group(2)
    return blocks


def test_r1_text_colors_meet_wcag_aa() -> None:
    color_pattern = re.compile(r"(?<!-)\bcolor:\s*(#[0-9a-fA-F]{6})")
    background_pattern = re.compile(r"\bbackground(?:-color)?:[^;}]*?(#[0-9a-fA-F]{6})")
    for selector, body in _blocks().items():
        # Disabled controls are WCAG-exempt for contrast.
        if "disabled" in selector:
            continue
        bg_match = background_pattern.search(body)
        background = bg_match.group(1) if bg_match else _BACKGROUND
        for hex_color in color_pattern.findall(body):
            ratio = _contrast_ratio(hex_color, background)
            assert ratio >= 4.5, f"{selector}: {hex_color} on {background} only {ratio:.2f}:1"


def test_r2_buttons_have_gradient() -> None:
    blocks = _blocks()
    for selector in (
        "QPushButton",
        "QPushButton#primaryAction",
        "QPushButton#secondaryAction",
        "QPushButton#seratoExportButton",
    ):
        assert "qlineargradient" in blocks[selector], f"{selector} lacks button depth gradient"


def test_r3_interactive_elements_have_hover_states() -> None:
    selectors = set(_blocks())
    for control in ("QPushButton", "QComboBox", "QLineEdit"):
        assert any(sel.startswith(control) and ":hover" in sel for sel in selectors), f"missing :hover for {control}"
    for selector in (
        "QPushButton#primaryAction:hover",
        "QPushButton#secondaryAction:hover",
        "QPushButton#seratoExportButton:hover",
    ):
        assert selector in selectors, f"missing :hover for {selector}"
    assert any("QListWidget#workflowSidebar::item:hover" in sel for sel in selectors)


def test_r4_focusable_elements_have_focus_outline() -> None:
    blocks = _blocks()
    for control in ("QPushButton", "QComboBox", "QLineEdit"):
        focus_selectors = [sel for sel in blocks if sel.startswith(control) and ":focus" in sel]
        assert focus_selectors, f"missing :focus for {control}"
        assert any("outline" in blocks[sel] for sel in focus_selectors), f"{control}:focus has no outline"
        assert all("outline: none" not in blocks[sel] for sel in focus_selectors), f"{control}:focus disables outline"
        assert any(_PALETTE["signal cyan accent"] in blocks[sel] for sel in focus_selectors), (
            f"{control}:focus lacks visible outline color"
        )


def test_r5_spectrum_palette_key_colors_are_present() -> None:
    for role, hex_color in _PALETTE.items():
        assert hex_color in _DJ_VISUAL_STYLESHEET, f"palette lost its {role} ({hex_color})"


def test_r5_selection_highlights_meet_wcag_aa() -> None:
    for selection in ("selection highlight", "active selection highlight"):
        ratio = _contrast_ratio("#ffffff", _PALETTE[selection])
        assert ratio >= 4.5, f"{selection}: white text only {ratio:.2f}:1"
