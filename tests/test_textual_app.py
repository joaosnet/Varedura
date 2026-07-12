import asyncio

import pytest

from cli import ui_shared
from cli.textual_app import ShutdownScreen, TargetPingCard, VareduraTextualApp
from i18n import get_language, init as i18n_init
from monitor.port_scanner import PortInfo, PortScannerState, ProcessConnections
from textual.containers import Grid, VerticalScroll
from textual.widgets import DataTable, Digits, ProgressBar, Sparkline, TabbedContent


@pytest.fixture(autouse=True)
def isolated_ui_prefs(monkeypatch, tmp_path):
    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    monkeypatch.setattr(ui_shared, "MCP_CONFIG_FILE", tmp_path / ".vscode" / "mcp.json")

    import i18n

    monkeypatch.setattr(i18n, "_PREFS_FILE", tmp_path / "lang.json")
    i18n_init("en")
    # Most UI tests exercise established-user flows.  First-run onboarding has
    # dedicated coverage below and must not intercept unrelated pilot clicks.
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
        await wait_until(lambda: bool(list(app.query("#network-subtabs"))), pilot)
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
        assert (
            app.query_one("#network-subtabs", TabbedContent).active == "net-ports-tab"
        )


def _patch_network(monkeypatch):
    """Make the network worker deterministic and offline."""
    import monitor.stalker as stalker
    import monitor.speed_tester as speed_tester
    import monitor.port_scanner as scanner
    import monitor.ping_scheduler as ping_scheduler
    from monitor.ping_targets import PingProbeResult, PingStatus
    import time

    monkeypatch.setattr(stalker, "run_ping", lambda host: 12.0)

    def fake_probe(self, target, generation, cancel_event):
        started = time.monotonic()
        return PingProbeResult(
            target_id=target.id,
            generation=generation,
            host=target.host,
            status=PingStatus.SUCCESS,
            latency_ms=12.0,
            started_monotonic=started,
            completed_monotonic=started + 0.001,
        )

    monkeypatch.setattr(ping_scheduler.PingScheduler, "_run_probe", fake_probe)
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
        assert (
            int(app.query_one("#health-digits", Digits).value) >= 80
        )  # 12ms ping -> top tier
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
async def test_first_run_requires_selection_before_external_monitoring(monkeypatch):
    from cli.network_ui import TargetPickerScreen
    from textual.widgets import Select, SelectionList

    ui_shared.PREFS_FILE.unlink(missing_ok=True)
    import monitor.netinfo as netinfo

    monkeypatch.setattr(netinfo, "detect_default_gateway", lambda: None)
    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await wait_until(lambda: isinstance(app.screen, TargetPickerScreen), pilot)
        assert not app.network_running
        assert app._ping_scheduler is None

        picker = app.screen
        picker.query_one("#target-list", SelectionList).select("cloudflare_ipv4")
        await pilot.pause()
        picker.query_one("#target-primary", Select).value = "cloudflare_ipv4"
        await pilot.click("#target-save")
        await wait_until(lambda: len(app.screen_stack) == 1, pilot)

        config = ui_shared.load_network_config()
        assert config["target_onboarding_completed"] is True
        assert config["selected_target_ids"] == ["cloudflare_ipv4"]
        # Saving on the dashboard does not itself start background pings.
        assert not app.network_running


@pytest.mark.asyncio
async def test_hidden_tabs_are_composed_only_when_opened():
    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        assert not list(app.query("#network-pane"))
        assert not list(app.query("#cleanup-config"))

        app.query_one("#main-tabs", TabbedContent).active = "network"
        await wait_until(lambda: bool(list(app.query("#network-pane"))), pilot)
        assert not list(app.query("#cleanup-config"))


@pytest.mark.asyncio
async def test_network_monitor_does_not_auto_start_bandwidth_test(monkeypatch):
    _patch_network(monkeypatch)
    import monitor.speed_tester as speed_module

    monkeypatch.setattr(speed_module, "speed_tester", None)
    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        await wait_until(lambda: app.network_running, pilot)
        await pilot.pause()
        assert speed_module.speed_tester is None


def test_speed_worker_is_prepared_before_schedule_and_can_cancel_immediately(
    monkeypatch,
):
    import monitor.speed_tester as speed_module
    from monitor.speed_tester import ContinuousSpeedTester, SpeedTestConfig

    tester = ContinuousSpeedTester(SpeedTestConfig())
    events = []
    original_prepare = tester.prepare_single_test

    def prepare():
        events.append("prepare")
        return original_prepare()

    monkeypatch.setattr(tester, "prepare_single_test", prepare)
    monkeypatch.setattr(speed_module, "get_speed_tester", lambda: tester)

    class Widget:
        disabled = False

    class FakeApp:
        _speed_test_active = False
        start_button = Widget()
        cancel_button = Widget()

        def query_one(self, selector, *_args):
            return (
                self.start_button
                if selector == "#network-speed-start"
                else self.cancel_button
            )

        def _network_log(self, _message):
            pass

        def _run_speed_test_once(self, *, prepared=False):
            events.append(("worker", prepared))

    app = FakeApp()
    VareduraTextualApp._start_speed_test(app)
    assert events == ["prepare", ("worker", True)]

    VareduraTextualApp._cancel_speed_test(app)
    assert tester.run_once(prepared=True) is None
    assert tester.get_stats_snapshot()["last_error"] == "Teste cancelado"


def test_additional_targets_do_not_increment_gamification_counters():
    app = VareduraTextualApp()
    calls = []
    app._record_and_check = lambda health: calls.append(health)
    health = {"score": 90, "monitor_s": 1.0}

    app._render_ping_update(health, {}, record=False)
    assert calls == []
    app._render_ping_update(health, {}, record=True)
    assert calls == [health]


def test_target_card_statistics_include_jitter_trend_and_live_league_ip():
    from monitor.ping_targets import PingTarget, TargetCategory

    assert VareduraTextualApp._target_jitter([10.0, 20.0, 15.0]) == 7.5
    assert VareduraTextualApp._target_trend([10.0, 10.0, 20.0, 20.0]) == "↑"
    league = PingTarget(
        "league_match_test",
        "League match",
        "104.160.131.3",
        TargetCategory.LEAGUE_MATCH,
        ephemeral=True,
    )
    assert "104.160.131.3" in VareduraTextualApp._live_target_label(league)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("size", "card_columns", "control_columns"),
    [((55, 18), 1, 2), ((90, 26), 2, 2), ((145, 42), 3, 4)],
)
async def test_network_cards_reflow_for_any_terminal_size(
    size, card_columns, control_columns
):
    ui_shared.save_network_config(
        {
            "network_schema_version": 3,
            "target_onboarding_completed": True,
            "selected_target_ids": [
                "cloudflare_ipv4",
                "google_ipv4",
                "quad9_ipv4",
            ],
            "primary_target_id": "cloudflare_ipv4",
            "custom_targets": [],
            "league_auto_detect": False,
        }
    )
    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    app._start_network = lambda: None

    async with app.run_test(size=size) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        await wait_until(lambda: "network" in app._hydrated_tabs, pilot)
        await pilot.pause()

        pane = app.query_one("#network-pane", VerticalScroll)
        cards = app.query_one("#network-cards")
        controls = app.query_one("#network-controls")
        visible_targets = [card for card in app.query(TargetPingCard) if card.display]

        assert len(app.query("#network-targets-table")) == 0
        assert [card.target_id for card in visible_targets] == [
            "google_ipv4",
            "quad9_ipv4",
        ]
        assert cards.has_class(f"cols-{card_columns}") == (card_columns > 1)
        assert controls.has_class(f"cols-{control_columns}") == (control_columns > 1)
        if size[1] == 18:
            assert pane.max_scroll_y > 0


@pytest.mark.asyncio
async def test_diagnosis_renders_repair_actions_inside_responsive_grid(monkeypatch):
    import monitor.network_repairs as repairs

    monkeypatch.setattr(repairs, "list_repair_actions", lambda report, **kwargs: ())
    monkeypatch.setattr(repairs, "list_repair_guidance", lambda report: ())
    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    app._start_network = lambda: None

    async with app.run_test(size=(90, 26)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        await wait_until(lambda: "network" in app._hydrated_tabs, pilot)
        await pilot.pause()

        app._show_repair_actions(object())

        assert isinstance(app.query_one("#repair-actions"), Grid)


def test_callback_from_previous_network_run_is_discarded():
    app = VareduraTextualApp()
    app.network_running = True
    app._network_run_generation = 2
    app._accept_ping_result(object(), run_generation=1)
    assert app._target_latest == {}


def test_late_league_callback_cannot_reenable_disabled_detector():
    from monitor.league_detector import (
        LeagueDetectionResult,
        LeagueDetectorState,
        LeagueEndpoint,
    )

    app = VareduraTextualApp()
    app._network_run_generation = 1
    app._league_detector_generation = 2
    endpoint = LeagueEndpoint(
        "104.160.131.3",
        7001,
        10,
        "League of Legends.exe",
        1.0,
        "session",
        1,
    )
    result = LeagueDetectionResult(LeagueDetectorState.ACTIVE, endpoint=endpoint)

    # The preference check independently rejects a callback from the current
    # detector after the switch is turned off.
    app._network_config["league_auto_detect"] = False
    app._accept_league_detection(result, run_generation=1, detector_generation=2)
    assert app._league_target is None

    # The detector token independently rejects an old callback after a new
    # detector has already been started in the same network run.
    app._network_config["league_auto_detect"] = True
    app._accept_league_detection(result, run_generation=1, detector_generation=1)
    assert app._league_target is None


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
