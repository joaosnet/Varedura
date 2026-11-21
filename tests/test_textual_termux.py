"""Tests for Termux/Android native UI, responsiveness, shortcuts and alerts."""

from __future__ import annotations

import asyncio
from pathlib import Path
import shutil

import pytest

from cli import ui_shared
from cli.textual_app import VareduraTextualApp
from i18n import init as i18n_init
from textual.widgets import Button, Input, Label, Static, Switch, TabbedContent
from varedura.termux_env import AndroidTelemetry, TermuxService, TermuxTool
from varedura.updater import UpdateResult


@pytest.fixture(autouse=True)
def isolated_termux_env(monkeypatch, tmp_path):
    monkeypatch.setenv("VAREDURA_TERMUX_MODE", "1")
    monkeypatch.delenv("VAREDURA_SHOW_DOCKER", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    monkeypatch.setattr(ui_shared, "MCP_CONFIG_FILE", tmp_path / ".vscode" / "mcp.json")

    import i18n
    import monitor.netinfo as netinfo
    import monitor.port_scanner as scanner
    import monitor.stalker as stalker

    monkeypatch.setattr(i18n, "_PREFS_FILE", tmp_path / "lang.json")
    i18n_init("en")
    monkeypatch.setattr(netinfo, "detect_default_gateway", lambda: "192.168.18.1")
    monkeypatch.setattr(stalker, "run_ping", lambda host: 15.0)
    monkeypatch.setattr(
        scanner,
        "get_system_network_stats",
        lambda: {
            "memoria_percent": 40.0,
            "memoria_usada_gb": 3.2,
            "memoria_total_gb": 8.0,
            "bytes_enviados_mb": 12.0,
            "bytes_recebidos_mb": 34.0,
        },
    )
    monkeypatch.setattr(
        "varedura.termux_env.collect_android_telemetry",
        lambda: AndroidTelemetry(
            battery_pct=87,
            battery_status="Discharging",
            battery_temp_c=31.5,
            wifi_ip="192.168.18.242",
            mobile_ip="10.20.30.40",
            rx_bytes=1024 * 1024,
            tx_bytes=512 * 1024,
            mobile_rx_bytes=2048 * 1024,
            mobile_tx_bytes=256 * 1024,
            mem_used_mb=3200.0,
            mem_total_mb=8000.0,
            uptime_str="2h 15m",
            user="u0_a123",
            has_root=True,
        ),
    )
    monkeypatch.setattr("varedura.termux_env.discover_termux_tools", lambda: [])
    monkeypatch.setattr(
        "varedura.termux_env.list_termux_services",
        lambda: [
            TermuxService("sshd", "OpenSSH", True, True, "port 8022"),
            TermuxService("crond", "Cron", False, True),
            TermuxService("wakelock", "Wake Lock", False, True),
            TermuxService("claro_daemon", "Claro Daemon", False, False),
        ],
    )
    monkeypatch.setattr("varedura.updater.is_cron_update_enabled", lambda: False)
    monkeypatch.setattr(
        "varedura.updater.get_repo_status",
        lambda: {
            "branch": "main",
            "commit": "abc1234",
            "dirty": False,
            "token_source": "env:GHG_TOKEN",
            "cron_enabled": False,
            "last_check": None,
        },
    )
    monkeypatch.setattr(
        "varedura.updater.update_repository",
        lambda **kwargs: UpdateResult(status="up_to_date", branch="main"),
    )

    ui_shared.save_network_config(
        {
            "network_schema_version": 3,
            "target_onboarding_completed": True,
            "selected_target_ids": ["cloudflare_ipv4"],
            "primary_target_id": "cloudflare_ipv4",
            "custom_targets": [],
            "league_auto_detect": False,
        }
    )
    yield
    i18n_init("en")


async def wait_until(predicate, pilot, attempts: int = 80) -> None:
    for _ in range(attempts):
        await pilot.pause()
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not reached")


@pytest.mark.asyncio
async def test_docker_tab_visibility_in_termux_mode(monkeypatch):
    orig_which = shutil.which
    monkeypatch.setattr(
        shutil,
        "which",
        lambda name: None if name == "docker" else orig_which(name),
    )
    app = VareduraTextualApp()
    async with app.run_test(size=(56, 36)) as pilot:
        await pilot.pause()
        tabs = app.query_one("#main-tabs", TabbedContent)
        pane_ids = [pane.id for pane in tabs.query("TabPane")]
        assert "docker" not in pane_ids
        assert "termux" in pane_ids

    monkeypatch.setenv("VAREDURA_SHOW_DOCKER", "1")
    app2 = VareduraTextualApp()
    async with app2.run_test(size=(56, 36)) as pilot:
        await pilot.pause()
        tabs2 = app2.query_one("#main-tabs", TabbedContent)
        pane_ids2 = [pane.id for pane in tabs2.query("TabPane")]
        assert "docker" in pane_ids2
        assert "termux" in pane_ids2


@pytest.mark.asyncio
@pytest.mark.parametrize("size", [(45, 32), (56, 36)])
async def test_narrow_mobile_dashboard_layout_and_quick_actions(monkeypatch, tmp_path, size):
    (tmp_path / ".claro_suite").mkdir()
    app = VareduraTextualApp()
    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        assert app.screen.has_class("mobile-narrow")
        assert app.query_one("#dashboard-grid").has_class("mobile-narrow")
        for btn_id in (
            "#dash-btn-network",
            "#dash-btn-cameras",
            "#dash-btn-termux",
            "#dash-btn-claro",
            "#dash-btn-screenshot",
            "#dash-btn-settings",
        ):
            assert app.query_one(btn_id, Button)

        await pilot.click("#dash-btn-termux")
        await wait_until(lambda: "termux" in app._hydrated_tabs, pilot)
        assert app.query_one("#main-tabs", TabbedContent).active == "termux"


@pytest.mark.asyncio
async def test_termux_hub_claro_and_services_subtabs(monkeypatch, tmp_path):
    # Without ~/.claro_suite, termux-claro subtab is omitted
    app_no_claro = VareduraTextualApp()
    async with app_no_claro.run_test(size=(56, 36)) as pilot:
        await pilot.pause()
        app_no_claro.query_one("#main-tabs", TabbedContent).active = "termux"
        await wait_until(lambda: "termux" in app_no_claro._hydrated_tabs, pilot)
        sub_ids = [
            p.id for p in app_no_claro.query_one("#termux-subtabs", TabbedContent).query("TabPane")
        ]
        assert sub_ids == ["termux-hub", "termux-services"]

    # With ~/.claro_suite and available claro_daemon
    (tmp_path / ".claro_suite").mkdir()
    monkeypatch.setenv("GHG_TOKEN", "ghp_SUPER_SECRET_RAW_TOKEN_VALUE")
    monkeypatch.setattr(
        "varedura.termux_env.list_termux_services",
        lambda: [
            TermuxService("sshd", "OpenSSH", True, True, "port 8022"),
            TermuxService("crond", "Cron", False, True),
            TermuxService("wakelock", "Wake Lock", False, True),
            TermuxService("claro_daemon", "Claro Daemon", True, True),
        ],
    )
    toggled: list[tuple[str, bool]] = []
    monkeypatch.setattr(
        "varedura.termux_env.toggle_termux_service",
        lambda sid, en: toggled.append((sid, en)) or (True, "ok"),
    )
    ussd_calls: list[list[str]] = []
    monkeypatch.setattr(
        "cli.textual_termux.subprocess.run",
        lambda cmd, **kw: ussd_calls.append(list(cmd))
        or type("P", (), {"returncode": 0, "stdout": "OK", "stderr": ""})(),
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(56, 36)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "termux"
        await wait_until(lambda: "termux" in app._hydrated_tabs, pilot)
        await wait_until(
            lambda: "87%" in str(app.query_one("#termux-lbl-battery", Label).render()),
            pilot,
        )

        subtabs = app.query_one("#termux-subtabs", TabbedContent)
        assert [p.id for p in subtabs.query("TabPane")] == [
            "termux-hub",
            "termux-claro",
            "termux-services",
        ]

        # Claro USSD button runs in background thread
        subtabs.active = "termux-claro"
        await pilot.pause()
        app.query_one("#termux-claro-ussd").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#termux-claro-ussd")
        await wait_until(lambda: bool(ussd_calls), pilot)
        assert ussd_calls[0] == ["cmd", "phone", "ussd", "*1052#"]

        # Services switches present including claro_daemon and git-cron
        subtabs.active = "termux-services"
        await pilot.pause()
        for sw_id in (
            "#sw-termux-sshd",
            "#sw-termux-claro_daemon",
            "#sw-termux-crond",
            "#sw-termux-wakelock",
            "#sw-termux-git-cron",
        ):
            assert app.query_one(sw_id, Switch)

        # Flipping switch triggers toggle_termux_service (when not syncing)
        crond_sw = app.query_one("#sw-termux-crond", Switch)
        crond_sw.value = True
        await wait_until(lambda: ("crond", True) in toggled, pilot)

        # Raw GitHub token never rendered in UI
        git_txt = str(app.query_one("#termux-git-status", Static).render())
        assert "ghp_SUPER_SECRET_RAW_TOKEN_VALUE" not in git_txt
        assert "GHG_TOKEN" in git_txt


@pytest.mark.asyncio
async def test_termux_tool_launcher_modes_and_arg_guard(monkeypatch):
    tools = [
        TermuxTool("portscan", "portscan", ("portscan",), "network", "suspend_pause", needs_arg=True),
        TermuxTool("micro", "micro", ("micro",), "editor", "suspend"),
        TermuxTool("web", "painel-web", ("painel-web",), "system", "background"),
    ]
    monkeypatch.setattr("varedura.termux_env.discover_termux_tools", lambda: tools)
    runs: list[list[str]] = []
    popens: list[list[str]] = []
    monkeypatch.setattr(
        "cli.textual_termux.subprocess.run",
        lambda cmd, **kw: runs.append(list(cmd)) or type("P", (), {"returncode": 0})(),
    )
    monkeypatch.setattr(
        "cli.textual_termux.subprocess.Popen",
        lambda cmd, **kw: popens.append(list(cmd)) or type("P", (), {"pid": 999})(),
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(56, 36)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "termux"
        await wait_until(lambda: "termux" in app._hydrated_tabs, pilot)
        await pilot.pause()

        # needs_arg empty -> warns & focuses #termux-tool-arg without launching
        btn_port = app.query_one("#termux-tool-portscan", Button)
        btn_port.scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#termux-tool-portscan")
        await pilot.pause()
        assert runs == []
        assert app.focused is app.query_one("#termux-tool-arg", Input)

        # Fill arg and launch
        app.query_one("#termux-tool-arg", Input).value = "192.168.1.1"
        await pilot.click("#termux-tool-portscan")
        await pilot.pause()
        assert runs == [["portscan", "192.168.1.1"]]

        # Background tool uses Popen
        btn_web = app.query_one("#termux-tool-web", Button)
        btn_web.scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#termux-tool-web")
        await pilot.pause()
        assert popens == [["painel-web", "192.168.1.1"]]


@pytest.mark.asyncio
async def test_termux_onboarding_non_blocking_f12_and_screenshot(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    ui_shared.PREFS_FILE.unlink(missing_ok=True)
    kbd_calls: list[str] = []
    opened: list[str] = []
    bg_update_calls: list[dict] = []

    monkeypatch.setattr(
        "varedura.termux_env.toggle_keyboard_page",
        lambda: kbd_calls.append("toggled") or (True, "OK"),
    )
    monkeypatch.setattr(
        "varedura.termux_env.open_file_or_url",
        lambda path: opened.append(path) or True,
    )
    monkeypatch.setattr(
        "varedura.updater.update_repository",
        lambda **kwargs: bg_update_calls.append(kwargs)
        or UpdateResult(status="updated", branch="main", commits_pulled=2),
    )

    monkeypatch.setattr(
        "varedura.termux_env.extra_key_macros",
        lambda path=None: ("menu", "netscan", "toggle-page"),
    )
    suspended: list[list[str]] = []

    app = VareduraTextualApp()
    app._run_suspended_command = lambda cmd, pause=False: suspended.append(cmd) or 0
    async with app.run_test(size=(45, 32)) as pilot:
        await wait_until(
            lambda: ui_shared.load_network_config().get("target_onboarding_completed") is True,
            pilot,
        )
        await wait_until(lambda: bool(app._macro_commands), pilot)
        # Non-blocking onboarding: no modal pushed!
        assert len(app.screen_stack) == 1
        assert bg_update_calls and bg_update_calls[0].get("force") is False

        # F12 toggles extra-keys page
        await pilot.press("f12")
        await pilot.pause()
        assert kbd_calls == ["toggled"]

        # Macro das teclas extras ("\ntoggle-page\n") também aciona o alternador
        await pilot.press("enter", *"toggle-page", "enter")
        await pilot.pause()
        assert kbd_calls == ["toggled", "toggled"]

        # "\nnetscan\n": abre a ferramenta em vez de disparar os atalhos
        # das letras (o "s" abriria Configurações).
        await pilot.press("enter", *"netscan", "enter")
        await pilot.pause()
        assert suspended == [["netscan"]]
        assert app.query_one("#main-tabs").active == "dashboard"

        # "\nmenu\n" volta ao Painel a partir de outra aba.
        app.query_one("#main-tabs").active = "settings"
        await pilot.pause()
        await pilot.press("enter", *"menu", "enter")
        await pilot.pause()
        assert app.query_one("#main-tabs").active == "dashboard"

        # Um Enter comum continua chegando ao widget em foco (após a janela).
        pressed: list[str] = []
        app._switch_main_tab = lambda tab, **kw: pressed.append(tab)
        app.query_one("#dash-btn-network").focus()
        await pilot.press("enter")
        await wait_until(lambda: pressed == ["network"], pilot)

        # Screenshot opens SVG via termux-open / open_file_or_url
        svg_path = app.action_capture_screenshot()
        assert svg_path is not None and svg_path.exists()
        assert opened == [str(svg_path)]


@pytest.mark.asyncio
async def test_termux_lol_disabled_and_outage_notifications(monkeypatch):
    import monitor.ping_scheduler as ping_scheduler
    import monitor.port_scanner as scanner
    from monitor.ping_targets import PingProbeResult, PingStatus, PingTarget, TargetCategory

    monkeypatch.setattr(ping_scheduler.PingScheduler, "start", lambda self, cb: None)
    monkeypatch.setattr(ping_scheduler.PingScheduler, "stop", lambda self, wait=False: None)
    monkeypatch.setattr(scanner, "run_full_scan", lambda: scanner.PortScannerState())

    sent_notifs: list[tuple[str, str, str]] = []
    monkeypatch.setattr(
        "varedura.termux_env.send_termux_notification",
        lambda title, content, *, notif_id="varedura", vibrate=False: sent_notifs.append(
            (title, content, notif_id)
        )
        or True,
    )

    ui_shared.save_network_config(
        {
            "network_schema_version": 3,
            "target_onboarding_completed": True,
            "selected_target_ids": ["cloudflare_ipv4"],
            "primary_target_id": "cloudflare_ipv4",
            "custom_targets": [],
            "league_auto_detect": True,
        }
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(56, 36)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        await wait_until(lambda: app.network_running, pilot)

        # LeagueMatchDetector must stay disabled on Android
        assert app._league_detector is None

        target = PingTarget("cloudflare_ipv4", "Cloudflare", "1.1.1.1", TargetCategory.INFRASTRUCTURE)
        app._target_map["cloudflare_ipv4"] = target
        app._primary_target_id = "cloudflare_ipv4"

        for _ in range(6):
            app._accept_ping_result(
                PingProbeResult(
                    "cloudflare_ipv4",
                    app._network_run_generation,
                    "1.1.1.1",
                    PingStatus.TIMEOUT,
                    0.0,
                    1.0,
                    None,
                ),
                run_generation=app._network_run_generation,
            )
        assert len(sent_notifs) == 1
        assert sent_notifs[0][2] == "varedura-net"

        # Recovery sends once
        app._accept_ping_result(
            PingProbeResult(
                "cloudflare_ipv4",
                app._network_run_generation,
                "1.1.1.1",
                PingStatus.SUCCESS,
                0.0,
                0.02,
                18.0,
            ),
            run_generation=app._network_run_generation,
        )
        assert len(sent_notifs) == 2
        assert "18 ms" in sent_notifs[1][1]
