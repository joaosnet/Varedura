"""Internationalization (i18n) module for Varedura.

Provides a simple JSON-based translation system with:
- Auto-detection of system language
- User preference persistence
- Fallback to Portuguese (original language)
"""

from __future__ import annotations

import json
import locale
import os
from pathlib import Path
from typing import Optional

_LOCALES_DIR = Path(__file__).parent
_SUPPORTED_LANGUAGES = ("pt", "en")
_DEFAULT_LANGUAGE = "pt"
_PREFS_FILE = Path.home() / ".varedura_lang.json"

_translations: dict[str, str] = {}
_current_language: str = _DEFAULT_LANGUAGE


def _detect_system_language() -> str:
    """Detect the system language and return a supported language code."""
    try:
        try:
            system_locale = locale.getlocale()[0] or ""
        except Exception:
            system_locale = locale.getdefaultlocale()[0] or ""
        lang_code = system_locale.split("_")[0].lower()
        if lang_code in _SUPPORTED_LANGUAGES:
            return lang_code
    except Exception:
        pass
    return _DEFAULT_LANGUAGE


def _load_preference() -> Optional[str]:
    """Load user language preference from disk."""
    try:
        if _PREFS_FILE.exists():
            data = json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
            lang = data.get("language", "").lower()
            if lang in _SUPPORTED_LANGUAGES:
                return lang
    except Exception:
        pass
    return None


def save_preference(language: str) -> None:
    """Save user language preference to disk."""
    try:
        _PREFS_FILE.write_text(
            json.dumps({"language": language}, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _load_translations(language: str) -> dict[str, str]:
    """Load translation file for a given language."""
    path = _LOCALES_DIR / f"{language}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        # Fallback to default language
        fallback = _LOCALES_DIR / f"{_DEFAULT_LANGUAGE}.json"
        return json.loads(fallback.read_text(encoding="utf-8"))


def init(language: Optional[str] = None) -> str:
    """Initialize the i18n system.

    Args:
        language: Force a specific language. If None, checks user preference
                  then falls back to system language detection.

    Returns:
        The language code that was loaded.
    """
    global _translations, _current_language

    if language and language in _SUPPORTED_LANGUAGES:
        _current_language = language
    else:
        pref = _load_preference()
        _current_language = pref if pref else _detect_system_language()

    _translations = _load_translations(_current_language)
    return _current_language


def set_language(language: str) -> str:
    """Switch language at runtime and save preference.

    Returns:
        The language code that was set.
    """
    global _translations, _current_language

    if language not in _SUPPORTED_LANGUAGES:
        language = _DEFAULT_LANGUAGE

    _current_language = language
    _translations = _load_translations(language)
    save_preference(language)
    return _current_language


def get_language() -> str:
    """Return the current language code."""
    return _current_language


def get_supported_languages() -> tuple[str, ...]:
    """Return tuple of supported language codes."""
    return _SUPPORTED_LANGUAGES


def t(key: str, **kwargs) -> str:
    """Translate a key, with optional format arguments.

    Args:
        key: Dot-separated translation key (e.g. "menu.title")
        **kwargs: Format arguments for string interpolation

    Returns:
        Translated string, or the key itself if not found.
    """
    if not _translations:
        init()

    value = _translations.get(key, key)
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value
    return value
