"""Teste de velocidade automático e provedores HTTP (Cloudflare / M-Lab)."""

from __future__ import annotations

import datetime
import threading
import time
import types

import pytest

from monitor import auto_speed, data_usage
from monitor.plan_profiles import ActiveNetwork, NetworkKind, PlanProfile

HOME = PlanProfile(id="home", name="Fibra", down_mbps=600, up_mbps=300)
WIFI = ActiveNetwork(NetworkKind.WIFI, "Casa", "192.168.0.1", "wlan0")
MOBILE = ActiveNetwork(NetworkKind.MOBILE, interface="rmnet0")


class _FakeTester:
    def __init__(self, result=None, can_prepare=True):
        self.result = result
        self.can_prepare = can_prepare
        self._provider_index = 0
        self.indexes: list[int] = []

    def prepare_single_test(self):
        return self.can_prepare

    def run_once(self, prepared=False):
        self.indexes.append(self._provider_index)
        return self.result

    def get_stats_snapshot(self):
        return {"last_error": "provider-failed"}


def _result(down=480.0, up=240.0):
    return types.SimpleNamespace(
        download_mbps=down,
        upload_mbps=up,
        ping_ms=12.0,
        provider_name="Cloudflare",
        servidor="Cloudflare FOR",
        timestamp=datetime.datetime.now(),
    )


def _use_tester(monkeypatch, tester):
    import monitor.speed_tester as speed_tester

    monkeypatch.setattr(speed_tester, "get_speed_tester", lambda: tester)


def test_normalize_minutes_bounds():
    assert [auto_speed.normalize_minutes(v) for v in (0, -5, "x", 1, 15, 60, 99999)] == [
        0,
        0,
        0,
        15,
        15,
        60,
        1440,
    ]


def test_never_runs_on_mobile_data_even_when_forced(monkeypatch):
    tester = _FakeTester(_result())
    _use_tester(monkeypatch, tester)
    outcome = auto_speed.run_scheduled(
        force=True, network=MOBILE, profile=HOME, minutes=60
    )
    assert outcome == {"status": "mobile"}
    assert tester.indexes == []
    unknown = auto_speed.run_scheduled(
        force=True, network=ActiveNetwork(), profile=HOME, minutes=60
    )
    assert unknown == {"status": "no_network"}


def test_runs_when_due_records_sample_and_respects_interval(monkeypatch):
    tester = _FakeTester(_result())
    _use_tester(monkeypatch, tester)
    now = 1_800_000_000.0

    assert auto_speed.run_scheduled(network=WIFI, profile=HOME, minutes=0, now=now) == {
        "status": "disabled"
    }
    first = auto_speed.run_scheduled(network=WIFI, profile=HOME, minutes=60, now=now)
    assert first["status"] == "ok" and first["download_mbps"] == 480.0

    (sample,) = data_usage.load_speed_samples(profile_id="home")
    assert (sample.provider, sample.network_kind) == ("Cloudflare", "wifi")

    # 30 min depois ainda não venceu; 61 min depois roda de novo, outro provedor.
    again = auto_speed.run_scheduled(
        network=WIFI, profile=HOME, minutes=60, now=now + 1800
    )
    assert again == {"status": "not_due"}
    later = auto_speed.run_scheduled(
        network=WIFI, profile=HOME, minutes=60, now=now + 3660
    )
    assert later["status"] == "ok"
    assert tester.indexes == [0, 1]  # rodízio persistido entre execuções


def test_failed_run_retries_in_fifteen_minutes(monkeypatch):
    _use_tester(monkeypatch, _FakeTester(None))
    now = 1_800_000_000.0
    outcome = auto_speed.run_scheduled(network=WIFI, profile=HOME, minutes=120, now=now)
    assert outcome["status"] == "failed"
    assert data_usage.load_speed_samples() == []
    assert not auto_speed.is_due(120, now + 14 * 60)
    assert auto_speed.is_due(120, now + 16 * 60)


def test_concurrent_run_is_reported_busy(monkeypatch):
    _use_tester(monkeypatch, _FakeTester(_result()))
    now = 1_800_000_000.0
    auto_speed._save_state({"running_since": now - 30})
    assert auto_speed.run_scheduled(
        force=True, network=WIFI, profile=HOME, minutes=60, now=now
    ) == {"status": "busy"}
    # Uma execução travada há mais de 10 min deixa de bloquear.
    auto_speed._save_state({"running_since": now - 700})
    assert (
        auto_speed.run_scheduled(
            force=True, network=WIFI, profile=HOME, minutes=60, now=now
        )["status"]
        == "ok"
    )


def test_cron_entry_is_added_and_removed_preserving_others(monkeypatch):
    stored = ["0 3 * * * outra-tarefa"]

    def fake_run(cmd, **kwargs):
        if cmd[1] == "-l":
            return types.SimpleNamespace(returncode=0, stdout="\n".join(stored), stderr="")
        stored[:] = [line for line in kwargs["input"].splitlines() if line]
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(auto_speed.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(auto_speed.subprocess, "run", fake_run)

    assert auto_speed.set_cron_enabled(True)[0] and auto_speed.is_cron_enabled()
    assert stored[0] == "0 3 * * * outra-tarefa"
    assert stored[1].startswith("*/15 * * * * /bin/varedura-speedtest --scheduled")
    assert auto_speed.set_cron_enabled(True)[0] and len(stored) == 2  # idempotente
    assert auto_speed.set_cron_enabled(False)[0]
    assert stored == ["0 3 * * * outra-tarefa"] and not auto_speed.is_cron_enabled()
    assert "schtasks /Create" in auto_speed.windows_task_command()


def test_measure_parallel_ignores_warmup_and_sums_streams():
    from monitor.speed_providers_http import measure_parallel

    def worker(stop: threading.Event, add) -> None:
        while not stop.is_set():
            add(125_000)  # 1 Mbit a cada 10 ms por fluxo
            time.sleep(0.01)

    mbps = measure_parallel(worker, streams=3, duration=0.6, warmup=0.2)
    assert 150 < mbps < 330  # ~3 fluxos x ~100 Mbps (folga para a máquina)


def test_websocket_client_frame_header_and_worker_registry():
    from monitor.speed_providers_http import _WebSocket
    from monitor.speed_tester import ContinuousSpeedTester
    from monitor.speed_worker import PROVIDER_IDS

    assert _WebSocket.binary_header(100) == b"\x82\xe4\0\0\0\0"
    assert _WebSocket.binary_header(8192)[:4] == b"\x82\xfe\x20\x00"
    assert len(_WebSocket.binary_header(1 << 20)) == 14

    ids = [item[0] for item in ContinuousSpeedTester._available_provider_ids()]
    assert {"cloudflare", "mlab"} <= set(ids) <= set(PROVIDER_IDS)


def test_unmeasured_upload_is_excluded_from_verdict():
    from monitor.plan_profiles import SpeedSample, evaluate_speed

    stamp = datetime.datetime(2026, 11, 21, 12, 0)
    verdict = evaluate_speed(
        HOME, [SpeedSample(stamp, 590, 0), SpeedSample(stamp, 580, 280)]
    )
    # O upload 0 (não medido) não derruba a média nem conta como violação.
    assert verdict.avg_up == 280 and verdict.instant_violations == 0
    assert verdict.status == "ok"


@pytest.mark.asyncio
async def test_settings_saves_auto_speed_interval(monkeypatch, tmp_path):
    from cli import ui_shared
    from cli.textual_app import VareduraTextualApp
    from textual.widgets import Input, TabbedContent

    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    ui_shared.save_network_config(
        {
            "target_onboarding_completed": True,
            "selected_target_ids": ["cloudflare_ipv4"],
            "primary_target_id": "cloudflare_ipv4",
            "custom_targets": [],
            "league_auto_detect": False,
        }
    )
    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "settings"
        for _ in range(30):
            await pilot.pause()
            if "settings" in app._hydrated_tabs:
                break
        await pilot.pause()
        field = app.query_one("#auto-speed-minutes", Input)
        field.value = "5"  # abaixo do mínimo: vira 15
        assert app._save_network_settings() is True
        await pilot.pause()
        assert ui_shared.load_network_config()["auto_speed_minutes"] == 15
        assert field.value == "15"

        # Em dados móveis o agendador da TUI nem tenta rodar.
        started: list[int] = []
        app._run_auto_speed = lambda minutes: started.append(minutes)
        app._active_network = MOBILE
        app._auto_speed_tick()
        assert started == []
        app._active_network = WIFI
        app._auto_speed_tick()
        assert started == [15]
