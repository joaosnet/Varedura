"""Tests for monitor.netinfo default-gateway detection (subprocess mocked)."""

from monitor import netinfo

# `route print -4 0.0.0.0` output with two valid default routes (metrics 35 and
# 25) plus a malformed gateway row that must be ignored.
_ROUTE_PRINT = """\
===========================================================================
Active Routes:
Network Destination        Netmask          Gateway       Interface  Metric
          0.0.0.0          0.0.0.0      192.168.0.1    192.168.0.50     35
          0.0.0.0          0.0.0.0      192.168.18.1   192.168.18.20    25
          0.0.0.0          0.0.0.0      not_an_ip      192.168.1.1       5
===========================================================================
"""


def _patch_run(monkeypatch, mapping):
    def fake_run(cmd):
        return mapping.get(" ".join(cmd), "")

    monkeypatch.setattr(netinfo, "_run", fake_run)


def test_detect_windows_picks_lowest_valid_metric(monkeypatch):
    _patch_run(monkeypatch, {"route print -4 0.0.0.0": _ROUTE_PRINT})
    # Lowest metric (25) wins; the metric-5 row is skipped (gateway not IPv4).
    assert netinfo._detect_windows() == "192.168.18.1"


def test_detect_windows_none_when_no_valid_route(monkeypatch):
    _patch_run(monkeypatch, {"route print -4 0.0.0.0": "no default route here\n"})
    assert netinfo._detect_windows() is None


def test_detect_unix_prefers_ip_route(monkeypatch):
    _patch_run(
        monkeypatch,
        {"ip route show default": "default via 192.168.1.1 dev eth0 proto dhcp\n"},
    )
    assert netinfo._detect_unix() == "192.168.1.1"


def test_detect_unix_falls_back_to_netstat(monkeypatch):
    _patch_run(
        monkeypatch,
        {
            "ip route show default": "",  # ip not available
            "netstat -rn": "Destination Gateway Flags\ndefault 10.0.0.1 UG en0\n",
        },
    )
    assert netinfo._detect_unix() == "10.0.0.1"


def test_detect_default_gateway_dispatches_by_platform(monkeypatch):
    monkeypatch.setattr(netinfo.platform, "system", lambda: "Linux")
    _patch_run(monkeypatch, {"ip route show default": "default via 172.16.0.1 dev wg0\n"})
    assert netinfo.detect_default_gateway() == "172.16.0.1"


def test_detect_default_gateway_returns_none_on_total_failure(monkeypatch):
    monkeypatch.setattr(netinfo.platform, "system", lambda: "Linux")
    _patch_run(monkeypatch, {})  # every command yields empty output
    assert netinfo.detect_default_gateway() is None
