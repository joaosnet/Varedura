"""Tests for monitor.port_scanner (psutil fully mocked — no real sockets touched)."""

import socket
import types

import psutil

from monitor import port_scanner as ps


def _conn(port, pid, status, ctype, ip="0.0.0.0", has_laddr=True):
    laddr = types.SimpleNamespace(ip=ip, port=port) if has_laddr else None
    return types.SimpleNamespace(status=status, laddr=laddr, type=ctype, pid=pid)


def _patch_processes(monkeypatch, names, denied=(), missing=()):
    def fake_process(pid):
        if pid in denied:
            raise psutil.AccessDenied(pid)
        if pid in missing:
            raise psutil.NoSuchProcess(pid)
        return types.SimpleNamespace(
            name=lambda: names.get(pid, "proc"),
            memory_info=lambda: types.SimpleNamespace(rss=10 * 1024 * 1024),
            status=lambda: "running",
        )

    monkeypatch.setattr(ps.psutil, "Process", fake_process)


def test_get_listening_ports_filters_dedups_and_sorts(monkeypatch):
    conns = [
        _conn(80, 1, psutil.CONN_LISTEN, socket.SOCK_STREAM, ip="0.0.0.0"),
        _conn(80, 1, psutil.CONN_LISTEN, socket.SOCK_STREAM, ip="0.0.0.0"),  # duplicate
        _conn(22, 2, psutil.CONN_LISTEN, socket.SOCK_STREAM, ip="127.0.0.1"),
        _conn(5000, 3, psutil.CONN_ESTABLISHED, socket.SOCK_STREAM),  # not LISTEN -> excluded
        _conn(53, 4, psutil.CONN_NONE, socket.SOCK_DGRAM, ip="0.0.0.0"),
        _conn(9, 5, psutil.CONN_LISTEN, socket.SOCK_STREAM, has_laddr=False),  # no laddr
    ]
    monkeypatch.setattr(ps.psutil, "net_connections", lambda kind="inet": conns)
    _patch_processes(monkeypatch, {1: "nginx", 2: "sshd", 4: "dns"})

    tcp, udp, established = ps.get_listening_ports()

    assert [p.porta for p in tcp] == [22, 80]  # sorted, deduped, established excluded
    assert [p.porta for p in udp] == [53]
    assert established == 1

    p80 = next(p for p in tcp if p.porta == 80)
    p22 = next(p for p in tcp if p.porta == 22)
    assert p80.endereco == "Todas"  # 0.0.0.0 is relabeled
    assert p22.endereco == "127.0.0.1"
    assert p80.processo == "nginx"


def test_get_listening_ports_access_denied_label(monkeypatch):
    conns = [_conn(443, 99, psutil.CONN_LISTEN, socket.SOCK_STREAM)]
    monkeypatch.setattr(ps.psutil, "net_connections", lambda kind="inet": conns)
    _patch_processes(monkeypatch, {}, denied={99})

    tcp, _udp, _est = ps.get_listening_ports()
    assert tcp[0].processo == "Acesso Negado"


def test_get_process_connections_count_orders_and_limits(monkeypatch):
    conns = (
        [_conn(1000 + i, 1, psutil.CONN_ESTABLISHED, socket.SOCK_STREAM) for i in range(3)]
        + [_conn(2000 + i, 2, psutil.CONN_ESTABLISHED, socket.SOCK_STREAM) for i in range(5)]
        + [_conn(3000, 3, psutil.CONN_ESTABLISHED, socket.SOCK_STREAM)]
        + [_conn(4000, None, psutil.CONN_ESTABLISHED, socket.SOCK_STREAM)]  # no pid -> skipped
    )
    monkeypatch.setattr(ps.psutil, "net_connections", lambda kind="inet": conns)
    _patch_processes(monkeypatch, {1: "a", 2: "b"}, denied={3})

    top = ps.get_process_connections_count(limit=2)
    assert [p.pid for p in top] == [2, 1]  # 5 connections, then 3
    assert top[0].conexoes == 5

    full = ps.get_process_connections_count(limit=10)
    p3 = next(p for p in full if p.pid == 3)
    assert p3.nome == "Desconhecido"  # AccessDenied fallback
    assert p3.memoria_mb == 0


def test_search_port_returns_matching_processes(monkeypatch):
    conns = [
        _conn(8080, 7, psutil.CONN_LISTEN, socket.SOCK_STREAM),
        _conn(9090, 8, psutil.CONN_LISTEN, socket.SOCK_STREAM),
    ]
    monkeypatch.setattr(ps.psutil, "net_connections", lambda kind="inet": conns)
    _patch_processes(monkeypatch, {7: "server"})

    found = ps.search_port(8080)
    assert len(found) == 1
    assert found[0]["pid"] == 7
    assert found[0]["nome"] == "server"
    assert found[0]["protocolo"] == "TCP"


def test_run_full_scan_aggregates_state(monkeypatch):
    conns = [
        _conn(80, 1, psutil.CONN_LISTEN, socket.SOCK_STREAM),
        _conn(53, 2, psutil.CONN_NONE, socket.SOCK_DGRAM),
        _conn(5000, 3, psutil.CONN_ESTABLISHED, socket.SOCK_STREAM),
    ]
    monkeypatch.setattr(ps.psutil, "net_connections", lambda kind="inet": conns)
    _patch_processes(monkeypatch, {1: "a", 2: "b", 3: "c"})

    state = ps.run_full_scan()

    assert isinstance(state, ps.PortScannerState)
    assert state.total_tcp == 1
    assert state.total_udp == 1
    assert state.total_established == 1
    assert state.last_scan_time  # HH:MM:SS string is set
