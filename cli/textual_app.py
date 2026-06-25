"""Textual application shell for Varedura."""

from __future__ import annotations

import datetime
import threading
from collections import deque
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.text import Text
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Checkbox,
    DataTable,
    Digits,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    ProgressBar,
    RichLog,
    Select,
    Sparkline,
    Static,
    Switch,
    TabbedContent,
    TabPane,
)
from textual.widgets.option_list import Option

from cli.gamification import (
    achievement_by_id,
    check_achievements,
    compute_health_score,
    load_game_state,
    save_game_state,
    StreakTracker,
    update_records,
)
from cli.richlog import DailyLogWriter
from cli.textual_cameras import CAMERAS_CSS, CamerasMixin
from cli.ui_shared import (
    CLEANUP_GROUPS,
    CLEANUP_STEPS,
    QUICK_CLEANUP_KEYS,
    anatel_minimums,
    build_achievements_row,
    build_cleanup_status_panel,
    build_dashboard_status,
    build_ports_summary,
    build_records_panel,
    build_settings_status_table,
    build_tool_option,
    cleanup_label_key,
    format_duration,
    get_cleanup_steps,
    is_mcp_configured,
    load_network_config,
    load_recording_pref,
    run_cleanup_steps,
    save_cleanup_steps,
    save_network_config,
    save_recording_pref,
    selected_cleanup_keys,
    toggle_mcp_config,
)
from i18n import (
    get_language,
    get_supported_languages,
    set_language,
    t,
)
from mascot import FRAMES, MascotRenderer, STATES


def _cleanup_checkbox_id(step_key: str) -> str:
    return f"cleanup-{step_key.replace('_', '-')}"


class RichRenderable(Static):
    """Static widget that displays Rich renderables."""


class VareduraTextualApp(CamerasMixin, App[str | None]):
    """Main Textual TUI for Varedura."""

    CSS = """
    Screen {
        layout: vertical;
    }

    Header {
        dock: top;
    }

    Footer {
        dock: bottom;
    }

    TabbedContent {
        height: 1fr;
    }

    .pane {
        height: 1fr;
        padding: 1;
    }

    #dashboard-grid {
        height: 1fr;
    }

    #dashboard-left {
        width: 42%;
        min-width: 34;
        padding-right: 1;
    }

    #dashboard-right {
        width: 1fr;
    }

    #tool-menu {
        height: 1fr;
        border: solid $primary;
    }

    #dashboard-summary,
    #mascot-card,
    #achievements-card,
    #records-card,
    #cleanup-summary,
    #settings-status,
    #network-ports-summary {
        height: auto;
        margin-bottom: 1;
    }

    RichLog {
        height: 1fr;
        border: solid $primary;
        padding: 0 1;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        height: auto;
        margin-bottom: 1;
    }

    .form-row {
        height: auto;
        margin-bottom: 1;
    }

    .form-row > Label {
        width: 28;
        content-align: left middle;
    }

    .form-row > Input {
        width: 1fr;
    }

    .form-row > Button {
        margin-left: 1;
        width: auto;
    }

    .button-row {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
    }

    .button-row Button {
        margin-right: 1;
    }

    #cleanup-config {
        height: 1fr;
    }

    #cleanup-log {
        height: 10;
    }

    #cleanup-top {
        height: auto;
        margin-bottom: 1;
    }

    #cleanup-mascot {
        width: auto;
        height: auto;
    }

    #cleanup-reward {
        width: 1fr;
        height: auto;
        content-align: center middle;
    }

    #cleanup-reward .ping-digits {
        color: $success;
    }

    #cleanup-progress {
        height: 1;
        margin-bottom: 1;
    }

    DataTable {
        height: 1fr;
    }

    #network-controls {
        height: auto;
        margin-bottom: 1;
    }

    #network-controls Button {
        margin-right: 1;
    }

    #network-controls #network-status {
        content-align: left middle;
        width: 1fr;
    }

    #network-cards {
        height: 11;
        margin-bottom: 1;
    }

    .ping-card {
        width: 1fr;
        border: round $primary;
        padding: 0 1;
        margin-right: 1;
    }

    .card-title {
        text-style: bold;
        color: $accent;
        height: 1;
    }

    .ping-digits {
        height: 3;
        color: $success;
    }

    .card-unit,
    .card-stats {
        height: 1;
        color: $text-muted;
    }

    #gateway-spark,
    #external-spark {
        height: 3;
        margin-top: 1;
    }

    .ping-ok {
        color: $success;
    }

    .ping-warn {
        color: $warning;
    }

    .ping-bad {
        color: $error;
    }

    .ping-timeout {
        color: $error;
        text-style: bold;
    }
    """ + CAMERAS_CSS

    BINDINGS = [
        Binding("q", "quit", t("textual.bind_quit"), show=True),
        Binding("d", "toggle_dark", t("textual.bind_dark"), show=True),
        Binding("s", "show_settings", t("textual.bind_settings"), show=True),
        Binding("r", "rescan_ports", t("textual.bind_scan"), show=True),
        Binding("escape", "dashboard", t("textual.bind_dashboard"), show=True),
        Binding("delete", "cam_del_regiao", t("rtsp.bind_del"), show=False),
        Binding("l", "cam_log", t("rtsp.bind_log"), show=False),
    ]

    TOOL_IDS = ("network", "docker", "settings")

    def __init__(self) -> None:
        super().__init__()
        self.cleanup_running = False
        self.network_running = False
        self._network_stop = threading.Event()
        self._network_tick = 0
        self._net_local_stats = None
        self._net_external_stats = None
        self._net_pool: ThreadPoolExecutor | None = None
        self._net_scan_failed = False
        # Força um port scan no próximo tick do worker (tecla "r" / botão).
        self._force_scan = False
        # Último top de conexões/RAM por processo (atualiza nos ticks de scan),
        # usado para enriquecer a tabela de processos entre varreduras.
        self._last_top_connections: list = []
        # Poller leve sempre ativo do dashboard (memória/tráfego + ping rápido).
        self._dash_stop = threading.Event()
        self._dash_stats: dict = {}
        # Aba ativa rastreada por atributo (thread-safe) para o poller decidir,
        # sem tocar na árvore de widgets de fora da thread de UI.
        self._active_tab = "dashboard"
        # Timers periódicos (criados em on_mount, parados em on_unmount).
        self._dashboard_timer = None
        self._mascot_timer = None
        # Gamification state.
        self._game = load_game_state()
        self._streak = StreakTracker()
        self._score_hist: deque[float] = deque(maxlen=100)
        self._mascot = MascotRenderer()
        self._mascot_state = STATES.IDLE
        self._mascot_msg = ""
        self._mascot_frame = 0
        # Estado da aba Câmeras (RTSP), fundida via CamerasMixin.
        self._init_cameras_state()

    def compose(self) -> ComposeResult:
        self.title = "Varedura"
        self.sub_title = t("menu.subtitle")
        yield Header(show_clock=True)
        with TabbedContent(initial="dashboard", id="main-tabs"):
            with TabPane(t("textual.tab_dashboard"), id="dashboard"):
                yield from self._compose_dashboard()
            with TabPane(t("textual.tab_cleanup"), id="docker"):
                yield from self._compose_cleanup()
            with TabPane(t("textual.tab_network"), id="network"):
                yield from self._compose_network()
            with TabPane(t("rtsp.tab_cameras"), id="cameras"):
                yield from self._compose_cameras()
            with TabPane(t("textual.tab_settings"), id="settings"):
                yield from self._compose_settings()
        yield Footer()

    def _compose_dashboard(self) -> ComposeResult:
        with Horizontal(id="dashboard-grid", classes="pane"):
            with Vertical(id="dashboard-left"):
                yield RichRenderable(
                    self._mascot.render_static(STATES.WAVE, t("mascot.welcome")),
                    id="mascot-card",
                )
                yield RichRenderable(
                    build_dashboard_status(
                        load_recording_pref(), get_language(), self._network_status_snapshot()
                    ),
                    id="dashboard-summary",
                )
                yield OptionList(
                    Option(
                        build_tool_option(t("menu.option_1"), t("menu.desc_1"), "green"),
                        id="network",
                    ),
                    Option(
                        build_tool_option(t("menu.option_2"), t("menu.desc_2"), "cyan"),
                        id="docker",
                    ),
                    Option(
                        build_tool_option(t("menu.option_3"), t("menu.desc_3"), "yellow"),
                        id="scanner",
                    ),
                    Option(
                        build_tool_option(t("rtsp.tab_cameras"), t("rtsp.menu_desc"), "red"),
                        id="cameras",
                    ),
                    Option(Text(""), disabled=True),
                    Option(
                        build_tool_option(t("menu.option_settings"), t("menu.desc_settings"), "magenta"),
                        id="settings",
                    ),
                    id="tool-menu",
                )
            with Vertical(id="dashboard-right"):
                yield RichRenderable(build_achievements_row(self._game), id="achievements-card")
                yield RichRenderable(build_records_panel(self._game), id="records-card")
                yield RichLog(id="dashboard-log", highlight=True, markup=True, wrap=True)

    def _compose_cleanup(self) -> ComposeResult:
        steps = get_cleanup_steps()
        with Vertical(classes="pane"):
            # Scrollable configuration area.
            with VerticalScroll(id="cleanup-config"):
                yield Label(t("cleanup_prefs.title"), classes="section-title")
                with Horizontal(id="cleanup-top"):
                    yield RichRenderable(
                        self._mascot.render_static(STATES.IDLE, ""), id="cleanup-mascot"
                    )
                    with Vertical(id="cleanup-reward"):
                        yield Label(t("cleanup_prefs.freed_label"), classes="card-title")
                        yield Digits("0.0", id="cleanup-freed", classes="ping-digits")
                        yield Label("GB", classes="card-unit")
                with Horizontal(classes="button-row"):
                    yield Button(t("cleanup_prefs.preset_quick"), id="preset-quick")
                    yield Button(t("cleanup_prefs.preset_deep"), id="preset-deep")
                yield RichRenderable(build_cleanup_status_panel(steps), id="cleanup-summary")
                for group_key, icon, keys in CLEANUP_GROUPS:
                    yield Label(f"{icon} {t(group_key)}", classes="section-title")
                    for key in keys:
                        yield Checkbox(
                            t(cleanup_label_key(key)),
                            value=steps.get(key, False),
                            id=_cleanup_checkbox_id(key),
                        )
            # Fixed action + status + progress + log (always visible).
            with Horizontal(classes="button-row"):
                yield Button(t("textual.cleanup_run"), id="run-cleanup", variant="primary")
                yield Button(t("textual.cleanup_save"), id="save-cleanup")
            yield Label(t("textual.ready"), id="cleanup-status")
            yield ProgressBar(total=100, id="cleanup-progress")
            yield RichLog(id="cleanup-log", highlight=True, markup=True, wrap=True)

    def _compose_network(self) -> ComposeResult:
        with Vertical(classes="pane", id="network-pane"):
            with Horizontal(id="network-controls"):
                yield Button(t("textual.network_start"), id="network-start", variant="primary")
                yield Button(t("textual.network_stop"), id="network-stop", disabled=True)
                yield Button(t("textual.network_rescan"), id="network-rescan")
                yield Button(t("textual.network_export"), id="network-export")
                yield Label(t("textual.network_idle"), id="network-status")
            with Horizontal(id="network-cards"):
                with Vertical(classes="ping-card", id="health-card"):
                    yield Label(t("game.health_title"), classes="card-title")
                    yield Digits("--", id="health-digits", classes="ping-digits")
                    yield Label("", id="health-tier", classes="card-unit")
                    yield Sparkline([], id="health-spark", summary_function=max)
                    yield Label("", id="health-streak", classes="card-stats")
                with Vertical(classes="ping-card", id="gateway-card"):
                    yield Label(t("stalker.graph_gateway"), classes="card-title")
                    yield Digits("--", id="gateway-digits", classes="ping-digits")
                    yield Label("ms", classes="card-unit")
                    yield Sparkline([], id="gateway-spark", summary_function=max)
                    yield Label("", id="gateway-stats", classes="card-stats")
                with Vertical(classes="ping-card", id="external-card"):
                    yield Label(t("stalker.graph_external"), classes="card-title")
                    yield Digits("--", id="external-digits", classes="ping-digits")
                    yield Label("ms", classes="card-unit")
                    yield Sparkline([], id="external-spark", summary_function=max)
                    yield Label("", id="external-stats", classes="card-stats")
            with TabbedContent(initial="net-speed-tab", id="network-subtabs"):
                with TabPane(t("textual.network_speed"), id="net-speed-tab"):
                    yield DataTable(id="network-speed-table")
                with TabPane(t("textual.network_ports"), id="net-ports-tab"):
                    with Vertical():
                        yield Label(t("ports.waiting"), id="network-ports-summary")
                        yield DataTable(id="network-ports-table")
                with TabPane(t("textual.network_processes"), id="net-procs-tab"):
                    yield DataTable(id="network-procs-table")
                with TabPane(t("textual.network_events"), id="net-log-tab"):
                    yield RichLog(id="network-log", highlight=True, markup=True, wrap=True)

    def _compose_settings(self) -> ComposeResult:
        lang_names = {"pt": t("lang.pt"), "en": t("lang.en")}
        language_options = [(lang_names.get(code, code), code) for code in get_supported_languages()]
        with VerticalScroll(classes="pane"):
            yield Label(t("settings.title"), classes="section-title")
            yield RichRenderable(
                build_settings_status_table(load_recording_pref(), get_language()),
                id="settings-status",
            )
            with Horizontal(classes="form-row"):
                yield Label(t("settings.option_rec"))
                yield Switch(value=load_recording_pref(), id="recording-switch")
            with Horizontal(classes="form-row"):
                yield Label(t("settings.option_lang"))
                yield Select(language_options, value=get_language(), id="language-select")

            net = load_network_config()
            yield Label(t("settings.network_title"), classes="section-title")
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_gateway"))
                yield Input(value=str(net["gateway_ip"]), id="net-gateway")
                yield Button(t("settings.net_detect"), id="net-detect-gateway")
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_external"))
                yield Input(value=str(net["external_host"]), id="net-external")
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_threshold"))
                yield Input(value=str(net["lag_threshold_ms"]), id="net-threshold", type="integer")
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_contracted_down"))
                yield Input(value=str(net["contracted_down"]), id="net-down", type="number")
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_contracted_up"))
                yield Input(value=str(net["contracted_up"]), id="net-up", type="number")

            with Horizontal(classes="button-row"):
                yield Button(t("textual.settings_save"), id="save-settings", variant="primary")
                yield Button(t("mcp.option"), id="toggle-mcp")
            yield Label(
                t("mcp.status_on") if is_mcp_configured() else t("mcp.status_off"),
                id="mcp-status",
            )

    def on_mount(self) -> None:
        self._setup_network_tables()
        self._cameras_on_mount()
        self._init_network_config()
        self.query_one("#tool-menu", OptionList).focus()
        self._write_dashboard_log(t("textual.ready"))
        self._dashboard_timer = self.set_interval(2.0, self._refresh_dashboard_status)
        self._mascot_timer = self.set_interval(0.5, self._animate_mascot)
        # Poller leve sempre ativo: mantém o dashboard vivo (memória/tráfego e
        # ping do gateway) mesmo sem o monitor de Rede estar ligado.
        self._run_dashboard_poller()

    def _network_status_snapshot(self) -> dict:
        """Cheap live snapshot of the network monitor for the dashboard."""
        snapshot: dict = {"running": self.network_running}
        try:
            import monitor.stalker as stalker_mod

            snapshot["gateway_ip"] = stalker_mod.config.gateway_ip
            snapshot["lag_threshold_ms"] = stalker_mod.config.lag_threshold_ms
            if stalker_mod.local_stats.history:
                snapshot["local_ms"] = stalker_mod.local_stats.history[-1]
            if stalker_mod.external_stats.history:
                snapshot["ext_ms"] = stalker_mod.external_stats.history[-1]
        except Exception:
            pass
        return snapshot

    def _refresh_dashboard_status(self) -> None:
        """Update the dashboard status + records panels with live data."""
        try:
            self.query_one("#dashboard-summary", RichRenderable).update(
                build_dashboard_status(
                    load_recording_pref(),
                    get_language(),
                    self._network_status_snapshot(),
                    self._dash_stats,
                )
            )
            self.query_one("#records-card", RichRenderable).update(
                build_records_panel(self._game)
            )
        except Exception:
            pass

    @work(thread=True, exclusive=False)
    def _run_dashboard_poller(self) -> None:
        """Always-on lightweight poll: system memory/traffic + a quick gateway
        ping (only when the heavy network monitor is not already running)."""
        import monitor.stalker as stalker_mod
        from monitor.port_scanner import get_system_network_stats

        while not self._dash_stop.is_set():
            try:
                self._dash_stats = get_system_network_stats()
            except Exception:
                self._dash_stats = {}
            # Ping the gateway only when the dashboard is the visible tab and the
            # heavy monitor isn't already collecting samples — no point spawning
            # ping subprocesses for a panel nobody is looking at.
            if self._active_tab == "dashboard" and not self.network_running:
                try:
                    gateway = stalker_mod.config.gateway_ip
                    if gateway:
                        stalker_mod.local_stats.add(stalker_mod.run_ping(gateway))
                except Exception:
                    pass
            self._dash_stop.wait(timeout=3.0)

    def _animate_mascot(self) -> None:
        """Cycle the mascot sprite frames; only while the dashboard is visible."""
        try:
            if self.query_one("#main-tabs", TabbedContent).active != "dashboard":
                return
            frames = FRAMES.get(self._mascot_state) or FRAMES[STATES.IDLE]
            path = frames[self._mascot_frame % len(frames)]
            self._mascot_frame += 1
            self.query_one("#mascot-card", RichRenderable).update(
                self._mascot.render_static_from_path(path, self._mascot_msg, self._mascot_state)
            )
        except Exception:
            pass

    def _update_mascot_state(self, score: int, testing: bool) -> None:
        if not self.network_running:
            self._mascot_state, self._mascot_msg = STATES.IDLE, t("mascot.welcome")
        elif testing:
            self._mascot_state, self._mascot_msg = STATES.SCANNING, t("mascot.scanning")
        elif score < 35:
            self._mascot_state, self._mascot_msg = STATES.ERROR, ""
        elif score < 70:
            self._mascot_state, self._mascot_msg = STATES.WORKING, ""
        else:
            self._mascot_state, self._mascot_msg = STATES.IDLE, ""

    def _init_network_config(self) -> None:
        """Resolve the network config (autodetect gateway) and apply it."""
        cfg = load_network_config()
        if not str(cfg.get("gateway_ip", "")).strip():
            from monitor.netinfo import detect_default_gateway

            detected = detect_default_gateway()
            if detected:
                cfg["gateway_ip"] = detected
                save_network_config(cfg)
                self._write_dashboard_log(t("settings.net_gateway_detected", ip=detected))
                try:
                    self.query_one("#net-gateway", Input).value = detected
                except Exception:
                    pass
        self._apply_network_config(cfg)

    def _apply_network_config(self, cfg: dict) -> None:
        """Push the config dict onto the live stalker/speed singletons."""
        try:
            import monitor.stalker as stalker_mod
            from monitor.speed_tester import speed_config

            if str(cfg.get("gateway_ip", "")).strip():
                stalker_mod.config.gateway_ip = str(cfg["gateway_ip"]).strip()
            stalker_mod.config.external_ip = str(cfg["external_host"]).strip()
            stalker_mod.config.lag_threshold_ms = int(cfg["lag_threshold_ms"])
            speed_config.velocidade_contratada_down = float(cfg["contracted_down"])
            speed_config.velocidade_contratada_up = float(cfg["contracted_up"])
        except Exception:
            pass

    def action_show_settings(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "settings"

    def action_dashboard(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "dashboard"

    def action_rescan_ports(self) -> None:
        """Jump to the network ports view and force a fresh scan next tick."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        if tabs.active != "network":
            tabs.active = "network"
        try:
            self.query_one("#network-subtabs", TabbedContent).active = "net-ports-tab"
        except Exception:
            pass
        # Start the monitor first if paused (it resets the flag), then request a
        # scan on the very next tick.
        if not self.network_running:
            self._start_network()
        self._force_scan = True
        self.notify(t("textual.network_rescan"))

    @on(OptionList.OptionSelected, "#tool-menu")
    def on_tool_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = str(event.option_id or "")
        # The legacy "Port Scanner" menu entry now opens the live ports view
        # inside the Network tab (the standalone scanner tab was merged in).
        if option_id == "scanner":
            self.query_one("#main-tabs", TabbedContent).active = "network"
            try:
                self.query_one("#network-subtabs", TabbedContent).active = "net-ports-tab"
            except Exception:
                pass
            return
        if option_id in {"network", "docker", "cameras", "settings"}:
            self.query_one("#main-tabs", TabbedContent).active = option_id

    @on(TabbedContent.TabActivated, "#main-tabs")
    def on_main_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._active_tab = event.pane.id or self._active_tab
        if event.pane.id == "network" and not self.network_running:
            self._start_network()
        elif event.pane.id == "cameras":
            self._maybe_render_cameras()

    def on_data_table_row_selected(self, event) -> None:
        self._cameras_on_row_selected(event)

    def on_descendant_focus(self, event) -> None:
        self._cameras_on_focus(event)

    def on_worker_state_changed(self, event) -> None:
        self._cameras_on_worker_state(event)

    def on_resize(self, event) -> None:
        self._cameras_on_resize(event.size.width)

    def on_unmount(self) -> None:
        # Sinaliza a parada do worker de rede (que encerra o ThreadPoolExecutor
        # no seu finally) e para os timers periódicos para que não disparem
        # durante o teardown da aplicação.
        self._network_stop.set()
        self._dash_stop.set()
        self._cameras_on_unmount()
        for timer in (self._dashboard_timer, self._mascot_timer):
            if timer is not None:
                timer.stop()

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "save-settings":
            self._save_settings()
        elif button_id == "toggle-mcp":
            self._toggle_mcp()
        elif button_id == "save-cleanup":
            self._save_cleanup_preferences()
        elif button_id == "run-cleanup":
            self._start_cleanup()
        elif button_id == "network-start":
            self._start_network()
        elif button_id == "network-stop":
            self._stop_network()
        elif button_id == "network-rescan":
            self.action_rescan_ports()
        elif button_id == "network-export":
            self._export_network_report()
        elif button_id == "net-detect-gateway":
            self._detect_gateway()
        elif button_id == "preset-quick":
            self._apply_cleanup_preset(QUICK_CLEANUP_KEYS)
        elif button_id == "preset-deep":
            self._apply_cleanup_preset([key for key, _l, _d in CLEANUP_STEPS])
        else:
            # Camera tab buttons (network cards, scans, credentials, etc.).
            self._cameras_handle_button(button_id or "")

    def _apply_cleanup_preset(self, enabled_keys: list[str]) -> None:
        wanted = set(enabled_keys)
        for key, _label_key, _default in CLEANUP_STEPS:
            self.query_one(f"#{_cleanup_checkbox_id(key)}", Checkbox).value = key in wanted
        self._refresh_cleanup_summary()

    def _refresh_cleanup_summary(self) -> None:
        try:
            self.query_one("#cleanup-summary", RichRenderable).update(
                build_cleanup_status_panel(self._cleanup_form_steps())
            )
        except Exception:
            pass

    @on(Checkbox.Changed)
    def on_cleanup_checkbox_changed(self, event: Checkbox.Changed) -> None:
        """Keep the cleanup summary in sync the moment a step is toggled."""
        if (event.checkbox.id or "").startswith("cleanup-"):
            self._refresh_cleanup_summary()

    @on(Switch.Changed, "#recording-switch")
    def on_recording_switch_changed(self, event: Switch.Changed) -> None:
        self._refresh_live_settings_status()

    @on(Select.Changed, "#language-select")
    def on_language_select_changed(self, event: Select.Changed) -> None:
        self._refresh_live_settings_status()

    def _refresh_live_settings_status(self) -> None:
        """Reflect the current (unsaved) settings form in the status panel."""
        try:
            recording = bool(self.query_one("#recording-switch", Switch).value)
            lang = self.query_one("#language-select", Select).value
            if not isinstance(lang, str):
                lang = get_language()
            self.query_one("#settings-status", RichRenderable).update(
                build_settings_status_table(recording, lang)
            )
        except Exception:
            pass

    def _detect_gateway(self) -> None:
        from monitor.netinfo import detect_default_gateway

        detected = detect_default_gateway()
        if detected:
            self.query_one("#net-gateway", Input).value = detected
            self.notify(t("settings.net_gateway_detected", ip=detected))
        else:
            self.notify(t("settings.net_gateway_not_found"), severity="warning")

    def _save_settings(self) -> None:
        recording = self.query_one("#recording-switch", Switch).value
        selected_language = self.query_one("#language-select", Select).value
        save_recording_pref(bool(recording))
        if isinstance(selected_language, str):
            set_language(selected_language)
        self._save_network_settings()
        self._refresh_status_renderables()
        self.notify(t("textual.settings_saved"))
        self._write_dashboard_log(t("textual.settings_saved"))

    def _save_network_settings(self) -> None:
        """Read the network form, validate, persist and apply it."""
        cfg = load_network_config()
        cfg["gateway_ip"] = self.query_one("#net-gateway", Input).value.strip()
        cfg["external_host"] = self.query_one("#net-external", Input).value.strip()
        try:
            cfg["lag_threshold_ms"] = int(self.query_one("#net-threshold", Input).value or 0)
            cfg["contracted_down"] = float(self.query_one("#net-down", Input).value or 0)
            cfg["contracted_up"] = float(self.query_one("#net-up", Input).value or 0)
        except ValueError:
            self.notify(t("settings.net_invalid"), severity="error")
            return
        save_network_config(cfg)
        self._apply_network_config(cfg)

    def _toggle_mcp(self) -> None:
        for style, message in toggle_mcp_config():
            self._write_dashboard_log(f"[{style}]{message}[/]")
        self.query_one("#mcp-status", Label).update(
            t("mcp.status_on") if is_mcp_configured() else t("mcp.status_off")
        )
        self._refresh_status_renderables()

    def _cleanup_form_steps(self) -> dict[str, bool]:
        steps: dict[str, bool] = {}
        for key, _label_key, _default in CLEANUP_STEPS:
            steps[key] = bool(self.query_one(f"#{_cleanup_checkbox_id(key)}", Checkbox).value)
        return steps

    def _save_cleanup_preferences(self) -> dict[str, bool]:
        steps = self._cleanup_form_steps()
        save_cleanup_steps(steps)
        self._refresh_status_renderables()
        self.query_one("#cleanup-status", Label).update(t("cleanup_prefs.saved"))
        self.notify(t("cleanup_prefs.saved"))
        return steps

    def _start_cleanup(self) -> None:
        if self.cleanup_running:
            return
        steps = self._save_cleanup_preferences()
        enabled = selected_cleanup_keys(steps)
        if not enabled:
            message = t("menu.no_steps_enabled")
            self.query_one("#cleanup-status", Label).update(message)
            self.notify(message, severity="warning")
            return
        self._run_cleanup_worker(enabled)

    @work(thread=True, exclusive=True)
    def _run_cleanup_worker(self, step_keys: list[str]) -> None:
        self.call_from_thread(self._set_cleanup_running, True)

        def ui_write(line: str) -> None:
            self.call_from_thread(self._write_cleanup_log, line)

        writer = DailyLogWriter(ui_write=ui_write)
        rich_console = Console(file=writer, width=100)

        def progress(completed: int, total: int, label: str) -> None:
            self.call_from_thread(self._update_cleanup_progress, completed, total, label)

        try:
            success, failures, freed = run_cleanup_steps(step_keys, rich_console, progress)
            self.call_from_thread(self._finish_cleanup, success, failures, freed)
        except Exception as exc:
            self.call_from_thread(self._finish_cleanup, False, [str(exc)], 0.0)
        finally:
            writer.close()
            self.call_from_thread(self._set_cleanup_running, False)

    def _set_cleanup_running(self, running: bool) -> None:
        self.cleanup_running = running
        self.query_one("#run-cleanup", Button).disabled = running
        self.query_one("#save-cleanup", Button).disabled = running
        if running:
            self.query_one("#cleanup-mascot", RichRenderable).update(
                self._mascot.render_static(STATES.WORKING, t("mascot.scanning"))
            )

    def _write_cleanup_log(self, line: str) -> None:
        self.query_one("#cleanup-log", RichLog).write(line)

    def _update_cleanup_progress(self, completed: int, total: int, label: str) -> None:
        bar = self.query_one("#cleanup-progress", ProgressBar)
        bar.total = max(total, 1)
        bar.progress = min(completed, max(total, 1))
        self.query_one("#cleanup-status", Label).update(label)

    def _finish_cleanup(self, success: bool, failures: list[str], freed: float = 0.0) -> None:
        if success:
            message = t("textual.cleanup_success")
            severity = "information"
        else:
            detail = ", ".join(failures) if failures else t("menu.error_during_cleanup", error="")
            message = t("menu.error_during_cleanup", error=detail)
            severity = "error"
        self.query_one("#cleanup-status", Label).update(message)
        self._write_cleanup_log(message)
        self.notify(message, severity=severity)

        # Gamified reward: show freed space + celebrate via the mascot.
        self.query_one("#cleanup-freed", Digits).update(f"{freed:.1f}")
        self.query_one("#cleanup-mascot", RichRenderable).update(
            self._mascot.render_static(
                STATES.SUCCESS if success else STATES.ERROR,
                t("cleanup_prefs.freed_msg", gb=f"{freed:.1f}") if success else "",
            )
        )
        if success:
            update_records(self._game, space_freed_gb=freed, cleanups=1)
            unlocked = check_achievements(self._game)
            if unlocked:
                self._unlock_achievements(unlocked)
            else:
                save_game_state(self._game)
            self._refresh_dashboard_status()

    def _setup_network_tables(self) -> None:
        speed_table = self.query_one("#network-speed-table", DataTable)
        speed_table.cursor_type = "row"
        speed_table.add_columns(
            t("stalker.speed_provider"),
            t("stalker.speed_download"),
            t("stalker.speed_upload"),
            t("stalker.speed_ping"),
        )

        ports_table = self.query_one("#network-ports-table", DataTable)
        ports_table.cursor_type = "row"
        ports_table.zebra_stripes = True
        ports_table.add_columns(
            t("ports.col_service"),
            t("ports.col_app"),
            t("ports.col_explain"),
            t("ports.col_exposure"),
            t("ports.col_port"),
        )

        procs_table = self.query_one("#network-procs-table", DataTable)
        procs_table.cursor_type = "row"
        procs_table.zebra_stripes = True
        procs_table.add_columns(
            t("ports.col_app"),
            t("ports.col_conns"),
            t("ports.col_ram"),
            t("stalker.pid_col"),
        )

    def _friendly_process(self, name: str) -> Text:
        """Translate the scanner's raw process labels for display."""
        if not name or name == "N/A":
            return Text(t("scanner.unknown"), style="dim")
        if name == "Acesso Negado":
            return Text(t("scanner.access_denied"), style="dim")
        return Text(name, style="green")

    def _render_ports_table(self, scan_state) -> None:
        """Render the lay-friendly ports view: service, app, what-it-does,
        visibility chip and the raw port/proto. Exposed ports float to the top."""
        from monitor.port_catalog import classify_exposure, describe_port, is_exposed

        table = self.query_one("#network-ports-table", DataTable)
        table.clear()
        ports = list(scan_state.listening_tcp) + list(scan_state.listening_udp)

        def sort_key(p):
            label_key, _ = describe_port(p.porta, p.protocolo)
            unknown = label_key in ("port.unknown", "port.ephemeral")
            return (not is_exposed(p.endereco), unknown, p.porta)

        ports.sort(key=sort_key)
        for p in ports[:50]:
            label_key, expl_key = describe_port(p.porta, p.protocolo)
            chip_key, color = classify_exposure(p.endereco)
            table.add_row(
                Text(t(label_key, porta=p.porta), style="bold"),
                self._friendly_process(p.processo),
                Text(t(expl_key), style="dim"),
                Text(t(chip_key), style=color),
                Text(f"{p.porta}/{p.protocolo}", style="dim"),
            )
        self.query_one("#network-ports-summary", Label).update(build_ports_summary(scan_state))

    def _render_procs_table(self, procs) -> None:
        """Render the merged processes view: active connections (live every tick)
        enriched with RAM from the latest port scan, matched by process name."""
        table = self.query_one("#network-procs-table", DataTable)
        table.clear()
        ram_by_name = {
            pc.nome: pc.memoria_mb for pc in self._last_top_connections if pc.memoria_mb > 0
        }
        for pid, name, raw in procs:
            conns = raw // (1024 * 1024)
            ram = ram_by_name.get(name)
            ram_str = f"{ram:.0f} MB" if ram else "—"
            table.add_row(self._friendly_process(name), str(conns), ram_str, str(pid))

    # ------------------------------------------------------------------ #
    # Network Stalker tab                                                 #
    # ------------------------------------------------------------------ #
    def _start_network(self) -> None:
        if self.network_running:
            return
        from monitor.stalker import PingStats

        self._net_local_stats = PingStats()
        self._net_external_stats = PingStats()
        self._net_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="net")
        self._network_tick = 0
        self._force_scan = False
        self._last_top_connections = []
        self._network_stop.clear()
        self._set_network_running(True)
        self._run_network_worker()

    def _stop_network(self) -> None:
        self._network_stop.set()
        self._set_network_running(False)

    def _set_network_running(self, running: bool) -> None:
        self.network_running = running
        self.query_one("#network-start", Button).disabled = running
        self.query_one("#network-stop", Button).disabled = not running
        self.query_one("#network-status", Label).update(
            t("textual.network_monitoring") if running else t("textual.network_idle")
        )

    @staticmethod
    def _ping_status_class(ms, threshold: int) -> str:
        if ms is None:
            return "ping-timeout"
        if ms > threshold:
            return "ping-bad"
        if ms > threshold * 0.7:
            return "ping-warn"
        return "ping-ok"

    @work(thread=True, exclusive=False)
    def _run_network_worker(self) -> None:
        import monitor.stalker as stalker_mod
        from monitor.stalker import analyze_lag_source, config as stalker_config
        from monitor.port_scanner import run_full_scan
        from monitor.speed_tester import (
            get_speed_tester,
            start_continuous_testing,
            stop_continuous_testing,
        )

        try:
            start_continuous_testing()
        except Exception as exc:
            self.call_from_thread(
                self._network_log, f"[red]{t('stalker.speed_start_error', error=exc)}[/]"
            )
        self.call_from_thread(self._network_log, f"[dim]{t('stalker.monitoring_started')}[/]")

        pool = self._net_pool
        try:
            while not self._network_stop.is_set():
                # Fan-out paralelo das chamadas bloqueantes (sob free-threading,
                # ping/psutil rodam de fato em paralelo: tick = max(...) e não soma).
                f_local = pool.submit(stalker_mod.run_ping, stalker_config.gateway_ip)
                f_ext = pool.submit(stalker_mod.run_ping, stalker_config.external_ip)
                f_procs = pool.submit(stalker_mod.get_top_network_hogs)
                self._network_tick += 1
                do_scan = (
                    self._network_tick % stalker_config.port_scan_interval == 0
                    or self._force_scan
                )
                self._force_scan = False
                f_scan = pool.submit(run_full_scan) if do_scan else None

                local_ms = self._future_result(f_local)
                ext_ms = self._future_result(f_ext)
                procs = self._future_result(f_procs) or []

                scan_state = None
                if f_scan is not None:
                    try:
                        scan_state = f_scan.result()
                        self._net_scan_failed = False
                    except Exception as exc:
                        # Surface the failure once (not every cycle) so a broken
                        # scan does not look like a silently empty ports table.
                        if not self._net_scan_failed:
                            self._net_scan_failed = True
                            self.call_from_thread(
                                self._network_log,
                                f"[yellow]{t('stalker.port_scan_error', error=exc)}[/]",
                            )

                # Agregação single-threaded (evita corrida no deque do PingStats).
                self._net_local_stats.add(local_ms)
                self._net_external_stats.add(ext_ms)
                stalker_mod.local_stats.add(local_ms)
                stalker_mod.external_stats.add(ext_ms)
                now = datetime.datetime.now()
                stalker_mod.record_ping_sample(now, local_ms, ext_ms)

                try:
                    speed_snapshot = get_speed_tester().get_stats_snapshot()
                except Exception:
                    speed_snapshot = {}

                # Gamification: health score (read-only on the stats), streak.
                threshold = stalker_config.lag_threshold_ms
                compliant, best_down = self._speed_compliance(speed_snapshot)
                score, tier, color = compute_health_score(
                    list(self._net_local_stats.history),
                    list(self._net_external_stats.history),
                    threshold,
                    compliant,
                )
                streak_ms = ext_ms if ext_ms is not None else local_ms
                ok = streak_ms is not None and streak_ms <= threshold
                streak_s = self._streak.update(ok, stalker_config.interval)
                health = {
                    "score": score,
                    "tier": tier,
                    "color": color,
                    "streak_s": streak_s,
                    "ping": ext_ms,
                    "best_down": best_down,
                    "compliant": compliant,
                    "monitor_s": stalker_config.interval,
                }

                log_lines = self._build_network_alerts(
                    local_ms,
                    ext_ms,
                    threshold,
                    procs,
                    analyze_lag_source,
                )

                self.call_from_thread(
                    self._render_network_tick,
                    local_ms,
                    ext_ms,
                    procs,
                    scan_state,
                    speed_snapshot,
                    log_lines,
                    health,
                )
                self._network_stop.wait(timeout=stalker_config.interval)
        finally:
            try:
                stop_continuous_testing()
            except Exception:
                pass
            if pool is not None:
                pool.shutdown(wait=False)
            self.call_from_thread(self._set_network_running, False)

    @staticmethod
    def _future_result(future):
        try:
            return future.result()
        except Exception:
            return None

    def _build_network_alerts(
        self, local_ms, ext_ms, threshold: int, procs: list, analyze_lag_source
    ) -> list[str]:
        lines: list[str] = []
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        alert_triggered = False

        if local_ms and local_ms > threshold:
            lines.append(f"[{stamp}] [bold red]{t('stalker.alert_local_lag', ms=local_ms)}[/]")
            alert_triggered = True
        elif ext_ms and ext_ms > threshold:
            lines.append(f"[{stamp}] [bold orange1]{t('stalker.alert_ext_lag', ms=ext_ms)}[/]")
            alert_triggered = True
        elif local_ms is None or ext_ms is None:
            lines.append(f"[{stamp}] [bold white on red]{t('stalker.alert_packet_loss')}[/]")
            alert_triggered = True

        if alert_triggered:
            suspeito, explicacao = analyze_lag_source(local_ms, ext_ms, threshold, procs)
            lines.append(f"   ↳ [bold yellow]{t('stalker.diagnostic')}[/] {suspeito}")
            lines.append(f"   ↳ [dim]{explicacao}[/]")
            if procs and not suspeito.startswith("🔌"):
                top_hog = procs[0]
                conns = top_hog[2] // (1024 * 1024)
                hog_name = top_hog[1] if top_hog[1] else t("stalker.unknown_process")
                lines.append(
                    f"   ↳ [dim]{t('stalker.top_connections_log', name=hog_name, conns=conns)}[/]"
                )
        return lines

    def _render_network_tick(
        self, local_ms, ext_ms, procs, scan_state, speed_snapshot, log_lines, health=None
    ) -> None:
        # The event log is cheap (append-only, fixed height) -> always flush it.
        log = self.query_one("#network-log", RichLog)
        for line in log_lines:
            log.write(line)

        # Record gamification metrics regardless of the active tab (runs on the
        # UI thread, so GameState is mutated from a single thread).
        if health is not None:
            self._record_and_check(health)
            self._score_hist.append(float(health.get("score", 0)))
            self._update_mascot_state(
                int(health.get("score", 0)), bool((speed_snapshot or {}).get("is_testing"))
            )

        # Cache the latest top-connections (conn count + RAM) regardless of the
        # active tab so the processes table can be enriched between scan ticks.
        if scan_state is not None:
            self._last_top_connections = list(scan_state.top_connections)

        # Skip the heavier visual updates when the network tab is not in front;
        # rebuilding tables every tick on a background tab triggers layout passes
        # that make the whole screen flicker.
        if self.query_one("#main-tabs", TabbedContent).active != "network":
            return

        threshold = 100
        try:
            from monitor.stalker import config as stalker_config

            threshold = stalker_config.lag_threshold_ms
        except Exception:
            pass

        if health is not None:
            self._render_health_card(health)
        self._render_ping_card("gateway", local_ms, self._net_local_stats, threshold)
        self._render_ping_card("external", ext_ms, self._net_external_stats, threshold)

        if scan_state is not None:
            self._render_ports_table(scan_state)

        self._render_procs_table(procs)
        self._render_speed_table(speed_snapshot or {})

    @staticmethod
    def _apply_status_class(widgets, cls: str) -> None:
        """Swap the ping-status colour class on a set of widgets."""
        for widget in widgets:
            widget.remove_class("ping-ok", "ping-warn", "ping-bad", "ping-timeout")
            widget.add_class(cls)

    def _render_ping_card(self, prefix: str, ms, stats, threshold: int) -> None:
        digits = self.query_one(f"#{prefix}-digits", Digits)
        spark = self.query_one(f"#{prefix}-spark", Sparkline)
        digits.update("--" if ms is None else f"{ms:.0f}")
        spark.data = [v if v is not None else 0.0 for v in stats.history]

        has_data = stats.min_ms is not None
        self.query_one(f"#{prefix}-stats", Label).update(
            t(
                "textual.network_card_stats",
                min=f"{stats.min_ms:.0f}" if has_data else "--",
                avg=f"{stats.avg_ms:.0f}" if has_data else "--",
                max=f"{stats.max_ms:.0f}" if has_data else "--",
                threshold=threshold,
            )
        )

        self._apply_status_class((digits, spark), self._ping_status_class(ms, threshold))

    @staticmethod
    def _speed_compliance(snapshot: dict) -> tuple[bool | None, float]:
        """Return (ANATEL-compliant?, best download Mbps) from a speed snapshot."""
        results = (snapshot or {}).get("results_by_provider", {})
        if not results:
            return None, 0.0
        min_down, min_up = anatel_minimums()
        best_down = 0.0
        compliant = False
        for result in results.values():
            try:
                down = float(result.download_mbps)
                up = float(result.upload_mbps)
            except (ValueError, TypeError, AttributeError):
                continue
            best_down = max(best_down, down)
            if down >= min_down and up >= min_up:
                compliant = True
        return compliant, best_down

    def _render_health_card(self, health: dict) -> None:
        digits = self.query_one("#health-digits", Digits)
        score = int(health.get("score", 0))
        tier = str(health.get("tier", "—"))
        color = str(health.get("color", "dim"))
        digits.update(str(score))
        self.query_one("#health-spark", Sparkline).data = list(self._score_hist) or [0.0]
        self.query_one("#health-tier", Label).update(Text(f"{tier}", style=f"bold {color}"))

        streak_s = float(health.get("streak_s", 0.0))
        self.query_one("#health-streak", Label).update(
            t("game.streak", time=format_duration(streak_s))
        )

        cls = "ping-ok" if score >= 75 else "ping-warn" if score >= 45 else "ping-bad"
        self._apply_status_class((digits, self.query_one("#health-spark", Sparkline)), cls)

    def _record_and_check(self, health: dict) -> None:
        """Update persisted records and surface any newly unlocked achievements."""
        update_records(
            self._game,
            ping=health.get("ping"),
            download=health.get("best_down"),
            streak_s=health.get("streak_s"),
            pings=1,
            monitor_s=health.get("monitor_s", 0.0),
            anatel=bool(health.get("compliant")),
        )
        unlocked = check_achievements(self._game)
        if unlocked:
            self._unlock_achievements(unlocked)
        elif self._network_tick % 30 == 0:
            save_game_state(self._game)

    def _unlock_achievements(self, ids: list[str]) -> None:
        for ach_id in ids:
            ach = achievement_by_id(ach_id)
            if ach is None:
                continue
            self.notify(
                f"{ach.emoji} {t(ach.name_key)} — {t(ach.desc_key)}",
                title=t("game.unlocked"),
            )
            self._write_dashboard_log(
                f"[bold yellow]{ach.emoji} {t('game.unlocked')}:[/] {t(ach.name_key)}"
            )
        save_game_state(self._game)
        self._refresh_achievements()

    def _refresh_achievements(self) -> None:
        """Hook updated in the dashboard phase; safe no-op until then."""
        try:
            from cli.ui_shared import build_achievements_row

            self.query_one("#achievements-card", RichRenderable).update(
                build_achievements_row(self._game)
            )
        except Exception:
            pass

    def _render_speed_table(self, snapshot: dict) -> None:
        table = self.query_one("#network-speed-table", DataTable)
        table.clear()

        # ANATEL compliance reference: at least `percentual_minimo`% of the
        # contracted speed (Resolução 574/2011 mensal mínimo de 80%).
        min_down, min_up = anatel_minimums()

        results = snapshot.get("results_by_provider", {})
        for provider, result in results.items():
            try:
                down_mbps = float(result.download_mbps)
                up_mbps = float(result.upload_mbps)
                ping = f"{float(result.ping_ms):.0f} ms"
            except (ValueError, TypeError, AttributeError):
                continue
            down = Text(
                f"{down_mbps:.0f} Mbps",
                style="green" if down_mbps >= min_down else "bold red",
            )
            up = Text(
                f"{up_mbps:.0f} Mbps",
                style="green" if up_mbps >= min_up else "bold red",
            )
            table.add_row(str(provider)[:14], down, up, ping)

        if snapshot.get("is_testing"):
            current = str(snapshot.get("current_provider", "") or "...")[:14]
            phase = snapshot.get("progress_phase", "")
            progress = snapshot.get("progress_mbps", 0.0) or 0.0
            if phase == "download" and progress > 0:
                table.add_row(current, f"{progress:.0f} Mbps", t("stalker.speed_downloading"), "...")
            elif phase == "upload":
                table.add_row(current, "ok", t("stalker.speed_uploading"), "...")
            else:
                table.add_row(current, t("stalker.speed_connecting"), "...", "...")
        elif not results:
            error = snapshot.get("last_error")
            if error:
                table.add_row("-", Text(str(error)[:24], style="red"), "-", "-")
            else:
                table.add_row("...", t("stalker.speed_waiting"), "...", "...")

    def _export_network_report(self) -> None:
        from monitor.stalker import export_combined_report

        msg = export_combined_report(full_history=False)
        self._network_log(msg)
        self.notify(msg)
        self.set_timer(3.0, self._poll_export_status)

    def _poll_export_status(self) -> None:
        from monitor.stalker import get_export_status

        status = get_export_status()
        if status:
            self._network_log(status)
            self.notify(status)

    def _network_log(self, message) -> None:
        self.query_one("#network-log", RichLog).write(message)

    def _refresh_status_renderables(self) -> None:
        recording = load_recording_pref()
        language = get_language()
        self._refresh_dashboard_status()
        self.query_one("#settings-status", RichRenderable).update(
            build_settings_status_table(recording, language)
        )
        self.query_one("#cleanup-summary", RichRenderable).update(
            build_cleanup_status_panel(get_cleanup_steps())
        )

    def _write_dashboard_log(self, message) -> None:
        self.query_one("#dashboard-log", RichLog).write(message)


def run_textual_app() -> None:
    """Run the Textual app."""
    # Pre-warm the speed-test backend while stdout still has a valid file
    # descriptor. Textual replaces sys.stdout during run(), and speedtest-cli
    # wraps sys.stdout.fileno() at import time -- importing it later, from
    # inside the running app, raises "negative file descriptor".
    try:
        from monitor.speed_tester import get_speed_tester

        get_speed_tester()
    except Exception:
        pass
    VareduraTextualApp().run()
