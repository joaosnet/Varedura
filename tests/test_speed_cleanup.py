"""Tests for Selenium driver cleanup (no orphaned chrome/chromedriver)."""

import subprocess

import pytest

from monitor.speed_providers import (
    BrasilBandaLargaProvider,
    SimetProvider,
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
    monkeypatch.setattr(
        tester._multi_provider, "cleanup_active", lambda: called.__setitem__("v", True)
    )
    tester.stop()  # _thread é None (nunca iniciado) -> só limpa drivers
    assert called["v"]
