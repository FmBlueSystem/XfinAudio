"""Internationalization helpers for the XfinAudio desktop app.

Uses Qt's QTranslator system with compiled .qm files under
assets/translations/.  Source .ts files live in translations/.

To update translations after marking new strings:
    uv run python scripts/update_translations.py
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLocale, QTranslator


def translations_dir() -> Path:
    """Return the directory holding compiled .qm translation files."""
    # Development: repo root / assets / translations
    here = Path(__file__).resolve().parent
    dev = here.parents[1] / "assets" / "translations"
    if dev.exists():
        return dev
    # Fallback for installed package
    return here.parent / "assets" / "translations"


_ACTIVE_TRANSLATOR: QTranslator | None = None


def remove_translator() -> None:
    """Remove the currently installed XfinAudio translator."""
    global _ACTIVE_TRANSLATOR
    app = QCoreApplication.instance()
    if app is not None and _ACTIVE_TRANSLATOR is not None:
        app.removeTranslator(_ACTIVE_TRANSLATOR)
        _ACTIVE_TRANSLATOR = None


def install_translator(lang: str | None = None) -> QTranslator | None:
    """Install a QTranslator for the requested or system language.

    *lang* is an ISO-639-1 code such as ``"es"`` or ``"en"``.
    If None or empty, the system locale is used.

    Returns the installed translator, or None if no .qm file was found.
    """
    global _ACTIVE_TRANSLATOR
    app = QCoreApplication.instance()
    if app is None:
        return None

    remove_translator()

    if not lang:
        lang = QLocale.system().name()
    short = lang.split("_")[0]

    tdir = translations_dir()
    filenames = [f"xfinaudio_{lang}.qm"]
    if short != lang:
        filenames.append(f"xfinaudio_{short}.qm")

    for filename in filenames:
        qm_path = tdir / filename
        if qm_path.exists():
            translator = QTranslator()
            if translator.load(str(qm_path)):
                app.installTranslator(translator)
                _ACTIVE_TRANSLATOR = translator
                return translator
    return None


def current_language() -> str:
    """Return the active UI language code (e.g. 'en' or 'es')."""
    app = QCoreApplication.instance()
    if app is None:
        return "en"
    loc = QLocale()
    lang = loc.name().split("_")[0]
    return lang if lang in ("en", "es") else "en"
