"""Tests for the lay-friendly port catalog and i18n key coverage."""

import json
from pathlib import Path

import pytest

from monitor.port_catalog import (
    EPHEMERAL_START,
    PORT_CATALOG,
    classify_exposure,
    describe_port,
    is_exposed,
)

I18N_DIR = Path(__file__).resolve().parents[1] / "i18n"


def _load(lang: str) -> dict:
    return json.loads((I18N_DIR / f"{lang}.json").read_text(encoding="utf-8"))


def test_describe_port_known():
    assert describe_port(443) == ("port.https", "port.https.expl")
    assert describe_port(53, "UDP") == ("port.dns", "port.dns.expl")


def test_describe_port_ephemeral():
    label, expl = describe_port(EPHEMERAL_START + 10)
    assert label == "port.ephemeral"
    assert expl == "port.ephemeral.expl"


def test_describe_port_unknown_low():
    label, expl = describe_port(12345)
    assert label == "port.unknown"
    assert expl == "port.unknown.expl"


@pytest.mark.parametrize(
    "endereco,expected",
    [
        ("0.0.0.0", "ports.exposure_all"),
        ("Todas", "ports.exposure_all"),
        ("::", "ports.exposure_all"),
        ("127.0.0.1", "ports.exposure_local"),
        ("::1", "ports.exposure_local"),
        ("localhost", "ports.exposure_local"),
        ("192.168.1.5", "ports.exposure_lan"),
        ("fe80::1", "ports.exposure_lan"),
    ],
)
def test_classify_exposure(endereco, expected):
    chip, color = classify_exposure(endereco)
    assert chip == expected
    assert color  # a non-empty color string


def test_is_exposed():
    assert is_exposed("0.0.0.0") is True
    assert is_exposed("Todas") is True
    assert is_exposed("::") is True
    assert is_exposed("127.0.0.1") is False
    assert is_exposed("192.168.0.2") is False


def test_i18n_key_parity():
    """pt.json and en.json must define exactly the same keys."""
    pt, en = _load("pt"), _load("en")
    assert set(pt) == set(en)


def test_catalog_keys_translated():
    """Every label/expl key the catalog can emit must exist in both languages."""
    pt, en = _load("pt"), _load("en")
    keys = set()
    for label_key, expl_key in PORT_CATALOG.values():
        keys.add(label_key)
        keys.add(expl_key)
    # Fallback keys emitted by describe_port for ephemeral/unknown ports.
    keys.update(
        {
            "port.ephemeral",
            "port.ephemeral.expl",
            "port.unknown",
            "port.unknown.expl",
        }
    )
    # Exposure chips from classify_exposure.
    keys.update({"ports.exposure_all", "ports.exposure_local", "ports.exposure_lan"})
    missing_pt = sorted(k for k in keys if k not in pt)
    missing_en = sorted(k for k in keys if k not in en)
    assert not missing_pt, f"missing in pt.json: {missing_pt}"
    assert not missing_en, f"missing in en.json: {missing_en}"
