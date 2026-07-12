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
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
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
from mascot.frames import FRAMES, STATES


def _cleanup_checkbox_id(step_key: str) -> str:
    return f"cleanup-{step_key.replace('_', '-')}"


class RichRenderable(Static):
    """Static widget that displays Rich renderables."""


class ShutdownScreen(ModalScreen):
    """Overlay de encerramento: mostra o que está sendo finalizado + barra.

    Ao montar, dispara o worker de encerramento do app (para evitar tocar nos
    widgets antes de existirem). O app fecha quando o worker termina.
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="shutdown-box"):
            yield Label(t("shutdown.title"), id="shutdown-title")
            yield Label(t("shutdown.step_network"), id="shutdown-step")
            yield ProgressBar(total=100, show_eta=False, id="shutdown-bar")

    def on_mount(self) -> None:
        self.app._run_shutdown()

    def set_step(self, label: str) -> None:
        try:
            self.query_one("#shutdown-step", Label).update(label)
        except Exception:
            pass

    def set_progress(self, pct: int) -> None:
        try:
            self.query_one("#shutdown-bar", ProgressBar).update(progress=pct)
        except Exception:
            pass


class VareduraTextualApp(CamerasMixin, App[str | None]):
    """Main Textual TUI for Varedura."""

    CSS = (
        """
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

    /* Etapas de limpeza: grade responsiva — o número de colunas é ajustado à
       largura disponível em on_resize (classes cols-2 / cols-3). */
    .step-grid {
        layout: grid;
        grid-size: 1;
        grid-gutter: 0 2;
        height: auto;
        margin-bottom: 1;
    }
    .step-grid.cols-2 { grid-size: 2; }
    .step-grid.cols-3 { grid-size: 3; }

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

    .lazy-pane {
        height: 1fr;
        align: center middle;
    }

    #network-targets-table {
        height: 12;
        margin-top: 1;
        margin-bottom: 1;
    }

    #network-diagnosis {
        height: auto;
        min-height: 3;
        border: solid $surface-lighten-2;
        padding: 0 1;
        margin-bottom: 1;
    }

    #repair-actions {
        height: auto;
        margin-bottom: 1;
    }

    #repair-actions Button {
        width: auto;
        margin-right: 1;
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

    ShutdownScreen {
        align: center middle;
    }
    #shutdown-box {
        width: 64;
        max-width: 90%;
        height: auto;
        border: thick $primary;
        background: $panel;
        padding: 2 4;
    }
    #shutdown-title {
        text-style: bold;
        color: $accent;
        width: 1fr;
        text-align: center;
        margin-bottom: 1;
    }
    #shutdown-step {
        color: $text-muted;
        width: 1fr;
        text-align: center;
        margin-bottom: 1;
    }
    #shutdown-bar {
        width: 1fr;
        align-horizontal: center;
    }
    """
        + CAMERAS_CSS
    )

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
        self._target_stats: dict[str, object] = {}
        self._target_latest: dict[str, object] = {}
        self._network_config = load_network_config()
        self._network_history = None
        self._ping_scheduler = None
        self._target_map: dict[str, object] = {}
        self._primary_target_id: str | None = None
        self._detail_target_id: str | None = None
        self._league_detector = None
        self._league_detector_generation = 0
        self._league_target = None
        self._league_endpoint = None
        self._league_detection_state = "waiting"
        self._diagnosis_report = None
        self._repair_actions: dict[str, object] = {}
        self._pending_app_ca_file = ""
        self._diagnostic_cancel = threading.Event()
        self._diagnostic_active = False
        self._speed_test_active = False
        self._network_run_generation = 0
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
        self._mascot = None
        self._mascot_state = STATES.IDLE
        self._mascot_msg = ""
        self._mascot_frame = 0
        # Estado da aba Câmeras (RTSP), fundida via CamerasMixin.
        self._init_cameras_state()
        self._shutting_down = False
        self._shutdown_screen = None
        self._hydrated_tabs = {"dashboard"}
        self._onboarding_open = False

    def compose(self) -> ComposeResult:
        self.title = "Varedura"
        self.sub_title = t("menu.subtitle")
        yield Header(show_clock=True)
        with TabbedContent(initial="dashboard", id="main-tabs"):
            with TabPane(t("textual.tab_dashboard"), id="dashboard"):
                yield from self._compose_dashboard()
            with TabPane(t("textual.tab_cleanup"), id="docker"):
                yield Vertical(
                    Label(t("textual.loading")),
                    id="docker-lazy-host",
                    classes="lazy-pane",
                )
            with TabPane(t("textual.tab_network"), id="network"):
                yield Vertical(
                    Label(t("textual.loading")),
                    id="network-lazy-host",
                    classes="lazy-pane",
                )
            with TabPane(t("rtsp.tab_cameras"), id="cameras"):
                yield Vertical(
                    Label(t("textual.loading")),
                    id="cameras-lazy-host",
                    classes="lazy-pane",
                )
            with TabPane(t("textual.tab_settings"), id="settings"):
                yield Vertical(
                    Label(t("textual.loading")),
                    id="settings-lazy-host",
                    classes="lazy-pane",
                )
        yield Footer()

    def _compose_dashboard(self) -> ComposeResult:
        with Horizontal(id="dashboard-grid", classes="pane"):
            with Vertical(id="dashboard-left"):
                yield RichRenderable(
                    Text(f"🤖 Varedura\n{t('mascot.welcome')}", justify="center"),
                    id="mascot-card",
                )
                yield RichRenderable(
                    build_dashboard_status(
                        load_recording_pref(),
                        get_language(),
                        self._network_status_snapshot(),
                    ),
                    id="dashboard-summary",
                )
                yield OptionList(
                    Option(
                        build_tool_option(
                            t("menu.option_1"), t("menu.desc_1"), "green"
                        ),
                        id="network",
                    ),
                    Option(
                        build_tool_option(t("menu.option_2"), t("menu.desc_2"), "cyan"),
                        id="docker",
                    ),
                    Option(
                        build_tool_option(
                            t("menu.option_3"), t("menu.desc_3"), "yellow"
                        ),
                        id="scanner",
                    ),
                    Option(
                        build_tool_option(
                            t("rtsp.tab_cameras"), t("rtsp.menu_desc"), "red"
                        ),
                        id="cameras",
                    ),
                    Option(Text(""), disabled=True),
                    Option(
                        build_tool_option(
                            t("menu.option_settings"),
                            t("menu.desc_settings"),
                            "magenta",
                        ),
                        id="settings",
                    ),
                    id="tool-menu",
                )
            with Vertical(id="dashboard-right"):
                yield RichRenderable(
                    build_achievements_row(self._game), id="achievements-card"
                )
                yield RichRenderable(build_records_panel(self._game), id="records-card")
                yield RichLog(
                    id="dashboard-log", highlight=True, markup=True, wrap=True
                )

    def _compose_cleanup(self) -> ComposeResult:
        steps = get_cleanup_steps()
        with Vertical(classes="pane"):
            # Scrollable configuration area.
            with VerticalScroll(id="cleanup-config"):
                yield Label(t("cleanup_prefs.title"), classes="section-title")
                with Horizontal(id="cleanup-top"):
                    yield RichRenderable(
                        Text("🤖", justify="center"), id="cleanup-mascot"
                    )
                    with Vertical(id="cleanup-reward"):
                        yield Label(
                            t("cleanup_prefs.freed_label"), classes="card-title"
                        )
                        yield Digits("0.0", id="cleanup-freed", classes="ping-digits")
                        yield Label("GB", classes="card-unit")
                with Horizontal(classes="button-row"):
                    yield Button(t("cleanup_prefs.preset_quick"), id="preset-quick")
                    yield Button(t("cleanup_prefs.preset_deep"), id="preset-deep")
                yield RichRenderable(
                    build_cleanup_status_panel(steps), id="cleanup-summary"
                )
                for group_key, icon, keys in CLEANUP_GROUPS:
                    yield Label(f"{icon} {t(group_key)}", classes="section-title")
                    with Container(classes="step-grid"):
                        for key in keys:
                            yield Checkbox(
                                t(cleanup_label_key(key)),
                                value=steps.get(key, False),
                                id=_cleanup_checkbox_id(key),
                            )
            # Fixed action + status + progress + log (always visible).
            with Horizontal(classes="button-row"):
                yield Button(
                    t("textual.cleanup_run"), id="run-cleanup", variant="primary"
                )
                yield Button(t("textual.cleanup_save"), id="save-cleanup")
            yield Label(t("textual.ready"), id="cleanup-status")
            yield ProgressBar(total=100, id="cleanup-progress")
            yield RichLog(id="cleanup-log", highlight=True, markup=True, wrap=True)

    def _compose_network(self) -> ComposeResult:
        with Vertical(classes="pane", id="network-pane"):
            with Horizontal(id="network-controls"):
                yield Button(
                    t("textual.network_start"), id="network-start", variant="primary"
                )
                yield Button(
                    t("textual.network_stop"), id="network-stop", disabled=True
                )
                yield Button(t("network.targets_button"), id="network-targets")
                yield Button(t("network.diagnose_button"), id="network-diagnose")
                yield Button(
                    t("network.cancel_button"),
                    id="network-diagnose-cancel",
                    disabled=True,
                )
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
                    yield Label(
                        t("stalker.graph_external"),
                        id="external-title",
                        classes="card-title",
                    )
                    yield Digits("--", id="external-digits", classes="ping-digits")
                    yield Label("ms", classes="card-unit")
                    yield Sparkline([], id="external-spark", summary_function=max)
                    yield Label("", id="external-stats", classes="card-stats")
            yield Static(t("network.diagnosis_idle"), id="network-diagnosis")
            yield Horizontal(id="repair-actions")
            yield DataTable(id="network-targets-table")
            with TabbedContent(initial="net-speed-tab", id="network-subtabs"):
                with TabPane(t("textual.network_speed"), id="net-speed-tab"):
                    with Vertical():
                        with Horizontal(classes="button-row"):
                            yield Button(
                                t("network.speed_start"), id="network-speed-start"
                            )
                            yield Button(
                                t("network.cancel_button"),
                                id="network-speed-cancel",
                                disabled=True,
                            )
                        yield DataTable(id="network-speed-table")
                with TabPane(t("textual.network_ports"), id="net-ports-tab"):
                    with Vertical():
                        yield Label(t("ports.waiting"), id="network-ports-summary")
                        yield DataTable(id="network-ports-table")
                with TabPane(t("textual.network_processes"), id="net-procs-tab"):
                    yield DataTable(id="network-procs-table")
                with TabPane(t("textual.network_events"), id="net-log-tab"):
                    yield RichLog(
                        id="network-log", highlight=True, markup=True, wrap=True
                    )

    @staticmethod
    def _target_selection_summary(config: dict) -> str:
        try:
            from monitor.ping_targets import TargetSelection

            selection = TargetSelection.from_config(config)
        except Exception:
            return t("network.no_targets")
        if not selection.targets:
            return t("network.no_targets")
        names = [
            f"{'★ ' if target.id == selection.primary_target_id else ''}{target.label}"
            for target in selection.targets
        ]
        return ", ".join(names)

    def _compose_settings(self) -> ComposeResult:
        lang_names = {"pt": t("lang.pt"), "en": t("lang.en")}
        language_options = [
            (lang_names.get(code, code), code) for code in get_supported_languages()
        ]
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
                yield Select(
                    language_options, value=get_language(), id="language-select"
                )

            net = self._network_config
            yield Label(t("settings.network_title"), classes="section-title")
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_gateway"))
                yield Input(value=str(net["gateway_ip"]), id="net-gateway")
                yield Button(t("settings.net_detect"), id="net-detect-gateway")
            with Horizontal(classes="form-row"):
                yield Label(t("network.targets_label"))
                yield Label(
                    self._target_selection_summary(net), id="net-target-summary"
                )
                yield Button(t("network.targets_button"), id="settings-network-targets")
            with Horizontal(classes="form-row"):
                yield Label(t("network.league_auto"))
                yield Switch(
                    value=bool(net.get("league_auto_detect", True)),
                    id="league-auto-switch",
                )
            with Horizontal(classes="form-row"):
                yield Label(t("network.export_full_ip"))
                yield Switch(
                    value=bool(net.get("include_full_ip_exports", False)),
                    id="export-full-ip-switch",
                )
            with Horizontal(classes="form-row"):
                yield Label(t("network.app_ca_file"))
                yield Input(
                    value=str(net.get("app_ca_file", "")),
                    placeholder=t("network.app_ca_hint"),
                    id="app-ca-file",
                )
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_threshold"))
                yield Input(
                    value=str(net["lag_threshold_ms"]),
                    id="net-threshold",
                    type="integer",
                )
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_contracted_down"))
                yield Input(
                    value=str(net["contracted_down"]), id="net-down", type="number"
                )
            with Horizontal(classes="form-row"):
                yield Label(t("settings.net_contracted_up"))
                yield Input(value=str(net["contracted_up"]), id="net-up", type="number")

            with Horizontal(classes="button-row"):
                yield Button(
                    t("textual.settings_save"), id="save-settings", variant="primary"
                )
                yield Button(t("mcp.option"), id="toggle-mcp")
            yield Label(
                t("mcp.status_on") if is_mcp_configured() else t("mcp.status_off"),
                id="mcp-status",
            )

    def on_mount(self) -> None:
        self.query_one("#tool-menu", OptionList).focus()
        self._write_dashboard_log(t("textual.ready"))
        self._dashboard_timer = self.set_interval(2.0, self._refresh_dashboard_status)
        self._mascot_timer = self.set_interval(0.5, self._animate_mascot)
        # Startup invariant: the first refresh happens before gateway discovery,
        # subprocesses, network traffic, or construction of hidden tab widgets.
        self.call_after_refresh(self._after_first_refresh)

    def _after_first_refresh(self) -> None:
        self._initialize_network_after_ready()
        self._run_dashboard_poller()
        self.set_timer(0.15, self._maybe_show_target_onboarding)

    async def _hydrate_tab(self, tab_id: str) -> None:
        """Compose an expensive tab only on its first activation."""
        if tab_id in self._hydrated_tabs:
            return
        host = self.query_one(f"#{tab_id}-lazy-host", Vertical)
        self._hydrated_tabs.add(tab_id)
        try:
            await host.remove_children()
            composers = {
                "docker": self._compose_cleanup,
                "network": self._compose_network,
                "cameras": self._compose_cameras,
                "settings": self._compose_settings,
            }
            await host.mount_compose(composers[tab_id]())
            host.remove_class("lazy-pane")
            # Nested TabbedContent mounts its own panes on the next refresh.
            self.call_after_refresh(self._finish_tab_hydration, tab_id)
        except Exception:
            self._hydrated_tabs.discard(tab_id)
            raise

    def _finish_tab_hydration(self, tab_id: str) -> None:
        if tab_id == "network":
            self._setup_network_tables()
            self._setup_target_table()
            self._render_target_table()
            if (
                self._network_config.get("target_onboarding_completed", False)
                and self._active_tab == "network"
                and not self.network_running
            ):
                self._start_network()
        elif tab_id == "cameras":
            self._cameras_on_mount()
            self._maybe_render_cameras()
        elif tab_id == "settings":
            self._refresh_target_selection_labels()

    def _network_status_snapshot(self) -> dict:
        """Cheap live snapshot of the network monitor for the dashboard."""
        snapshot: dict = {
            "running": self.network_running,
            "gateway_ip": str(self._network_config.get("gateway_ip", "") or ""),
            "lag_threshold_ms": int(
                self._network_config.get("lag_threshold_ms", 100) or 100
            ),
        }
        if self._net_local_stats is not None and self._net_local_stats.history:
            snapshot["local_ms"] = self._net_local_stats.history[-1]
        if self._net_external_stats is not None and self._net_external_stats.history:
            snapshot["ext_ms"] = self._net_external_stats.history[-1]
        if "gateway_ms" in self._dash_stats:
            snapshot.setdefault("local_ms", self._dash_stats["gateway_ms"])
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
        from monitor.port_scanner import get_system_network_stats
        from monitor.ping_targets import PingStatus, probe_ping

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
                    gateway = str(
                        self._network_config.get("gateway_ip", "") or ""
                    ).strip()
                    if gateway:
                        result = probe_ping(gateway, timeout_seconds=1.25)
                        self._dash_stats["gateway_ms"] = (
                            result.latency_ms
                            if result.status is PingStatus.SUCCESS
                            else None
                        )
                except Exception:
                    pass
            self._dash_stop.wait(timeout=3.0)

    def _get_mascot(self):
        if self._mascot is None:
            from mascot.renderer import MascotRenderer

            self._mascot = MascotRenderer()
        return self._mascot

    def _animate_mascot(self) -> None:
        """Cycle the mascot sprite frames; only while the dashboard is visible."""
        try:
            if self.query_one("#main-tabs", TabbedContent).active != "dashboard":
                return
            frames = FRAMES.get(self._mascot_state) or FRAMES[STATES.IDLE]
            path = frames[self._mascot_frame % len(frames)]
            self._mascot_frame += 1
            self.query_one("#mascot-card", RichRenderable).update(
                self._get_mascot().render_static_from_path(
                    path, self._mascot_msg, self._mascot_state
                )
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

    @work(thread=True, exclusive=True)
    def _initialize_network_after_ready(self) -> None:
        """Resolve local-only state after the first frame, without persisting it."""
        cfg = dict(self._network_config)
        detected = None
        if not str(cfg.get("gateway_ip", "")).strip():
            from monitor.netinfo import detect_default_gateway

            detected = detect_default_gateway()
            if detected:
                cfg["gateway_ip"] = detected
        self.call_from_thread(self._finish_network_initialization, cfg, detected)

    def _finish_network_initialization(self, cfg: dict, detected: str | None) -> None:
        self._network_config = cfg
        self._apply_network_config(cfg)
        if detected:
            self._write_dashboard_log(t("settings.net_gateway_detected", ip=detected))
        if "settings" in self._hydrated_tabs:
            try:
                self.query_one("#net-gateway", Input).value = str(
                    cfg.get("gateway_ip", "")
                )
            except Exception:
                pass

    def _apply_network_config(self, cfg: dict) -> None:
        """Push the config dict onto the live stalker/speed singletons."""
        try:
            import monitor.stalker as stalker_mod
            from monitor.ping_targets import TargetSelection
            from monitor.speed_tester import speed_config

            stalker_mod.config.gateway_ip = str(cfg.get("gateway_ip", "") or "").strip()
            selection = TargetSelection.from_config(cfg)
            stalker_mod.config.external_ip = (
                selection.primary_target.host if selection.primary_target else ""
            )
            stalker_mod.config.lag_threshold_ms = int(cfg["lag_threshold_ms"])
            speed_config.velocidade_contratada_down = float(cfg["contracted_down"])
            speed_config.velocidade_contratada_up = float(cfg["contracted_up"])
        except Exception:
            pass

    def action_show_settings(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "settings"

    def action_dashboard(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "dashboard"

    def action_quit(self) -> None:
        """Encerra deixando claro o que está sendo finalizado.

        Se nada pesado estiver em andamento, fecha na hora. Caso contrário,
        mostra uma tela de encerramento com barra de progresso enquanto para os
        monitores, o teste de velocidade (Chrome/Selenium) e os players.
        """
        if self._shutting_down:
            return
        if not (
            self.network_running
            or self._players
            or self._speed_test_active
            or self._diagnostic_active
        ):
            self.exit()
            return
        self._shutting_down = True
        self._shutdown_screen = ShutdownScreen()
        self.push_screen(self._shutdown_screen)

    @work(thread=True)
    def _run_shutdown(self) -> None:
        """Finaliza os recursos em background, atualizando a barra, e fecha."""
        screen = self._shutdown_screen
        steps = (
            (t("shutdown.step_network"), self._sd_stop_monitors),
            (t("shutdown.step_speed"), self._sd_stop_speed),
            (t("shutdown.step_players"), self._sd_close_resources),
        )
        total = len(steps)
        for i, (label, action) in enumerate(steps, 1):
            if screen is not None:
                self.call_from_thread(screen.set_step, label)
            try:
                action()
            except Exception:
                pass
            if screen is not None:
                self.call_from_thread(screen.set_progress, int(i / total * 100))
        if screen is not None:
            self.call_from_thread(screen.set_step, t("shutdown.step_done"))
        self.call_from_thread(self.exit)

    def _sd_stop_monitors(self) -> None:
        self._network_run_generation += 1
        self._league_detector_generation += 1
        self._network_stop.set()
        self._dash_stop.set()
        self._diagnostic_cancel.set()
        if self._ping_scheduler is not None:
            self._ping_scheduler.stop(wait=False)
            self._ping_scheduler = None
        if self._league_detector is not None:
            self._league_detector.stop(wait=False)
            self._league_detector = None

    def _sd_stop_speed(self) -> None:
        from monitor.speed_tester import stop_continuous_testing

        stop_continuous_testing()

    def _sd_close_resources(self) -> None:
        for proc in list(self._players):
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass
        if self._net_pool is not None:
            try:
                self._net_pool.shutdown(wait=False)
            except Exception:
                pass

    def action_rescan_ports(self) -> None:
        """Jump to the network ports view and force a fresh scan next tick."""
        tabs = self.query_one("#main-tabs", TabbedContent)
        if tabs.active != "network":
            tabs.active = "network"
        self.set_timer(0.05, self._activate_ports_subtab)
        # Start the monitor first if paused (it resets the flag), then request a
        # scan on the very next tick.
        if not self.network_running:
            self._start_network()
        self._force_scan = True
        self.notify(t("textual.network_rescan"))

    def _activate_ports_subtab(self, attempt: int = 0) -> None:
        try:
            self.query_one("#network-subtabs", TabbedContent).active = "net-ports-tab"
        except Exception:
            if attempt < 10:
                self.set_timer(0.1, lambda: self._activate_ports_subtab(attempt + 1))

    @on(OptionList.OptionSelected, "#tool-menu")
    def on_tool_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = str(event.option_id or "")
        # The legacy "Port Scanner" menu entry now opens the live ports view
        # inside the Network tab (the standalone scanner tab was merged in).
        if option_id == "scanner":
            self.query_one("#main-tabs", TabbedContent).active = "network"
            self.set_timer(0.05, self._activate_ports_subtab)
            return
        if option_id in {"network", "docker", "cameras", "settings"}:
            self.query_one("#main-tabs", TabbedContent).active = option_id

    @on(TabbedContent.TabActivated, "#main-tabs")
    async def on_main_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        self._active_tab = event.pane.id or self._active_tab
        if event.pane.id in {"docker", "network", "cameras", "settings"}:
            await self._hydrate_tab(event.pane.id)

    def on_data_table_row_selected(self, event) -> None:
        if getattr(event.data_table, "id", None) == "network-targets-table":
            self._detail_target_id = str(event.row_key.value)
            self._render_target_detail_card()
            return
        self._cameras_on_row_selected(event)

    def on_descendant_focus(self, event) -> None:
        self._cameras_on_focus(event)

    def on_worker_state_changed(self, event) -> None:
        self._cameras_on_worker_state(event)

    def on_resize(self, event) -> None:
        width = event.size.width
        self._cameras_on_resize(width)
        # Etapas de limpeza: nº de colunas conforme a largura disponível.
        cols = 3 if width >= 110 else (2 if width >= 70 else 1)
        for grid in self.query(".step-grid"):
            grid.set_class(cols == 2, "cols-2")
            grid.set_class(cols == 3, "cols-3")

    def on_unmount(self) -> None:
        # Sinaliza a parada do worker de rede (que encerra o ThreadPoolExecutor
        # no seu finally) e para os timers periódicos para que não disparem
        # durante o teardown da aplicação.
        self._network_stop.set()
        self._network_run_generation += 1
        self._league_detector_generation += 1
        self._dash_stop.set()
        self._diagnostic_cancel.set()
        if self._ping_scheduler is not None:
            self._ping_scheduler.stop(wait=False)
            self._ping_scheduler = None
        if self._league_detector is not None:
            self._league_detector.stop(wait=False)
            self._league_detector = None
        if self._speed_test_active:
            try:
                from monitor.speed_tester import stop_continuous_testing

                stop_continuous_testing()
            except Exception:
                pass
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
        elif button_id in {"network-targets", "settings-network-targets"}:
            self._open_target_picker(onboarding=False)
        elif button_id == "network-diagnose":
            self._run_network_diagnosis()
        elif button_id == "network-diagnose-cancel":
            self._cancel_network_diagnosis()
        elif button_id == "network-speed-start":
            self._start_speed_test()
        elif button_id == "network-speed-cancel":
            self._cancel_speed_test()
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
        elif button_id and button_id.startswith("repair-action-"):
            self._confirm_repair_action(button_id)
        else:
            # Camera tab buttons (network cards, scans, credentials, etc.).
            self._cameras_handle_button(button_id or "")

    def _apply_cleanup_preset(self, enabled_keys: list[str]) -> None:
        wanted = set(enabled_keys)
        for key, _label_key, _default in CLEANUP_STEPS:
            self.query_one(f"#{_cleanup_checkbox_id(key)}", Checkbox).value = (
                key in wanted
            )
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

    def _maybe_show_target_onboarding(self) -> None:
        from monitor.ping_targets import TargetSelection

        selection = TargetSelection.from_config(self._network_config)
        if not selection.onboarding_completed or not selection.targets:
            self._open_target_picker(onboarding=True)

    def _open_target_picker(self, *, onboarding: bool) -> None:
        if self._onboarding_open:
            return
        from cli.network_ui import TargetPickerScreen

        self._onboarding_open = True
        self.push_screen(
            TargetPickerScreen(self._network_config, onboarding=onboarding),
            self._on_targets_selected,
        )

    def _on_targets_selected(self, selection_config: dict | None) -> None:
        self._onboarding_open = False
        if selection_config is None:
            if not self._network_config.get("target_onboarding_completed", False):
                self._write_dashboard_log(t("network.onboarding_deferred"))
            return
        updated = dict(self._network_config)
        updated.update(selection_config)
        save_network_config(updated)
        self._network_config = load_network_config()
        self._apply_network_config(self._network_config)
        self._refresh_target_selection_labels()
        self._render_target_table()
        self._reconfigure_ping_scheduler()
        self._sync_league_detector()
        if self._active_tab == "network" and not self.network_running:
            self._start_network()
        self.notify(t("network.targets_saved"))

    def _refresh_target_selection_labels(self) -> None:
        summary = self._target_selection_summary(self._network_config)
        try:
            self.query_one("#net-target-summary", Label).update(summary)
            self.query_one("#league-auto-switch", Switch).value = bool(
                self._network_config.get("league_auto_detect", True)
            )
        except Exception:
            pass

    def _run_network_diagnosis(self) -> None:
        if "network" not in self._hydrated_tabs:
            return
        self._diagnostic_cancel.clear()
        self._diagnostic_active = True
        self.query_one("#network-diagnose", Button).disabled = True
        self.query_one("#network-diagnose-cancel", Button).disabled = False
        self.query_one("#network-diagnosis", Static).update(
            t("network.diagnosis_running")
        )
        self._diagnose_network_worker()

    def _cancel_network_diagnosis(self) -> None:
        if not self._diagnostic_active:
            return
        self._diagnostic_cancel.set()
        self.query_one("#network-diagnose-cancel", Button).disabled = True
        self.query_one("#network-diagnosis", Static).update(
            t("network.diagnosis_cancelling")
        )

    @work(thread=True, exclusive=True)
    def _diagnose_network_worker(self) -> None:
        try:
            from monitor.network_diagnostics import (
                DiagnosticOptions,
                diagnose_network,
            )

            report = diagnose_network(
                options=DiagnosticOptions(
                    ca_file=str(self._network_config.get("app_ca_file", "") or "")
                    or None
                ),
                cancel_event=self._diagnostic_cancel,
            )
            self.call_from_thread(self._finish_network_diagnosis, report, None)
        except Exception as exc:
            self.call_from_thread(self._finish_network_diagnosis, None, str(exc))

    def _finish_network_diagnosis(self, report, error: str | None) -> None:
        self._diagnostic_active = False
        try:
            self.query_one("#network-diagnose", Button).disabled = False
            self.query_one("#network-diagnose-cancel", Button).disabled = True
        except Exception:
            pass
        if error or report is None:
            self.query_one("#network-diagnosis", Static).update(
                t("network.diagnosis_failed", error=error or "unknown")
            )
            return
        self._diagnosis_report = report
        evidence = "\n".join(f"• {item.message}" for item in report.evidence[:4])
        self.query_one("#network-diagnosis", Static).update(
            f"[bold]{t(f'network.state_{report.state.value}')}[/] "
            f"({t(f'network.confidence_{report.confidence.value}')})\n"
            f"{report.summary}\n{evidence}"
        )
        if self._ping_scheduler is not None:
            from monitor.network_diagnostics import NetworkState, ProbeKind

            self._ping_scheduler.set_route_available(report.snapshot.route_present)
            https_probe = report.probe(ProbeKind.HTTPS)
            self._ping_scheduler.set_alternative_connectivity_healthy(
                report.state in {NetworkState.ONLINE, NetworkState.ONLINE_MANAGED}
                and bool(https_probe and https_probe.succeeded)
            )
        self._show_repair_actions(report)

    def _show_repair_actions(self, report) -> None:
        from monitor.network_repairs import list_repair_actions, list_repair_guidance

        actions = list_repair_actions(
            report,
            app_ca_file=(
                self._pending_app_ca_file
                or str(self._network_config.get("app_ca_file", "") or "")
                or None
            ),
        )
        container = self.query_one("#repair-actions", Horizontal)
        container.remove_children()
        self._repair_actions = {}
        buttons = []
        for index, action in enumerate(actions):
            button_id = f"repair-action-{index}"
            self._repair_actions[button_id] = action
            label = action.title
            if not action.eligible and action.blocked_reason:
                label = f"{label} ({action.blocked_reason})"
            buttons.append(Button(label, id=button_id, disabled=not action.eligible))
        if buttons:
            container.mount(*buttons)
        guidance = list_repair_guidance(report)
        if guidance:
            self._network_log(f"[dim]{guidance[0].title}: {guidance[0].explanation}[/]")

    def _confirm_repair_action(self, button_id: str) -> None:
        action = self._repair_actions.get(button_id)
        if action is None:
            return
        from cli.network_ui import RepairConfirmationScreen

        self.push_screen(
            RepairConfirmationScreen(action),
            lambda confirmed: self._on_repair_confirmed(action, confirmed),
        )

    def _on_repair_confirmed(self, action, confirmed: bool) -> None:
        if not confirmed or self._diagnosis_report is None:
            return
        self._diagnostic_cancel.clear()
        self._diagnostic_active = True
        self.query_one("#network-diagnose", Button).disabled = True
        self.query_one("#network-diagnose-cancel", Button).disabled = False
        self._execute_repair_worker(action, self._diagnosis_report)

    @work(thread=True, exclusive=True)
    def _execute_repair_worker(self, action, report) -> None:
        try:
            from monitor.network_diagnostics import (
                DiagnosticOptions,
                collect_network_snapshot,
                diagnose_network,
            )
            from monitor.network_repairs import RepairExecutor

            ca_file = getattr(action, "ca_file", None) or str(
                self._network_config.get("app_ca_file", "") or ""
            )
            executor = RepairExecutor(
                post_test=lambda: diagnose_network(
                    options=DiagnosticOptions(ca_file=ca_file or None),
                    cancel_event=self._diagnostic_cancel,
                ),
                preflight_snapshot=lambda: collect_network_snapshot(
                    timeout=2.5,
                    cancel_event=self._diagnostic_cancel,
                ),
            )
            result = executor.execute(
                action,
                report,
                confirmed=True,
                cancel_event=self._diagnostic_cancel,
            )
            self.call_from_thread(self._finish_repair, result, None)
        except Exception as exc:
            self.call_from_thread(self._finish_repair, None, str(exc))

    def _finish_repair(self, result, error: str | None) -> None:
        self._diagnostic_active = False
        self.query_one("#network-diagnose", Button).disabled = False
        self.query_one("#network-diagnose-cancel", Button).disabled = True
        if error or result is None:
            self._network_log(
                f"[red]{t('network.repair_failed', error=error or 'unknown')}[/]"
            )
            return
        color = "green" if result.succeeded else "yellow"
        self._network_log(f"[{color}]{result.action.title}: {result.message}[/]")
        if result.succeeded and result.app_ca_file:
            updated = dict(self._network_config)
            updated["app_ca_file"] = result.app_ca_file
            save_network_config(updated)
            self._network_config = load_network_config()
            self._pending_app_ca_file = ""
        if result.post_report is not None:
            self._finish_network_diagnosis(result.post_report, None)

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
        if not self._save_network_settings():
            return
        self._refresh_status_renderables()
        self.notify(t("textual.settings_saved"))
        self._write_dashboard_log(t("textual.settings_saved"))

    def _save_network_settings(self) -> bool:
        """Read the network form, validate, persist and apply it."""
        cfg = dict(self._network_config)
        cfg["gateway_ip"] = self.query_one("#net-gateway", Input).value.strip()
        try:
            cfg["lag_threshold_ms"] = int(
                self.query_one("#net-threshold", Input).value or 0
            )
            cfg["contracted_down"] = float(
                self.query_one("#net-down", Input).value or 0
            )
            cfg["contracted_up"] = float(self.query_one("#net-up", Input).value or 0)
        except ValueError:
            self.notify(t("settings.net_invalid"), severity="error")
            return False
        if (
            cfg["lag_threshold_ms"] <= 0
            or cfg["contracted_down"] < 0
            or cfg["contracted_up"] < 0
        ):
            self.notify(t("settings.net_invalid"), severity="error")
            return False
        cfg["league_auto_detect"] = bool(
            self.query_one("#league-auto-switch", Switch).value
        )
        cfg["include_full_ip_exports"] = bool(
            self.query_one("#export-full-ip-switch", Switch).value
        )
        candidate_ca = self.query_one("#app-ca-file", Input).value.strip()
        active_ca = str(self._network_config.get("app_ca_file", "") or "")
        if not candidate_ca:
            cfg["app_ca_file"] = ""
            self._pending_app_ca_file = ""
        elif candidate_ca == active_ca:
            cfg["app_ca_file"] = active_ca
        else:
            # A newly supplied CA remains a non-persistent candidate until the
            # policy-aware repair confirmation validates it for app-only use.
            cfg["app_ca_file"] = active_ca
            self._pending_app_ca_file = candidate_ca
            self.notify(t("network.ca_pending_confirmation"), severity="warning")
        save_network_config(cfg)
        self._network_config = cfg
        self._apply_network_config(cfg)
        self._sync_league_detector()
        return True

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
            steps[key] = bool(
                self.query_one(f"#{_cleanup_checkbox_id(key)}", Checkbox).value
            )
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
            self.call_from_thread(
                self._update_cleanup_progress, completed, total, label
            )

        try:
            success, failures, freed = run_cleanup_steps(
                step_keys, rich_console, progress
            )
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
                self._get_mascot().render_static(STATES.WORKING, t("mascot.scanning"))
            )

    def _write_cleanup_log(self, line: str) -> None:
        self.query_one("#cleanup-log", RichLog).write(line)

    def _update_cleanup_progress(self, completed: int, total: int, label: str) -> None:
        bar = self.query_one("#cleanup-progress", ProgressBar)
        bar.total = max(total, 1)
        bar.progress = min(completed, max(total, 1))
        self.query_one("#cleanup-status", Label).update(label)

    def _finish_cleanup(
        self, success: bool, failures: list[str], freed: float = 0.0
    ) -> None:
        if success:
            message = t("textual.cleanup_success")
            severity = "information"
        else:
            detail = (
                ", ".join(failures)
                if failures
                else t("menu.error_during_cleanup", error="")
            )
            message = t("menu.error_during_cleanup", error=detail)
            severity = "error"
        self.query_one("#cleanup-status", Label).update(message)
        self._write_cleanup_log(message)
        self.notify(message, severity=severity)

        # Gamified reward: show freed space + celebrate via the mascot.
        self.query_one("#cleanup-freed", Digits).update(f"{freed:.1f}")
        self.query_one("#cleanup-mascot", RichRenderable).update(
            self._get_mascot().render_static(
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

    def _setup_target_table(self) -> None:
        table = self.query_one("#network-targets-table", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns(
            t("network.col_target"),
            t("network.col_method"),
            t("network.col_now"),
            t("network.col_min"),
            t("network.col_avg"),
            t("network.col_max"),
            t("network.col_jitter"),
            t("network.col_loss"),
            t("network.col_status"),
            t("network.col_trend"),
        )

    @staticmethod
    def _target_jitter(values: list[float]) -> float | None:
        if len(values) < 2:
            return None
        return sum(
            abs(current - previous) for previous, current in zip(values, values[1:])
        ) / (len(values) - 1)

    @staticmethod
    def _target_trend(values: list[float]) -> str:
        if len(values) < 4:
            return "—"
        width = min(5, len(values) // 2)
        previous = sum(values[-2 * width : -width]) / width
        current = sum(values[-width:]) / width
        tolerance = max(1.0, previous * 0.05)
        if current > previous + tolerance:
            return "↑"
        if current < previous - tolerance:
            return "↓"
        return "→"

    @staticmethod
    def _live_target_label(target) -> str:
        if target.category.value == "league_match":
            return f"{target.label} — {target.host}"
        if target.id == "lol_br1_api":
            return f"{target.label} — {t('network.lol_br1_short_warning')}"
        return target.label

    def _render_target_table(self) -> None:
        if "network" not in self._hydrated_tabs:
            return
        try:
            table = self.query_one("#network-targets-table", DataTable)
        except Exception:
            return
        table.clear()
        snapshots = self._ping_scheduler.snapshot() if self._ping_scheduler else ()
        if not snapshots:
            try:
                from monitor.ping_targets import TargetSelection

                selection = TargetSelection.from_config(self._network_config)
                targets = selection.targets
            except Exception:
                targets = ()
            for target in targets:
                prefix = (
                    "★ "
                    if target.id == self._network_config.get("primary_target_id")
                    else ""
                )
                table.add_row(
                    f"{prefix}{self._live_target_label(target)}",
                    "ICMP",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    "—",
                    t("network.status_waiting"),
                    "—",
                    key=target.id,
                )
            return
        for snapshot in snapshots:
            target = snapshot.target
            stats = self._target_stats.get(target.id)
            history = list(getattr(stats, "history", ()))
            valid = [value for value in history if value is not None]
            loss = (
                (100.0 * (len(history) - len(valid)) / len(history))
                if history
                else None
            )
            result = self._target_latest.get(target.id)
            latency = getattr(result, "latency_ms", None)
            status = getattr(getattr(result, "status", None), "value", "waiting")
            role_icon = {
                "gateway": "⌂ ",
                "primary": "★ ",
                "league": "🎮 ",
            }.get(snapshot.role.value, "")
            jitter = self._target_jitter(valid)
            method = str(getattr(result, "method", "icmp")).upper()
            if snapshot.role.value == "league" and self._league_endpoint is not None:
                method = "ICMP+UDP"
            table.add_row(
                f"{role_icon}{self._live_target_label(target)}",
                method,
                "—" if latency is None else f"{latency:.1f}",
                "—" if not valid else f"{min(valid):.1f}",
                "—" if not valid else f"{sum(valid) / len(valid):.1f}",
                "—" if not valid else f"{max(valid):.1f}",
                "—" if jitter is None else f"{jitter:.1f}",
                "—" if loss is None else f"{loss:.0f}%",
                t(f"network.ping_status_{status}"),
                self._target_trend(valid),
                key=target.id,
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
        self.query_one("#network-ports-summary", Label).update(
            build_ports_summary(scan_state)
        )

    def _render_procs_table(self, procs) -> None:
        """Render the merged processes view: active connections (live every tick)
        enriched with RAM from the latest port scan, matched by process name."""
        table = self.query_one("#network-procs-table", DataTable)
        table.clear()
        ram_by_name = {
            pc.nome: pc.memoria_mb
            for pc in self._last_top_connections
            if pc.memoria_mb > 0
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
        from monitor.network_history import NetworkSessionHistory
        from monitor.ping_scheduler import PingScheduler
        from monitor.ping_targets import (
            PingTarget,
            TargetCategory,
            TargetSelection,
        )
        from monitor.stalker import PingStats

        selection = TargetSelection.from_config(self._network_config)
        if not selection.targets:
            self.notify(t("network.choose_one_target"), severity="warning")
            self._open_target_picker(onboarding=True)
            return

        self._net_local_stats = PingStats()
        self._net_external_stats = PingStats()
        self._target_stats = {target.id: PingStats() for target in selection.targets}
        self._target_latest = {}
        self._target_map = {target.id: target for target in selection.targets}
        self._primary_target_id = selection.primary_target_id
        self._detail_target_id = selection.primary_target_id
        self._network_history = NetworkSessionHistory()
        gateway = None
        gateway_host = str(self._network_config.get("gateway_ip", "") or "").strip()
        if gateway_host:
            try:
                gateway = PingTarget(
                    "gateway",
                    t("stalker.graph_gateway"),
                    gateway_host,
                    TargetCategory.GATEWAY,
                    ephemeral=True,
                )
                self._target_map[gateway.id] = gateway
                self._target_stats[gateway.id] = self._net_local_stats
            except ValueError:
                gateway = None
        self._target_stats[selection.primary_target_id] = self._net_external_stats
        self._ping_scheduler = PingScheduler()
        self._ping_scheduler.configure(selection, gateway_target=gateway)
        self._ping_scheduler.set_route_available(gateway is not None)
        self._net_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="net-aux")
        self._network_tick = 0
        self._force_scan = False
        self._last_top_connections = []
        self._network_stop.clear()
        self._network_run_generation += 1
        run_generation = self._network_run_generation
        self._set_network_running(True)
        self._ping_scheduler.start(
            lambda result: self.call_from_thread(
                self._accept_ping_result, result, run_generation
            )
        )
        if selection.league_auto_detect:
            from monitor.league_detector import LeagueMatchDetector

            self._league_detector_generation += 1
            detector_generation = self._league_detector_generation
            self._league_detector = LeagueMatchDetector()
            self._league_detector.start(
                lambda result: self.call_from_thread(
                    self._accept_league_detection,
                    result,
                    run_generation,
                    detector_generation,
                )
            )
        self._run_network_worker()

    def _stop_network(self) -> None:
        self._network_run_generation += 1
        self._league_detector_generation += 1
        self._network_stop.set()
        scheduler, self._ping_scheduler = self._ping_scheduler, None
        if scheduler is not None:
            scheduler.stop(wait=False)
        detector, self._league_detector = self._league_detector, None
        if detector is not None:
            detector.stop(wait=False)
        self._set_network_running(False)

    def _reconfigure_ping_scheduler(self) -> None:
        if self._ping_scheduler is None:
            return
        from monitor.ping_targets import PingTarget, TargetCategory, TargetSelection
        from monitor.stalker import PingStats

        selection = TargetSelection.from_config(self._network_config)
        if not selection.targets:
            self._stop_network()
            return
        gateway = None
        gateway_host = str(self._network_config.get("gateway_ip", "") or "").strip()
        if gateway_host:
            try:
                gateway = PingTarget(
                    "gateway",
                    t("stalker.graph_gateway"),
                    gateway_host,
                    TargetCategory.GATEWAY,
                    ephemeral=True,
                )
            except ValueError:
                gateway = None
        self._target_map = {target.id: target for target in selection.targets}
        if gateway is not None:
            self._target_map[gateway.id] = gateway
        if self._league_target is not None:
            self._target_map[self._league_target.id] = self._league_target
        for target_id in self._target_map:
            self._target_stats.setdefault(target_id, PingStats())
        self._primary_target_id = selection.primary_target_id
        self._detail_target_id = self._detail_target_id or selection.primary_target_id
        self._ping_scheduler.configure(
            selection,
            gateway_target=gateway,
            league_target=self._league_target,
        )
        self._render_target_table()

    def _sync_league_detector(self) -> None:
        if not self.network_running:
            return
        enabled = bool(self._network_config.get("league_auto_detect", True))
        if enabled and self._league_detector is None:
            from monitor.league_detector import LeagueMatchDetector

            run_generation = self._network_run_generation
            self._league_detector_generation += 1
            detector_generation = self._league_detector_generation
            self._league_detector = LeagueMatchDetector()
            self._league_detector.start(
                lambda result: self.call_from_thread(
                    self._accept_league_detection,
                    result,
                    run_generation,
                    detector_generation,
                )
            )
        elif not enabled and self._league_detector is not None:
            self._league_detector_generation += 1
            self._league_detector.stop(wait=False)
            self._league_detector = None
            self._league_endpoint = None
            self._league_target = None
            self._reconfigure_ping_scheduler()

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
        from monitor.stalker import config as stalker_config
        from monitor.port_scanner import run_full_scan

        self.call_from_thread(
            self._network_log, f"[dim]{t('stalker.monitoring_started')}[/]"
        )

        pool = self._net_pool
        try:
            while not self._network_stop.is_set():
                f_procs = pool.submit(stalker_mod.get_top_network_hogs)
                self._network_tick += 1
                do_scan = (
                    self._network_tick % stalker_config.port_scan_interval == 0
                    or self._force_scan
                )
                self._force_scan = False
                f_scan = pool.submit(run_full_scan) if do_scan else None

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

                try:
                    import monitor.speed_tester as speed_module

                    speed_snapshot = (
                        speed_module.speed_tester.get_stats_snapshot()
                        if speed_module.speed_tester is not None
                        else {}
                    )
                except Exception:
                    speed_snapshot = {}

                self.call_from_thread(
                    self._render_auxiliary_network,
                    procs,
                    scan_state,
                    speed_snapshot,
                )
                self._network_stop.wait(timeout=stalker_config.interval)
        finally:
            if pool is not None:
                pool.shutdown(wait=False)
            self.call_from_thread(self._set_network_running, False)

    @staticmethod
    def _future_result(future):
        try:
            return future.result()
        except Exception:
            return None

    def _accept_ping_result(self, result, run_generation: int | None = None) -> None:
        """Consume one generation-checked scheduler result on the UI thread."""
        if not self.network_running or (
            run_generation is not None
            and run_generation != self._network_run_generation
        ):
            return
        from monitor.ping_targets import PingStatus

        target = self._target_map.get(result.target_id)
        if target is None:
            return
        self._target_latest[result.target_id] = result
        stats = self._target_stats.get(result.target_id)
        value = result.latency_ms if result.status is PingStatus.SUCCESS else None
        if stats is not None:
            stats.add(value)

        endpoint = (
            self._league_endpoint
            if result.target_id.startswith("league_match_")
            else None
        )
        if self._network_history is not None:
            self._network_history.add_result(
                result,
                target,
                remote_port=getattr(endpoint, "port", None),
                session_id=getattr(endpoint, "session_id", None),
            )

        try:
            import monitor.stalker as stalker_mod

            if result.target_id == "gateway":
                stalker_mod.local_stats.add(value)
            elif result.target_id == self._primary_target_id:
                stalker_mod.external_stats.add(value)
                gateway_result = self._target_latest.get("gateway")
                stalker_mod.record_ping_sample(
                    datetime.datetime.now(),
                    getattr(gateway_result, "latency_ms", None),
                    value,
                )
        except Exception:
            pass

        speed_snapshot = {}
        try:
            import monitor.speed_tester as speed_module

            if speed_module.speed_tester is not None:
                speed_snapshot = speed_module.speed_tester.get_stats_snapshot()
        except Exception:
            pass

        threshold = int(self._network_config.get("lag_threshold_ms", 100))
        compliant, best_down = self._speed_compliance(speed_snapshot)
        primary_result = self._target_latest.get(self._primary_target_id or "")
        primary_history = list(self._net_external_stats.history)
        if getattr(primary_result, "status", None) is PingStatus.ICMP_FILTERED:
            primary_history = [item for item in primary_history if item is not None]
        score, tier, color = compute_health_score(
            list(self._net_local_stats.history),
            primary_history,
            threshold,
            compliant,
        )
        primary_ms = getattr(primary_result, "latency_ms", None)
        ok = primary_ms is not None and primary_ms <= threshold
        streak_s = (
            self._streak.update(ok, 1.0)
            if result.target_id == self._primary_target_id
            else self._streak.seconds
        )
        health = {
            "score": score,
            "tier": tier,
            "color": color,
            "streak_s": streak_s,
            "ping": primary_ms,
            "best_down": best_down,
            "compliant": compliant,
            "monitor_s": 1.0,
        }
        if result.target_id in {"gateway", self._primary_target_id}:
            if result.status is PingStatus.ICMP_FILTERED:
                self._network_log(f"[yellow]{t('network.icmp_filtered')}[/]")
            elif value is not None and value > threshold:
                self._network_log(f"[yellow]{t('stalker.alert_ext_lag', ms=value)}[/]")
        self._render_ping_update(
            health,
            speed_snapshot,
            record=result.target_id == self._primary_target_id,
        )

    def _render_ping_update(
        self, health: dict, speed_snapshot: dict, *, record: bool = True
    ) -> None:
        if record:
            self._record_and_check(health)
            self._score_hist.append(float(health.get("score", 0)))
            self._update_mascot_state(
                int(health.get("score", 0)), bool(speed_snapshot.get("is_testing"))
            )
        if self._active_tab != "network":
            return
        self._render_health_card(health)
        gateway_result = self._target_latest.get("gateway")
        self._render_ping_card(
            "gateway",
            getattr(gateway_result, "latency_ms", None),
            self._net_local_stats,
            int(self._network_config.get("lag_threshold_ms", 100)),
        )
        self._render_target_detail_card()
        self._render_target_table()
        self._render_speed_table(speed_snapshot)

    def _render_target_detail_card(self) -> None:
        if "network" not in self._hydrated_tabs:
            return
        target_id = self._detail_target_id or self._primary_target_id
        target = self._target_map.get(target_id or "")
        stats = self._target_stats.get(target_id or "")
        if target is None or stats is None:
            return
        result = self._target_latest.get(target_id or "")
        self.query_one("#external-title", Label).update(self._live_target_label(target))
        self._render_ping_card(
            "external",
            getattr(result, "latency_ms", None),
            stats,
            int(self._network_config.get("lag_threshold_ms", 100)),
        )

    def _accept_league_detection(
        self,
        result,
        run_generation: int | None = None,
        detector_generation: int | None = None,
    ) -> None:
        if (
            run_generation is not None
            and run_generation != self._network_run_generation
        ):
            return
        if detector_generation is not None and (
            detector_generation != self._league_detector_generation
            or not bool(self._network_config.get("league_auto_detect", True))
        ):
            return
        from monitor.league_detector import LeagueDetectorState

        self._league_detection_state = result.state.value
        endpoint = result.endpoint
        if result.state is LeagueDetectorState.ENDED or (
            endpoint is None
            and result.state
            in {
                LeagueDetectorState.ACTIVE_PENDING,
                LeagueDetectorState.AMBIGUOUS,
                LeagueDetectorState.PERMISSION_DENIED,
            }
        ):
            had_target = self._league_target is not None
            self._league_endpoint = None
            self._league_target = None
            if had_target:
                self._reconfigure_ping_scheduler()
        elif endpoint is not None:
            target = endpoint.to_ping_target()
            if self._league_target != target:
                self._league_endpoint = endpoint
                self._league_target = target
                self._detail_target_id = target.id
                self._reconfigure_ping_scheduler()
        if "network" in self._hydrated_tabs:
            detail = result.detail or result.state.value
            prefix = (
                "[yellow]"
                if result.state
                in {
                    LeagueDetectorState.PERMISSION_DENIED,
                    LeagueDetectorState.AMBIGUOUS,
                }
                else "[dim]"
            )
            self._network_log(f"{prefix}League: {detail}[/]")
            self._render_target_table()

    def _render_auxiliary_network(self, procs, scan_state, speed_snapshot) -> None:
        if scan_state is not None:
            self._last_top_connections = list(scan_state.top_connections)
        if self._active_tab != "network":
            return
        if scan_state is not None:
            self._render_ports_table(scan_state)
        self._render_procs_table(procs)
        self._render_speed_table(speed_snapshot or {})

    def _build_network_alerts(
        self, local_ms, ext_ms, threshold: int, procs: list, analyze_lag_source
    ) -> list[str]:
        lines: list[str] = []
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        alert_triggered = False

        if local_ms and local_ms > threshold:
            lines.append(
                f"[{stamp}] [bold red]{t('stalker.alert_local_lag', ms=local_ms)}[/]"
            )
            alert_triggered = True
        elif ext_ms and ext_ms > threshold:
            lines.append(
                f"[{stamp}] [bold orange1]{t('stalker.alert_ext_lag', ms=ext_ms)}[/]"
            )
            alert_triggered = True
        elif local_ms is None or ext_ms is None:
            lines.append(
                f"[{stamp}] [bold white on red]{t('stalker.alert_packet_loss')}[/]"
            )
            alert_triggered = True

        if alert_triggered:
            suspeito, explicacao = analyze_lag_source(
                local_ms, ext_ms, threshold, procs
            )
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
        self,
        local_ms,
        ext_ms,
        procs,
        scan_state,
        speed_snapshot,
        log_lines,
        health=None,
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
                int(health.get("score", 0)),
                bool((speed_snapshot or {}).get("is_testing")),
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

        self._apply_status_class(
            (digits, spark), self._ping_status_class(ms, threshold)
        )

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
        self.query_one("#health-spark", Sparkline).data = list(self._score_hist) or [
            0.0
        ]
        self.query_one("#health-tier", Label).update(
            Text(f"{tier}", style=f"bold {color}")
        )

        streak_s = float(health.get("streak_s", 0.0))
        self.query_one("#health-streak", Label).update(
            t("game.streak", time=format_duration(streak_s))
        )

        cls = "ping-ok" if score >= 75 else "ping-warn" if score >= 45 else "ping-bad"
        self._apply_status_class(
            (digits, self.query_one("#health-spark", Sparkline)), cls
        )

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
                table.add_row(
                    current,
                    f"{progress:.0f} Mbps",
                    t("stalker.speed_downloading"),
                    "...",
                )
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

    def _start_speed_test(self) -> None:
        button = self.query_one("#network-speed-start", Button)
        if button.disabled or self._speed_test_active:
            return
        try:
            from monitor.speed_tester import get_speed_tester

            tester = get_speed_tester()
            if not tester.prepare_single_test():
                return
        except Exception as exc:
            self._network_log(f"[yellow]{exc}[/]")
            return
        self._speed_test_active = True
        button.disabled = True
        self.query_one("#network-speed-cancel", Button).disabled = False
        self._network_log(f"[cyan]{t('network.speed_started')}[/]")
        self._run_speed_test_once(prepared=True)

    def _cancel_speed_test(self) -> None:
        if not self._speed_test_active:
            return
        try:
            from monitor.speed_tester import get_speed_tester

            get_speed_tester().cancel_current_test()
        except Exception:
            pass
        self.query_one("#network-speed-cancel", Button).disabled = True
        self._network_log(f"[yellow]{t('network.speed_cancelling')}[/]")

    @work(thread=True, exclusive=True)
    def _run_speed_test_once(self, *, prepared: bool = False) -> None:
        try:
            from monitor.speed_tester import get_speed_tester

            tester = get_speed_tester()
            result = tester.run_once(prepared=prepared)
            snapshot = tester.get_stats_snapshot()
            self.call_from_thread(self._finish_speed_test, result, snapshot, None)
        except Exception as exc:
            self.call_from_thread(self._finish_speed_test, None, {}, str(exc))

    def _finish_speed_test(self, result, snapshot: dict, error: str | None) -> None:
        self._speed_test_active = False
        try:
            self.query_one("#network-speed-start", Button).disabled = False
            self.query_one("#network-speed-cancel", Button).disabled = True
        except Exception:
            pass
        self._render_speed_table(snapshot)
        if result is not None:
            self._network_log(
                f"[green]{t('network.speed_finished', provider=result.provider_name)}[/]"
            )
        else:
            detail = error or snapshot.get("last_error") or t("network.speed_failed")
            self._network_log(f"[yellow]{detail}[/]")

    def _export_network_report(self) -> None:
        if self._network_history is None or not self._network_history.snapshot():
            self.notify(t("stalker.export_no_data"), severity="warning")
            return
        self._network_log(f"[cyan]{t('network.export_started')}[/]")
        self._run_network_export()

    @work(thread=True, exclusive=True)
    def _run_network_export(self) -> None:
        try:
            paths = self._network_history.export_bundle(
                include_full_ips=bool(
                    self._network_config.get("include_full_ip_exports", False)
                )
            )
            self.call_from_thread(self._finish_network_export, paths, None)
        except Exception as exc:
            self.call_from_thread(self._finish_network_export, None, str(exc))

    def _finish_network_export(self, paths, error: str | None) -> None:
        if error:
            message = t("network.export_failed", error=error)
            self._network_log(f"[red]{message}[/]")
            self.notify(message, severity="error")
            return
        csv_path, pdf_path = paths
        message = t("network.export_finished", csv=str(csv_path), pdf=str(pdf_path))
        self._network_log(f"[green]{message}[/]")
        self.notify(message)

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
        if "settings" in self._hydrated_tabs:
            self.query_one("#settings-status", RichRenderable).update(
                build_settings_status_table(recording, language)
            )
        if "docker" in self._hydrated_tabs:
            self.query_one("#cleanup-summary", RichRenderable).update(
                build_cleanup_status_panel(get_cleanup_steps())
            )

    def _write_dashboard_log(self, message) -> None:
        self.query_one("#dashboard-log", RichLog).write(message)


def run_textual_app() -> None:
    """Run the Textual app."""
    VareduraTextualApp().run()
