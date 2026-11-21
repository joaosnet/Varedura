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

    # Nenhum teste sonda a rede real da máquina (netsh/ip/termux-*). Quem testa
    # a detecção usa ``REAL_DETECT_ACTIVE_NETWORK`` com ``_run`` mockado.
    from monitor import netinfo
    from monitor.plan_profiles import ActiveNetwork

    monkeypatch.setattr(netinfo, "detect_active_network", lambda: ActiveNetwork())
    yield
