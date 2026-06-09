import asyncio

import pytest

from cli import ui_shared
from cli.textual_app import VareduraTextualApp
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

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "settings"
        await pilot.pause()

        app.query_one("#recording-switch").value = False
        app.query_one("#language-select").value = "pt"
        await pilot.click("#save-settings")
        await pilot.pause()

        assert ui_shared.load_recording_pref() is False
        assert get_language() == "pt"


@pytest.mark.asyncio
async def test_textual_cleanup_preferences_are_saved():
    app = VareduraTextualApp()

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "docker"
        await pilot.pause()

        app.query_one("#cleanup-containers").value = False
        await pilot.click("#save-cleanup")
        await pilot.pause()

        assert ui_shared.get_cleanup_steps()["containers"] is False


@pytest.mark.asyncio
async def test_textual_scanner_worker_populates_tables(monkeypatch):
    fake_state = PortScannerState(
        listening_tcp=[PortInfo(8080, 123, "python.exe", "TCP", "127.0.0.1")],
        listening_udp=[],
        top_connections=[ProcessConnections(123, "python.exe", 2, 42.0, "running")],
        total_tcp=1,
        total_udp=0,
        total_established=2,
        last_scan_time="12:00:00",
    )

    import monitor.port_scanner as scanner

    monkeypatch.setattr(scanner, "run_full_scan", lambda: fake_state)
    app = VareduraTextualApp()

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "scanner"
        await pilot.pause()
        await pilot.click("#run-scanner")

        await wait_until(
            lambda: app.query_one("#tcp-table", DataTable).row_count == 1,
            pilot,
        )

        assert app.query_one("#connections-table", DataTable).row_count == 1


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

    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "docker"
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
