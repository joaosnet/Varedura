"""Passive League Live Client and per-process UDP endpoint tests."""

import socket
import threading
import time
from types import SimpleNamespace

import psutil
import pytest

from monitor.league_detector import (
    LeagueDetectorState,
    LeagueMatchDetector,
    _RejectLiveClientRedirects,
    _validate_live_client_url,
    mask_endpoint_ip,
)


class _Process:
    def __init__(
        self,
        *,
        pid=100,
        name="League of Legends.exe",
        create_time=10.0,
        connections=(),
        error=None,
        cmdline=(),
    ):
        self.pid = pid
        self.info = {
            "pid": pid,
            "name": name,
            "exe": f"C:/Riot/{name}",
            "create_time": create_time,
            "cmdline": list(cmdline),
        }
        self._connections = list(connections)
        self._error = error

    def net_connections(self, kind="inet"):
        assert kind == "inet"
        if self._error:
            raise self._error
        return self._connections


def _udp(host="104.160.131.3", port=7001):
    return SimpleNamespace(
        type=socket.SOCK_DGRAM,
        raddr=SimpleNamespace(ip=host, port=port),
    )


def _tcp(host="104.160.131.3", port=7001):
    return SimpleNamespace(
        type=socket.SOCK_STREAM,
        raddr=SimpleNamespace(ip=host, port=port),
    )


def _detector(processes, **kwargs):
    process_iter = kwargs.pop("process_iter", lambda: processes)
    return LeagueMatchDetector(
        live_client_probe=lambda: {"gameTime": 12.0},
        process_iter=process_iter,
        system=kwargs.pop("system", "Windows"),
        session_id_factory=lambda: "session123",
        **kwargs,
    )


def test_endpoint_requires_two_stable_readings_and_becomes_ephemeral_target():
    detector = _detector([_Process(connections=[_udp()])])
    first = detector.poll()
    second = detector.poll()
    assert first.state is LeagueDetectorState.ACTIVE_PENDING
    assert first.endpoint is None
    assert second.state is LeagueDetectorState.ACTIVE
    assert second.endpoint is not None
    assert second.endpoint.generation == 1
    target = second.endpoint.to_ping_target()
    assert target.ephemeral
    assert target.id == "league_match_session123"
    assert target.host == "104.160.131.3"


def test_only_real_game_public_udp_and_documented_ports_are_considered():
    processes = [
        _Process(name="LeagueClientUx.exe", connections=[_udp()]),
        _Process(connections=[_tcp()]),
        _Process(connections=[_udp("192.168.1.8", 7001)]),
        _Process(connections=[_udp("104.160.131.3", 443)]),
    ]
    result = _detector(processes).poll()
    assert result.state is LeagueDetectorState.ACTIVE_PENDING
    assert result.candidate_count == 0


def test_ambiguous_public_endpoints_are_never_guessed():
    process = _Process(connections=[_udp("104.160.131.3", 7001), _udp("8.8.8.8", 7002)])
    result = _detector([process]).poll()
    assert result.state is LeagueDetectorState.AMBIGUOUS
    assert result.endpoint is None
    assert result.candidate_count == 2


def test_permission_denied_is_visible_without_elevation():
    process = _Process(error=psutil.AccessDenied(pid=100))
    result = _detector([process]).poll()
    assert result.state is LeagueDetectorState.PERMISSION_DENIED
    assert result.endpoint is None


def test_three_live_api_failures_end_and_remove_session():
    calls = {"ok": True}

    def live_probe():
        if calls["ok"]:
            return {"gameTime": 42.0}
        raise OSError("closed")

    detector = LeagueMatchDetector(
        live_client_probe=live_probe,
        process_iter=lambda: [_Process(connections=[_udp()])],
        system="Windows",
        session_id_factory=lambda: "session123",
    )
    detector.poll()
    assert detector.poll().state is LeagueDetectorState.ACTIVE
    calls["ok"] = False
    assert detector.poll().state is LeagueDetectorState.ACTIVE
    assert detector.poll().state is LeagueDetectorState.ACTIVE
    ended = detector.poll()
    assert ended.state is LeagueDetectorState.ENDED
    assert ended.endpoint is None
    assert detector.current_endpoint is None


def test_pid_reuse_or_endpoint_change_creates_new_generation():
    holder = {"process": _Process(create_time=10.0, connections=[_udp()])}
    detector = _detector([], process_iter=lambda: [holder["process"]])
    detector.poll()
    original = detector.poll().endpoint
    assert original is not None and original.generation == 1

    holder["process"] = _Process(create_time=11.0, connections=[_udp()])
    pending = detector.poll()
    changed = detector.poll()
    assert pending.state is LeagueDetectorState.ACTIVE_PENDING
    assert pending.endpoint == original
    assert changed.endpoint is not None
    assert changed.endpoint.generation == 2


def test_active_endpoint_is_removed_when_socket_disappears_or_is_ambiguous():
    process = _Process(connections=[_udp()])
    detector = _detector([], process_iter=lambda: [process])
    detector.poll()
    assert detector.poll().endpoint is not None

    process._connections = []
    missing = detector.poll()
    assert missing.state is LeagueDetectorState.ACTIVE_PENDING
    assert missing.endpoint is None
    assert detector.current_endpoint is None

    process._connections = [_udp("104.160.131.3", 7001)]
    detector.poll()
    assert detector.poll().endpoint is not None
    process._connections = [_udp("104.160.131.3", 7001), _udp("8.8.8.8", 7002)]
    ambiguous = detector.poll()
    assert ambiguous.state is LeagueDetectorState.AMBIGUOUS
    assert ambiguous.endpoint is None
    assert detector.current_endpoint is None


def test_incomplete_socket_scan_never_accepts_partial_single_candidate():
    class SlowProcess(_Process):
        def net_connections(self, kind="inet"):
            time.sleep(0.15)
            return [_udp("8.8.8.8", 7002)]

    detector = _detector(
        [
            _Process(connections=[_udp("104.160.131.3", 7001)]),
            SlowProcess(pid=101),
        ],
        scan_timeout=0.05,
    )
    first = detector.poll()
    second = detector.poll()
    assert first.state is LeagueDetectorState.ACTIVE_PENDING
    assert second.state is LeagueDetectorState.ACTIVE_PENDING
    assert first.endpoint is None and second.endpoint is None
    assert detector.current_endpoint is None


def test_process_iteration_failure_never_accepts_candidates_collected_before_it():
    def incomplete_process_iter():
        yield _Process(connections=[_udp("104.160.131.3", 7001)])
        raise psutil.Error("process enumeration failed")

    detector = _detector([], process_iter=incomplete_process_iter)

    first = detector.poll()
    second = detector.poll()

    assert first.state is LeagueDetectorState.ACTIVE_PENDING
    assert second.state is LeagueDetectorState.ACTIVE_PENDING
    assert first.endpoint is None and second.endpoint is None
    assert detector.current_endpoint is None


def test_absolute_poll_cadence_ends_session_promptly_after_three_failures():
    working = {"value": True}

    def live_probe():
        if working["value"]:
            return {"gameTime": 12.0}
        raise OSError("ended")

    detector = LeagueMatchDetector(
        live_client_probe=live_probe,
        process_iter=lambda: [_Process(connections=[_udp()])],
        system="Windows",
        session_id_factory=lambda: "session123",
    )
    detector.poll()
    assert detector.poll().state is LeagueDetectorState.ACTIVE
    working["value"] = False
    ended = threading.Event()
    started = time.monotonic()
    detector.start(
        lambda result: ended.set()
        if result.state is LeagueDetectorState.ENDED
        else None,
        interval=0.25,
    )
    assert ended.wait(1.5)
    detector.stop()
    assert time.monotonic() - started < 1.25


def test_linux_detection_is_explicitly_experimental():
    detector = _detector([_Process(connections=[_udp()])], system="Linux")
    detector.poll()
    result = detector.poll()
    assert result.endpoint is not None
    assert result.endpoint.experimental


def test_linux_wine_process_is_identified_from_command_line():
    process = _Process(
        name="wine64-preloader",
        cmdline=("wine64-preloader", "C:/Riot/League of Legends.exe"),
        connections=[_udp()],
    )
    detector = _detector([process], system="Linux")
    detector.poll()
    result = detector.poll()
    assert result.state is LeagueDetectorState.ACTIVE
    assert result.endpoint is not None and result.endpoint.experimental


def test_privacy_mask_defaults_to_network_prefixes():
    assert mask_endpoint_ip("104.160.131.3") == "104.160.131.0/24"
    assert mask_endpoint_ip("2606:4700:4700::1111") == "2606:4700:4700::/64"


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost:2999/liveclientdata/gamestats",
        "https://127.0.0.1:3000/liveclientdata/gamestats",
        "https://riot.example/liveclientdata/gamestats",
        "http://127.0.0.1:2999/liveclientdata/gamestats",
        "https://127.0.0.1:2999/other",
    ],
)
def test_self_signed_tls_exception_cannot_escape_exact_loopback_url(url):
    with pytest.raises(ValueError, match="loopback"):
        _validate_live_client_url(url)


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_self_signed_tls_exception_rejects_redirects(status):
    handler = _RejectLiveClientRedirects()
    with pytest.raises(OSError, match="redirects are not allowed"):
        handler.redirect_request(
            None,
            None,
            status,
            "Found",
            {"Location": "https://example.com/"},
            "https://example.com/",
        )


def test_live_api_mapping_must_contain_numeric_game_time():
    detector = LeagueMatchDetector(
        live_client_probe=lambda: {},
        process_iter=lambda: [],
        system="Windows",
    )
    result = detector.poll()
    assert result.state is LeagueDetectorState.API_UNAVAILABLE
    assert "active match" in result.detail
