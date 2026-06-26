import asyncio

import pytest

from cli import ui_shared
from cli.textual_app import ShutdownScreen, VareduraTextualApp
from i18n import get_language, init as i18n_init
from monitor.port_scanner import PortInfo, PortScannerState, ProcessConnections
from textual.widgets import DataTable, Digits, ProgressBar, Sparkline, TabbedContent


@pytest.fixture(autouse=True)
def isolated_ui_prefs(monkeypatch, tmp_path):
    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    monkeypatch.setattr(ui_shared, "MCP_CONFIG_FILE", tmp_path / ".vscode" / "mcp.json")

    import i18n

    monkeypatch.setattr(i18n, "_PREFS_FILE", tmp_path / "lang.json")
    i18n_init("en")
    yield
    i18n_init("en")


async def wait_until(predicate, pilot, attempts: int = 30) -> None:
    for _ in range(attempts):
        await pilot.pause()
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not reached")


@pytest.mark.asyncio
async def test_textual_dashboard_renders_and_menu_switches_to_cleanup():
    app = VareduraTextualApp()

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()

        tabs = app.query_one("#main-tabs", TabbedContent)
        assert tabs.active == "dashboard"

        await pilot.press("down", "enter")
        await pilot.pause()

        assert tabs.active == "docker"


@pytest.mark.asyncio
async def test_textual_settings_save_recording_and_language():
    app = VareduraTextualApp()

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "settings"
        await pilot.pause()

        app.query_one("#recording-switch").value = False
        app.query_one("#language-select").value = "pt"
        # The settings form scrolls; bring the save button into view first.
        app.query_one("#save-settings").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#save-settings")
        await pilot.pause()

        assert ui_shared.load_recording_pref() is False
        assert get_language() == "pt"


@pytest.mark.asyncio
async def test_textual_network_settings_detect_and_apply(monkeypatch):
    import monitor.netinfo as netinfo
    import monitor.stalker as stalker
    from monitor.speed_tester import speed_config
    from textual.widgets import Input

    monkeypatch.setattr(netinfo, "detect_default_gateway", lambda: "10.1.2.3")

    app = VareduraTextualApp()
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        # Autodetected gateway is applied to the live config and prefilled.
        assert stalker.config.gateway_ip == "10.1.2.3"

        app.query_one("#main-tabs", TabbedContent).active = "settings"
        await pilot.pause()
        assert app.query_one("#net-gateway", Input).value == "10.1.2.3"

        app.query_one("#net-threshold", Input).value = "175"
        app.query_one("#net-down", Input).value = "300"
        app.query_one("#save-settings").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#save-settings")
        await pilot.pause()

        assert stalker.config.lag_threshold_ms == 175
        assert speed_config.velocidade_contratada_down == 300.0


@pytest.mark.asyncio
async def test_textual_cleanup_preferences_are_saved():
    app = VareduraTextualApp()

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "docker"
        await pilot.pause()

        app.query_one("#cleanup-containers").value = False
        app.query_one("#save-cleanup").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#save-cleanup")
        await pilot.pause()

        assert ui_shared.get_cleanup_steps()["containers"] is False


@pytest.mark.asyncio
async def test_textual_ports_view_populates_in_network_tab(monkeypatch):
    """The merged ports view (formerly the standalone Scanner tab) fills the
    network ports table with one row per listening TCP/UDP port."""
    fake_state = PortScannerState(
        listening_tcp=[PortInfo(443, 123, "python.exe", "TCP", "0.0.0.0")],
        listening_udp=[PortInfo(5353, 456, "svchost.exe", "UDP", "127.0.0.1")],
        top_connections=[ProcessConnections(111, "chrome.exe", 3, 42.0, "running")],
        total_tcp=1,
        total_udp=1,
        total_established=2,
        last_scan_time="12:00:00",
    )

    _patch_network(monkeypatch)
    import monitor.port_scanner as scanner
    import monitor.stalker as stalker

    monkeypatch.setattr(scanner, "run_full_scan", lambda: fake_state)
    # Scan on the very first tick (which renders immediately) so the ports table
    # fills without cranking the interval (a fast interval races with teardown).
    monkeypatch.setattr(stalker.config, "port_scan_interval", 1, raising=False)

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        app.query_one("#network-subtabs", TabbedContent).active = "net-ports-tab"
        await pilot.pause()

        await wait_until(
            lambda: app.query_one("#network-ports-table", DataTable).row_count == 2,
            pilot,
        )
        # Merged processes view also fills from get_top_network_hogs.
        assert app.query_one("#network-procs-table", DataTable).row_count >= 1


@pytest.mark.asyncio
async def test_textual_scanner_menu_option_opens_network_ports(monkeypatch):
    """The legacy 'Port Scanner' menu entry now jumps to the network ports view."""
    _patch_network(monkeypatch)
    app = VareduraTextualApp()

    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        app.query_one("#tool-menu").focus()
        # Move to the third tool option ("Port Scanner") and select it.
        await pilot.press("down", "down", "enter")
        await pilot.pause()

        assert app.query_one("#main-tabs", TabbedContent).active == "network"
        assert app.query_one("#network-subtabs", TabbedContent).active == "net-ports-tab"


def _patch_network(monkeypatch):
    """Make the network worker deterministic and offline."""
    import monitor.stalker as stalker
    import monitor.speed_tester as speed_tester
    import monitor.port_scanner as scanner

    monkeypatch.setattr(stalker, "run_ping", lambda host: 12.0)
    monkeypatch.setattr(
        stalker, "get_top_network_hogs", lambda: [(111, "chrome.exe", 3 * 1024 * 1024)]
    )
    monkeypatch.setattr(speed_tester, "start_continuous_testing", lambda: None)
    monkeypatch.setattr(speed_tester, "stop_continuous_testing", lambda: None)
    monkeypatch.setattr(
        speed_tester.ContinuousSpeedTester,
        "get_stats_snapshot",
        lambda self: {
            "results_by_provider": {},
            "is_testing": False,
            "current_provider": "",
            "progress_mbps": 0.0,
            "progress_phase": "",
            "test_count": 0,
            "last_error": None,
        },
    )
    monkeypatch.setattr(scanner, "run_full_scan", lambda: PortScannerState())


@pytest.mark.asyncio
async def test_textual_network_tab_updates(monkeypatch):
    _patch_network(monkeypatch)
    app = VareduraTextualApp()

    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        await pilot.pause()

        # Widgets exist
        assert app.query_one("#gateway-digits", Digits)
        assert app.query_one("#external-spark", Sparkline)

        # Tab activation auto-starts monitoring; ensure a tick rendered.
        await wait_until(
            lambda: app.query_one("#gateway-digits", Digits).value == "12",
            pilot,
        )
        assert app.query_one("#network-procs-table", DataTable).row_count >= 1

        app.query_one("#network-stop").disabled is False
        await pilot.click("#network-stop")
        await wait_until(lambda: not app.network_running, pilot)


@pytest.mark.asyncio
async def test_textual_network_health_card_updates(monkeypatch):
    _patch_network(monkeypatch)
    app = VareduraTextualApp()
    async with app.run_test(size=(140, 50)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        await pilot.pause()
        await wait_until(
            lambda: app.query_one("#health-digits", Digits).value not in ("", "--"),
            pilot,
        )
        assert int(app.query_one("#health-digits", Digits).value) >= 80  # 12ms ping -> top tier
        assert "sub20" in app._game.achievements


@pytest.mark.asyncio
async def test_textual_docker_reward_and_achievement(monkeypatch):
    class FakeCleaner:
        def __init__(self, console=None):
            self.console = console
            self.daily_log_writer = None
            self.total_space_saved = 6.0

        def docker_cleanup(self, prune_only=None, steps=None):
            return True

        def stop_docker_wsl(self):
            return True

        def configure_wsl_sparse(self):
            return True

        def compact_vhdx_files(self):
            return True

        def cleanup_temp_files(self):
            return True

        def cleanup_recycle_bin(self):
            return True

    import docker_cleaner.core as core

    monkeypatch.setattr(core, "WSLDockerCleaner", FakeCleaner)
    app = VareduraTextualApp()
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "docker"
        await pilot.pause()
        app.query_one("#run-cleanup").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#run-cleanup")
        await wait_until(lambda: not app.cleanup_running, pilot)

        assert app.query_one("#cleanup-freed", Digits).value == "6.0"
        assert "docker_first" in app._game.achievements
        assert "docker5gb" in app._game.achievements


@pytest.mark.asyncio
async def test_textual_network_option_activates_tab_without_modal(monkeypatch):
    _patch_network(monkeypatch)
    app = VareduraTextualApp()

    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        # First option in the tool menu is "network".
        app.query_one("#tool-menu").focus()
        await pilot.press("enter")
        await pilot.pause()

        assert app.query_one("#main-tabs", TabbedContent).active == "network"
        assert len(app.screen_stack) == 1  # no modal pushed


@pytest.mark.asyncio
async def test_textual_dashboard_poller_populates_system_stats(monkeypatch):
    """The always-on lightweight poller fills system stats without the heavy
    network monitor running."""
    import monitor.port_scanner as scanner
    import monitor.stalker as stalker

    monkeypatch.setattr(stalker, "run_ping", lambda host: 12.0)
    monkeypatch.setattr(
        scanner,
        "get_system_network_stats",
        lambda: {
            "memoria_percent": 55.0,
            "memoria_usada_gb": 8.0,
            "memoria_total_gb": 16.0,
            "bytes_enviados_mb": 100.0,
            "bytes_recebidos_mb": 200.0,
        },
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await wait_until(
            lambda: app._dash_stats.get("memoria_percent") == 55.0,
            pilot,
        )


@pytest.mark.asyncio
async def test_textual_cleanup_summary_is_reactive(monkeypatch):
    """Toggling a cleanup checkbox refreshes the summary immediately."""
    import cli.textual_app as ta

    calls = []
    original = ta.build_cleanup_status_panel
    monkeypatch.setattr(
        ta,
        "build_cleanup_status_panel",
        lambda steps=None: calls.append(steps) or original(steps),
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "docker"
        await pilot.pause()
        calls.clear()
        checkbox = app.query_one("#cleanup-containers")
        checkbox.value = not checkbox.value
        await pilot.pause()
        assert calls, "toggling a checkbox should rebuild the cleanup summary"


@pytest.mark.asyncio
async def test_textual_settings_status_is_reactive(monkeypatch):
    """Flipping the recording switch updates the settings status live (pre-save)."""
    import cli.textual_app as ta

    calls = []
    original = ta.build_settings_status_table
    monkeypatch.setattr(
        ta,
        "build_settings_status_table",
        lambda rec, lang: calls.append((rec, lang)) or original(rec, lang),
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "settings"
        await pilot.pause()
        calls.clear()
        switch = app.query_one("#recording-switch")
        switch.value = not switch.value
        await pilot.pause()
        assert calls, "toggling the recording switch should refresh the status panel"


@pytest.mark.asyncio
async def test_textual_cleanup_worker_uses_fake_cleaner(monkeypatch):
    calls = []

    class FakeCleaner:
        def __init__(self, console=None):
            self.console = console
            self.daily_log_writer = None

        def docker_cleanup(self, prune_only=None, steps=None):
            calls.append(("docker_cleanup", prune_only, steps))
            self.console.print(f"cleanup {prune_only}")
            return True

        def stop_docker_wsl(self):
            calls.append(("stop_docker_wsl", None, None))
            return True

        def configure_wsl_sparse(self):
            calls.append(("configure_wsl_sparse", None, None))
            return True

        def compact_vhdx_files(self):
            calls.append(("compact_vhdx_files", None, None))
            return True

        def cleanup_temp_files(self):
            calls.append(("cleanup_temp_files", None, None))
            return True

        def cleanup_recycle_bin(self):
            calls.append(("cleanup_recycle_bin", None, None))
            return True

    import docker_cleaner.core as core

    monkeypatch.setattr(core, "WSLDockerCleaner", FakeCleaner)
    app = VareduraTextualApp()

    async with app.run_test(size=(100, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "docker"
        await pilot.pause()
        app.query_one("#run-cleanup").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#run-cleanup")

        await wait_until(
            lambda: not app.cleanup_running and bool(calls),
            pilot,
        )

        progress = app.query_one("#cleanup-progress", ProgressBar)
        assert progress.progress == progress.total
        assert [call[1] for call in calls[:5]] == [
            "containers",
            "images",
            "volumes",
            "networks",
            "builder",
        ]


def test_shutdown_stop_monitors_sets_events():
    app = VareduraTextualApp()
    app._sd_stop_monitors()
    assert app._network_stop.is_set()
    assert app._dash_stop.is_set()


def test_shutdown_close_resources_terminates_players():
    app = VareduraTextualApp()

    class FakeProc:
        def __init__(self):
            self.terminated = False

        def poll(self):
            return None  # ainda vivo

        def terminate(self):
            self.terminated = True

    proc = FakeProc()
    app._players = [proc]
    app._sd_close_resources()
    assert proc.terminated


@pytest.mark.asyncio
async def test_quit_exits_immediately_when_idle():
    app = VareduraTextualApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        # Nada pesado rodando -> sai na hora, sem tela de encerramento.
        app.action_quit()
        assert app._shutting_down is False
        assert not any(isinstance(s, ShutdownScreen) for s in app.screen_stack)


@pytest.mark.asyncio
async def test_quit_shows_shutdown_screen_when_busy(monkeypatch):
    _patch_network(monkeypatch)
    # Não deixa o worker fechar o app; só queremos verificar a tela.
    monkeypatch.setattr(VareduraTextualApp, "_run_shutdown", lambda self: None)
    app = VareduraTextualApp()
    async with app.run_test(size=(120, 45)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        await wait_until(lambda: app.network_running, pilot)
        app.action_quit()
        await pilot.pause()
        assert app._shutting_down is True
        assert any(isinstance(s, ShutdownScreen) for s in app.screen_stack)
