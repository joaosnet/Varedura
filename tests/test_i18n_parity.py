"""Parity and integrity tests for i18n locale files."""

from __future__ import annotations

import json
from pathlib import Path
from string import Formatter

I18N_DIR = Path(__file__).resolve().parents[1] / "i18n"


def _load_locale(lang: str) -> dict[str, str]:
    path = I18N_DIR / f"{lang}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _field_names(template: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(template)
        if field_name is not None
    }


def test_i18n_pt_en_key_parity() -> None:
    pt = _load_locale("pt")
    en = _load_locale("en")
    assert set(pt.keys()) == set(en.keys())


def test_i18n_all_values_non_empty_strings() -> None:
    for lang in ("pt", "en"):
        data = _load_locale(lang)
        assert data, f"{lang}.json must not be empty"
        for key, value in data.items():
            assert isinstance(value, str), f"{lang}:{key} must be str"
            assert value.strip(), f"{lang}:{key} must not be empty"


def test_i18n_placeholder_parity() -> None:
    pt = _load_locale("pt")
    en = _load_locale("en")
    for key in pt:
        assert _field_names(pt[key]) == _field_names(en[key]), (
            f"Placeholder mismatch for {key}: pt={pt[key]!r} en={en[key]!r}"
        )
