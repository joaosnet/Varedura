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


def test_windows_background_uses_scheduled_task_without_console(monkeypatch):
    import importlib

    module = importlib.reload(auto_speed)  # desfaz os stubs do conftest
    calls: list[tuple[str, ...]] = []
    exists = {"task": False}

    def fake_schtasks(*args):
        calls.append(args)
        if args[0] == "/Query":
            return exists["task"], ""
        exists["task"] = args[0] == "/Create"
        return True, ""

    monkeypatch.setattr(module.os, "name", "nt")
    monkeypatch.setattr(module, "_schtasks", fake_schtasks)

    assert module.is_background_enabled() is False
    assert module.set_background_enabled(True)[0] and module.is_background_enabled()
    create = next(call for call in calls if call[0] == "/Create")
    assert create[1:7] == ("/F", "/SC", "MINUTE", "/MO", "15", "/TN")
    assert create[-1].endswith("-m monitor.auto_speed --scheduled")
    assert module.set_background_enabled(False)[0] and not module.is_background_enabled()
    # Desligar de novo não tenta apagar uma tarefa que não existe.
    before = len(calls)
    assert module.set_background_enabled(False) == (True, "already disabled")
    assert [call[0] for call in calls[before:]] == ["/Query"]


@pytest.mark.asyncio
async def test_background_switch_in_settings_drives_the_scheduler(monkeypatch, tmp_path):
    from cli import ui_shared
    from cli.textual_app import VareduraTextualApp
    from textual.widgets import Input, Label, Switch, TabbedContent

    state = {"on": False}
    monkeypatch.setattr(auto_speed, "is_background_enabled", lambda: state["on"])
    monkeypatch.setattr(
        auto_speed,
        "set_background_enabled",
        lambda enabled: (state.update(on=enabled) or True, "ok"),
    )
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
        status = app.query_one("#auto-speed-status", Label)
        assert "desligado" in str(status.content) or "off" in str(status.content)

        app.query_one("#auto-speed-minutes", Input).value = "60"
        app.query_one("#auto-speed-cron", Switch).value = True
        assert app._save_network_settings() is True
        for _ in range(40):
            await pilot.pause()
            if state["on"]:
                break
        assert state["on"] is True
        await pilot.pause()
        assert "60" in str(app.query_one("#auto-speed-status", Label).content)

        # Desligar o interruptor age na hora, sem precisar salvar.
        app.query_one("#auto-speed-cron", Switch).value = False
        for _ in range(40):
            await pilot.pause()
            if not state["on"]:
                break
        assert state["on"] is False
        app.query_one("#auto-speed-cron", Switch).value = True
        for _ in range(40):
            await pilot.pause()
            if state["on"]:
                break
        assert state["on"] is True

        # Intervalo 0 desliga também o agendamento do sistema.
        app.query_one("#auto-speed-minutes", Input).value = "0"
        assert app._save_network_settings() is True
        for _ in range(40):
            await pilot.pause()
            if not state["on"]:
                break
        assert state["on"] is False


@pytest.mark.asyncio
async def test_speed_tab_shows_plan_history_including_background_runs(monkeypatch, tmp_path):
    from cli import ui_shared
    from cli.textual_app import VareduraTextualApp
    from monitor.plan_profiles import SpeedSample
    from textual.widgets import DataTable, Label, TabbedContent

    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    ui_shared.save_network_config(
        {
            "target_onboarding_completed": True,
            "selected_target_ids": ["cloudflare_ipv4"],
            "primary_target_id": "cloudflare_ipv4",
            "custom_targets": [],
            "league_auto_detect": False,
            "plan_profiles": [HOME.to_dict()],
        }
    )
    now = datetime.datetime.now().replace(microsecond=0)
    # Gravadas por outro processo (cron / Agendador), não por esta sessão.
    data_usage.record_speed_sample(
        SpeedSample(now - datetime.timedelta(hours=2), 590, 290, 11, "Cloudflare", "", "home", "wifi")
    )
    data_usage.record_speed_sample(
        SpeedSample(now - datetime.timedelta(hours=1), 300, 0, 0, "Fast.com", "", "home", "wifi")
    )
    data_usage.record_speed_sample(
        SpeedSample(now, 999, 999, 5, "Outro plano", "", "sim", "mobile")
    )

    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    app._start_network = lambda: None
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app._refresh_active_plan()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        for _ in range(30):
            await pilot.pause()
            if "network" in app._hydrated_tabs:
                break
        await pilot.pause()
        app._render_speed_table({})

        table = app.query_one("#network-speed-table", DataTable)
        rows = [[str(cell) for cell in table.get_row_at(i)] for i in range(table.row_count)]
        # Só o plano ativo, mais recente primeiro; upload não medido vira "—".
        assert [row[1] for row in rows] == ["Fast.com", "Cloudflare"]
        assert rows[0][2:5] == ["300 Mbps", "—", "—"]
        assert rows[1][2:5] == ["590 Mbps", "290 Mbps", "11 ms"]

        summary = str(app.query_one("#network-speed-summary", Label).content)
        # Média de download (590+300)/2 = 445 -> 74% de 600: abaixo de 80%.
        assert "2 " in summary and "445" in summary and "74%" in summary

        # Um teste novo gravado em segundo plano aparece no próximo redesenho.
        data_usage.record_speed_sample(
            SpeedSample(now + datetime.timedelta(seconds=5), 610, 305, 9, "M-Lab NDT7", "", "home", "wifi")
        )
        app._render_speed_table({})
        assert str(table.get_row_at(0)[1]) == "M-Lab NDT7"
