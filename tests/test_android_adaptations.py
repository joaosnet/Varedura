"""Adaptações Android/Termux do painel e do diagnóstico de rede."""

from __future__ import annotations

import io
from types import SimpleNamespace

from rich.console import Console

from cli import ui_shared
from i18n import t
from monitor import network_diagnostics as diagnostics
from varedura import termux_env


def _render(renderable) -> str:
    console = Console(width=120, file=io.StringIO(), record=True)
    console.print(renderable)
    return console.export_text()


def test_dashboard_hides_docker_and_mcp_rows_without_docker_tab(monkeypatch):
    monkeypatch.setattr(termux_env, "should_show_docker_tab", lambda: False)
    text = _render(ui_shared.build_dashboard_status("pt"))
    assert t("mcp.option") not in text
    assert t("settings.option_cleanup") not in text

    monkeypatch.setattr(termux_env, "should_show_docker_tab", lambda: True)
    assert t("mcp.option") in _render(ui_shared.build_dashboard_status("pt"))


def test_dashboard_traffic_uses_android_wifi_counters():
    telemetry = SimpleNamespace(rx_bytes=3 * 1024**3, tx_bytes=512 * 1024**2)
    stats = {"bytes_enviados_mb": 9999.0, "bytes_recebidos_mb": 99999.0}
    text = _render(
        ui_shared.build_dashboard_status(
            "pt", dash_stats=stats, android_telemetry=telemetry
        )
    )
    assert "↑ 512 MB" in text and "↓ 3.0 GB" in text


def test_interfaces_fall_back_to_sysfs_when_stats_are_denied(monkeypatch):
    address = SimpleNamespace(
        family=diagnostics.socket.AF_INET, address="192.168.18.242"
    )
    monkeypatch.setattr(
        diagnostics.psutil, "net_if_addrs", lambda: {"wlan0": [address]}
    )

    def denied():
        raise PermissionError(13, "Permission denied (SIOCETHTOOL)")

    monkeypatch.setattr(diagnostics.psutil, "net_if_stats", denied)
    monkeypatch.setattr(diagnostics, "_sysfs_interface_is_up", lambda name: True)
    (wlan,) = diagnostics._interface_addresses()
    assert wlan.name == "wlan0" and wlan.is_up
