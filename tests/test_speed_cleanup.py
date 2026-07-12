"""Tests for Selenium driver cleanup (no orphaned chrome/chromedriver)."""

import subprocess
import threading
import time

import pytest

from monitor.speed_providers import (
    BrasilBandaLargaProvider,
    SimetProvider,
    SpeedtestNetProvider,
    _safe_quit,
)
from monitor.speed_tester import ContinuousSpeedTester, SpeedTestConfig


class FakeDriver:
    def __init__(self, raise_on_quit=False):
        self.quit_called = False
        self._raise = raise_on_quit
        self.service = type("S", (), {"process": None})()

    def quit(self):
        self.quit_called = True
        if self._raise:
            raise RuntimeError("boom")


def test_safe_quit_calls_quit():
    d = FakeDriver()
    _safe_quit(d)
    assert d.quit_called


def test_safe_quit_handles_none():
    _safe_quit(None)  # deve ser no-op, sem erro


def test_safe_quit_fallback_kills_process():
    killed = {"v": False}

    class Proc:
        def kill(self):
            killed["v"] = True

    d = FakeDriver(raise_on_quit=True)
    d.service.process = Proc()
    _safe_quit(d)
    assert d.quit_called and killed["v"]


def test_provider_cleanup_quits_and_clears_driver():
    p = BrasilBandaLargaProvider()
    d = FakeDriver()
    p._driver = d
    p.cleanup()
    assert d.quit_called
    assert p._driver is None


def test_provider_cleanup_without_driver_is_safe():
    p = SimetProvider()
    p.cleanup()  # nenhum driver aberto -> sem erro
    assert p._driver is None


def test_chrome_service_suppresses_console_window():
    """O Service do chromedriver deve usar CREATE_NO_WINDOW (sem console)."""
    pytest.importorskip("selenium")
    from monitor.speed_providers import _chrome_service

    service = _chrome_service()
    assert service.creation_flags == getattr(subprocess, "CREATE_NO_WINDOW", 0)


def test_continuous_stop_cleans_active_drivers(monkeypatch):
    tester = ContinuousSpeedTester(SpeedTestConfig())
    called = {"v": False}

    class FakeManager:
        def cleanup_active(self):
            called["v"] = True

    # Providers are intentionally lazy now; inject one without materializing
    # requests/Selenium during this cleanup-only test.
    monkeypatch.setattr(tester, "_multi_provider", FakeManager())
    tester.stop()  # _thread é None (nunca iniciado) -> só limpa drivers
    assert called["v"]


def test_speedtest_provider_uses_isolated_json_subprocess(monkeypatch):
    import monitor.speed_providers as providers

    captured = {}

    class FakeProcess:
        returncode = 0

        def communicate(self, timeout):
            captured["timeout"] = timeout
            return (
                '{"download":120000000,"upload":40000000,"ping":18.5,'
                '"server":{"sponsor":"Example ISP"}}',
                "",
            )

        def poll(self):
            return self.returncode

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    monkeypatch.setattr(providers.subprocess, "Popen", fake_popen)
    provider = SpeedtestNetProvider()
    provider._available = True
    result = provider.run_test()

    assert captured["command"][1:] == ["-m", "speedtest", "--json", "--secure"]
    assert captured["timeout"] == 120
    assert result.download_mbps == 120.0
    assert result.upload_mbps == 40.0
    assert result.servidor == "Example ISP"


def test_every_bandwidth_provider_runs_in_an_isolated_worker(monkeypatch):
    import monitor.speed_tester as speed_module

    captured = {}

    class FakeProcess:
        pid = 4321
        returncode = 0

        def communicate(self, timeout):
            captured["timeout"] = timeout
            return (
                '{"ok":true,"result":{"download_mbps":90.0,'
                '"upload_mbps":30.0,"ping_ms":12.0,"servidor":"CDN",'
                '"timestamp":"2026-01-01T00:00:00",'
                '"provider_name":"Fast.com"}}\n',
                "",
            )

        def poll(self):
            return self.returncode

    def fake_popen(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return FakeProcess()

    tester = ContinuousSpeedTester(SpeedTestConfig())
    monkeypatch.setattr(tester, "_next_provider", lambda: ("fast", "Fast.com"))
    monkeypatch.setattr(speed_module.subprocess, "Popen", fake_popen)

    result = tester.run_once()

    assert result is not None and result.provider_name == "Fast.com"
    assert captured["command"][1:4] == ["-m", "monitor.speed_worker", "--provider"]
    assert captured["command"][-1] == "fast"
    assert captured["kwargs"]["shell"] is False


def test_bandwidth_worker_cancellation_is_observed_promptly(monkeypatch):
    import monitor.speed_tester as speed_module

    stopped = threading.Event()

    class SlowProcess:
        pid = 9876
        returncode = None

        def communicate(self, timeout):
            if stopped.is_set():
                self.returncode = -1
                return "", ""
            raise subprocess.TimeoutExpired("worker", timeout)

        def poll(self):
            return self.returncode

    tester = ContinuousSpeedTester(SpeedTestConfig(total_timeout_seconds=30))
    monkeypatch.setattr(tester, "_next_provider", lambda: ("simet", "SIMET"))
    monkeypatch.setattr(speed_module.subprocess, "Popen", lambda *a, **k: SlowProcess())
    monkeypatch.setattr(
        tester,
        "_terminate_process_tree",
        lambda process: stopped.set(),
    )
    worker = threading.Thread(target=tester.run_once)
    worker.start()
    deadline = time.monotonic() + 1
    while not tester.get_stats_snapshot()["is_testing"] and time.monotonic() < deadline:
        time.sleep(0.005)

    started = time.monotonic()
    assert tester.cancel_current_test()
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert time.monotonic() - started < 0.25
    assert tester.get_stats_snapshot()["last_error"] == "Teste cancelado"


def test_prepared_bandwidth_test_honors_cancel_before_worker_starts(monkeypatch):
    tester = ContinuousSpeedTester(SpeedTestConfig())
    provider_called = False

    def fail_if_provider_runs():
        nonlocal provider_called
        provider_called = True
        raise AssertionError("a pre-cancelled test must not start a provider")

    monkeypatch.setattr(tester, "_run_single_test", fail_if_provider_runs)

    assert tester.prepare_single_test()
    assert tester.cancel_current_test()
    assert tester.run_once(prepared=True) is None

    assert not provider_called
    assert tester.get_stats_snapshot()["last_error"] == "Teste cancelado"
    assert not tester.cancel_current_test()


def test_continuous_loop_uses_the_same_reservation_path(monkeypatch):
    tester = ContinuousSpeedTester(SpeedTestConfig())
    called = threading.Event()

    def one_iteration():
        called.set()
        tester._running = False
        return None

    monkeypatch.setattr(tester, "_run_single_test", one_iteration)
    tester.start()
    tester._thread.join(timeout=1)

    assert called.is_set()
    assert not tester._thread.is_alive()
    assert not tester.cancel_current_test()


def test_rich_speed_key_can_cancel_before_its_thread_starts(monkeypatch):
    import monitor.stalker as stalker

    tester = ContinuousSpeedTester(SpeedTestConfig())
    queued = {}
    provider_called = False

    def fail_if_provider_runs():
        nonlocal provider_called
        provider_called = True
        return None

    class DeferredThread:
        def __init__(self, *, target, kwargs, daemon):
            queued.update(target=target, kwargs=kwargs, daemon=daemon)

        def start(self):
            pass

    monkeypatch.setattr(tester, "_run_single_test", fail_if_provider_runs)
    monkeypatch.setattr(stalker, "get_speed_tester", lambda: tester)
    monkeypatch.setattr(stalker.threading, "Thread", DeferredThread)

    assert stalker.handle_key("v")
    assert queued["daemon"] is True
    assert stalker.handle_key("v")
    queued["target"](**queued["kwargs"])

    assert not provider_called
    assert tester.get_stats_snapshot()["last_error"] == "Teste cancelado"
