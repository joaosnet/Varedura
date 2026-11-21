"""Isolamento global: nenhum teste grava o consumo/histórico reais do usuário."""

from __future__ import annotations

import pytest

from monitor.netinfo import detect_active_network as REAL_DETECT_ACTIVE_NETWORK  # noqa: F401


@pytest.fixture(autouse=True)
def _isolated_plan_storage(monkeypatch, tmp_path_factory):
    from monitor import data_usage

    base = tmp_path_factory.mktemp("plan-storage")
    monkeypatch.setattr(data_usage, "USAGE_FILE", base / "usage.json")
    monkeypatch.setattr(data_usage, "SPEED_HISTORY_FILE", base / "speed.jsonl")
    monkeypatch.setattr(data_usage, "_tracker", None)

    from monitor import auto_speed

    monkeypatch.setattr(auto_speed, "STATE_FILE", base / "auto_speed.json")

    # Nenhum teste sonda a rede real da máquina (netsh/ip/termux-*). Quem testa
    # a detecção usa ``REAL_DETECT_ACTIVE_NETWORK`` com ``_run`` mockado.
    from monitor import netinfo
    from monitor.plan_profiles import ActiveNetwork

    monkeypatch.setattr(netinfo, "detect_active_network", lambda: ActiveNetwork())

    # Nunca altera o ~/.termux/termux.properties real nem abre diálogos nativos.
    from varedura import termux_env

    monkeypatch.setattr(
        termux_env, "termux_properties_path", lambda: base / "termux.properties"
    )
    monkeypatch.setattr(termux_env, "has_native_dialog", lambda: False)
    yield
