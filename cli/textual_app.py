"""Textual application shell for Varedura."""

from __future__ import annotations

import datetime
import threading
from concurrent.futures import ThreadPoolExecutor

from rich.console import Console
from rich.panel import Panel
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

from cli.richlog import DailyLogWriter
from cli.ui_shared import (
    CLEANUP_STEPS,
    build_cleanup_status_panel,
    build_dashboard_summary,
    build_scanner_tables,
    build_settings_status_table,
    build_tool_option,
    get_cleanup_steps,
    is_mcp_configured,
    load_recording_pref,
    run_cleanup_steps,
    save_cleanup_steps,
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


def _cleanup_checkbox_id(step_key: str) -> str:
    return f"cleanup-{step_key.replace('_', '-')}"


class RichRenderable(Static):
    """Static widget that displays Rich renderables."""


class VareduraTextualApp(App[str | None]):
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
    #activity-card,
    #cleanup-summary,
    #settings-status,
    #scanner-rich-summary {
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

    .button-row {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
    }

    .button-row Button {
        margin-right: 1;
    }

    #cleanup-checks {
        height: 14;
        border: solid $primary;
        padding: 0 1;
        margin-bottom: 1;
    }

    #cleanup-progress,
    #scanner-progress {
        height: 1;
        margin-bottom: 1;
    }

    DataTable {
        height: 1fr;
    }

    #scanner-controls {
        height: auto;
        margin-bottom: 1;
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
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "toggle_dark", "Dark", show=True),
        Binding("s", "show_settings", "Settings", show=True),
        Binding("r", "run_scanner", "Scan", show=True),
        Binding("escape", "dashboard", "Dashboard", show=True),
    ]

    TOOL_IDS = ("network", "docker", "scanner", "settings", "lmarena")

    def __init__(self) -> None:
        super().__init__()
        self.cleanup_running = False
        self.scanner_running = False
        self.network_running = False
        self._network_stop = threading.Event()
        self._network_tick = 0
        self._net_local_stats = None
        self._net_external_stats = None
        self._net_pool: ThreadPoolExecutor | None = None

    def compose(self) -> ComposeResult:
        self.title = "Varedura"
        self.sub_title = t("menu.subtitle")
        yield Header(show_clock=True)
        with TabbedContent(initial="dashboard", id="main-tabs"):
            with TabPane(t("textual.tab_dashboard"), id="dashboard"):
                yield from self._compose_dashboard()
            with TabPane(t("textual.tab_cleanup"), id="docker"):
                yield from self._compose_cleanup()
            with TabPane(t("textual.tab_scanner"), id="scanner"):
                yield from self._compose_scanner()
            with TabPane(t("textual.tab_network"), id="network"):
                yield from self._compose_network()
            with TabPane(t("textual.tab_settings"), id="settings"):
                yield from self._compose_settings()
        yield Footer()

    def _compose_dashboard(self) -> ComposeResult:
        with Horizontal(id="dashboard-grid", classes="pane"):
            with Vertical(id="dashboard-left"):
                yield RichRenderable(
                    build_dashboard_summary(load_recording_pref(), get_language()),
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
                    Option(Text(""), disabled=True),
                    Option(
                        build_tool_option(t("menu.option_settings"), t("menu.desc_settings"), "magenta"),
                        id="settings",
                    ),
                    Option(
                        build_tool_option("LMArena", t("menu.starting_lmarena"), "blue"),
                        id="lmarena",
                    ),
                    id="tool-menu",
                )
            with Vertical(id="dashboard-right"):
                yield RichRenderable(
                    Panel(Text(t("textual.ready"), style="green"), border_style="green"),
                    id="activity-card",
                )
                yield RichLog(id="dashboard-log", highlight=True, markup=True, wrap=True)

    def _compose_cleanup(self) -> ComposeResult:
        steps = get_cleanup_steps()
        with VerticalScroll(classes="pane"):
            yield Label(t("cleanup_prefs.title"), classes="section-title")
            yield RichRenderable(build_cleanup_status_panel(steps), id="cleanup-summary")
            with VerticalScroll(id="cleanup-checks"):
                for key, label_key, _default in CLEANUP_STEPS:
                    yield Checkbox(t(label_key), value=steps.get(key, False), id=_cleanup_checkbox_id(key))
            with Horizontal(classes="button-row"):
                yield Button(t("textual.cleanup_run"), id="run-cleanup", variant="primary")
                yield Button(t("textual.cleanup_save"), id="save-cleanup")
            yield Label(t("textual.ready"), id="cleanup-status")
            yield ProgressBar(total=100, id="cleanup-progress")
            yield RichLog(id="cleanup-log", highlight=True, markup=True, wrap=True)

    def _compose_scanner(self) -> ComposeResult:
        with Vertical(classes="pane"):
            with Horizontal(id="scanner-controls"):
                yield Button(t("textual.scanner_run"), id="run-scanner", variant="primary")
                yield Label(t("textual.scanner_hint"), id="scanner-status")
            yield ProgressBar(total=100, id="scanner-progress")
            with TabbedContent(initial="tcp-tab", id="scanner-tabs"):
                with TabPane(t("textual.scanner_tcp"), id="tcp-tab"):
                    yield DataTable(id="tcp-table")
                with TabPane(t("textual.scanner_connections"), id="connections-tab"):
                    yield DataTable(id="connections-table")
                with TabPane(t("textual.scanner_rich"), id="rich-tab"):
                    yield RichRenderable(
                        Panel(Text(t("textual.scanner_empty"), style="dim"), border_style="blue"),
                        id="scanner-rich-summary",
                    )

    def _compose_network(self) -> ComposeResult:
        with Vertical(classes="pane", id="network-pane"):
            with Horizontal(id="network-controls"):
                yield Button(t("textual.network_start"), id="network-start", variant="primary")
                yield Button(t("textual.network_stop"), id="network-stop", disabled=True)
                yield Button(t("textual.network_export"), id="network-export")
                yield Label(t("textual.network_idle"), id="network-status")
            with Horizontal(id="network-cards"):
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
            with Horizontal(classes="button-row"):
                yield Button(t("textual.settings_save"), id="save-settings", variant="primary")
                yield Button(t("mcp.option"), id="toggle-mcp")
            yield Label(
                t("mcp.status_on") if is_mcp_configured() else t("mcp.status_off"),
                id="mcp-status",
            )

    def on_mount(self) -> None:
        self._setup_scanner_tables()
        self._setup_network_tables()
        self.query_one("#tool-menu", OptionList).focus()
        self._write_dashboard_log(t("textual.ready"))

    def action_show_settings(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "settings"

    def action_dashboard(self) -> None:
        self.query_one("#main-tabs", TabbedContent).active = "dashboard"

    def action_run_scanner(self) -> None:
        self._start_scanner()

    @on(OptionList.OptionSelected, "#tool-menu")
    def on_tool_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = str(event.option_id or "")
        if option_id in {"network", "docker", "scanner", "settings"}:
            self.query_one("#main-tabs", TabbedContent).active = option_id
        elif option_id == "lmarena":
            self._write_dashboard_log(t("menu.starting_lmarena"))
            self.notify(t("textual.lmarena_legacy"))

    @on(TabbedContent.TabActivated, "#main-tabs")
    def on_main_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        if event.pane.id == "network" and not self.network_running:
            self._start_network()

    def on_unmount(self) -> None:
        self._network_stop.set()

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
        elif button_id == "run-scanner":
            self._start_scanner()
        elif button_id == "network-start":
            self._start_network()
        elif button_id == "network-stop":
            self._stop_network()
        elif button_id == "network-export":
            self._export_network_report()

    def _save_settings(self) -> None:
        recording = self.query_one("#recording-switch", Switch).value
        selected_language = self.query_one("#language-select", Select).value
        save_recording_pref(bool(recording))
        if isinstance(selected_language, str):
            set_language(selected_language)
        self._refresh_status_renderables()
        self.notify(t("textual.settings_saved"))
        self._write_dashboard_log(t("textual.settings_saved"))

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
            success, failures = run_cleanup_steps(step_keys, rich_console, progress)
            self.call_from_thread(self._finish_cleanup, success, failures)
        except Exception as exc:
            self.call_from_thread(self._finish_cleanup, False, [str(exc)])
        finally:
            writer.close()
            self.call_from_thread(self._set_cleanup_running, False)

    def _set_cleanup_running(self, running: bool) -> None:
        self.cleanup_running = running
        self.query_one("#run-cleanup", Button).disabled = running
        self.query_one("#save-cleanup", Button).disabled = running

    def _write_cleanup_log(self, line: str) -> None:
        self.query_one("#cleanup-log", RichLog).write(line)

    def _update_cleanup_progress(self, completed: int, total: int, label: str) -> None:
        bar = self.query_one("#cleanup-progress", ProgressBar)
        bar.total = max(total, 1)
        bar.progress = min(completed, max(total, 1))
        self.query_one("#cleanup-status", Label).update(label)

    def _finish_cleanup(self, success: bool, failures: list[str]) -> None:
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

    def _start_scanner(self) -> None:
        if self.scanner_running:
            return
        self._run_scanner_worker()

    @work(thread=True, exclusive=True)
    def _run_scanner_worker(self) -> None:
        self.call_from_thread(self._set_scanner_running, True)
        try:
            from monitor.port_scanner import run_full_scan

            state = run_full_scan()
            self.call_from_thread(self._render_scan_state, state)
        except Exception as exc:
            self.call_from_thread(self._scanner_failed, exc)
        finally:
            self.call_from_thread(self._set_scanner_running, False)

    def _set_scanner_running(self, running: bool) -> None:
        self.scanner_running = running
        self.query_one("#run-scanner", Button).disabled = running
        self.query_one("#scanner-status", Label).update(
            t("scanner.scanning") if running else t("textual.scanner_hint")
        )
        progress = self.query_one("#scanner-progress", ProgressBar)
        progress.total = 100
        progress.progress = 35 if running else 100

    def _scanner_failed(self, exc: Exception) -> None:
        message = t("menu.error_during_scan", error=str(exc))
        self.query_one("#scanner-status", Label).update(message)
        self.notify(message, severity="error")

    def _setup_scanner_tables(self) -> None:
        tcp_table = self.query_one("#tcp-table", DataTable)
        tcp_table.cursor_type = "row"
        tcp_table.add_columns(t("scanner.port"), t("scanner.process"), t("scanner.address"))

        conn_table = self.query_one("#connections-table", DataTable)
        conn_table.cursor_type = "row"
        conn_table.add_columns(t("scanner.process"), t("scanner.connections"), t("scanner.ram_mb"))

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
        ports_table.add_columns(t("scanner.port"), t("scanner.process"), t("scanner.address"))

        procs_table = self.query_one("#network-procs-table", DataTable)
        procs_table.cursor_type = "row"
        procs_table.add_columns(
            t("stalker.process_col"), t("stalker.connections_col"), t("stalker.pid_col")
        )

    def _render_scan_state(self, state) -> None:
        tcp_table = self.query_one("#tcp-table", DataTable)
        tcp_table.clear(columns=True)
        tcp_table.add_columns(t("scanner.port"), t("scanner.process"), t("scanner.address"))
        for port in state.listening_tcp[:50]:
            tcp_table.add_row(str(port.porta), port.processo, port.endereco)

        conn_table = self.query_one("#connections-table", DataTable)
        conn_table.clear(columns=True)
        conn_table.add_columns(t("scanner.process"), t("scanner.connections"), t("scanner.ram_mb"))
        for proc in state.top_connections:
            ram_str = f"{proc.memoria_mb:.1f}" if proc.memoria_mb > 0 else "N/A"
            conn_table.add_row(proc.nome, str(proc.conexoes), ram_str)

        tcp_rich, conn_rich, summary = build_scanner_tables(state)
        self.query_one("#scanner-rich-summary", RichRenderable).update(
            Panel(tcp_rich, title=t("textual.scanner_tcp"), border_style="cyan")
        )
        self._write_dashboard_log(summary)
        self._write_dashboard_log(conn_rich)
        self.query_one("#scanner-status", Label).update(t("textual.scanner_done"))
        self.notify(t("textual.scanner_done"))

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
                do_scan = self._network_tick % stalker_config.port_scan_interval == 0
                f_scan = pool.submit(run_full_scan) if do_scan else None

                local_ms = self._future_result(f_local)
                ext_ms = self._future_result(f_ext)
                procs = self._future_result(f_procs) or []
                scan_state = self._future_result(f_scan) if f_scan is not None else None

                # Agregação single-threaded (evita corrida no deque do PingStats).
                self._net_local_stats.add(local_ms)
                self._net_external_stats.add(ext_ms)
                stalker_mod.local_stats.add(local_ms)
                stalker_mod.external_stats.add(ext_ms)
                now = datetime.datetime.now()
                if stalker_mod.test_session_start is None:
                    stalker_mod.test_session_start = now
                stalker_mod.full_ping_history.append((now, local_ms, ext_ms))

                try:
                    speed_snapshot = get_speed_tester().get_stats_snapshot()
                except Exception:
                    speed_snapshot = {}

                log_lines = self._build_network_alerts(
                    local_ms,
                    ext_ms,
                    stalker_config.lag_threshold_ms,
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
        self, local_ms, ext_ms, procs, scan_state, speed_snapshot, log_lines
    ) -> None:
        threshold = 100
        try:
            from monitor.stalker import config as stalker_config

            threshold = stalker_config.lag_threshold_ms
        except Exception:
            pass

        self._render_ping_card("gateway", local_ms, self._net_local_stats, threshold)
        self._render_ping_card("external", ext_ms, self._net_external_stats, threshold)

        if scan_state is not None:
            ports_table = self.query_one("#network-ports-table", DataTable)
            ports_table.clear(columns=True)
            ports_table.add_columns(
                t("scanner.port"), t("scanner.process"), t("scanner.address")
            )
            for port in scan_state.listening_tcp[:50]:
                ports_table.add_row(str(port.porta), port.processo, port.endereco)

        procs_table = self.query_one("#network-procs-table", DataTable)
        procs_table.clear(columns=True)
        procs_table.add_columns(
            t("stalker.process_col"), t("stalker.connections_col"), t("stalker.pid_col")
        )
        for pid, name, raw in procs:
            conns = raw // (1024 * 1024)
            procs_table.add_row(name or t("stalker.unknown_process"), str(conns), str(pid))

        self._render_speed_table(speed_snapshot or {})

        log = self.query_one("#network-log", RichLog)
        for line in log_lines:
            log.write(line)

    def _render_ping_card(self, prefix: str, ms, stats, threshold: int) -> None:
        digits = self.query_one(f"#{prefix}-digits", Digits)
        spark = self.query_one(f"#{prefix}-spark", Sparkline)
        digits.update("--" if ms is None else f"{ms:.0f}")
        spark.data = [v if v is not None else 0.0 for v in stats.history]

        if stats.min_ms is not None:
            stats_text = t(
                "textual.network_card_stats",
                min=f"{stats.min_ms:.0f}",
                avg=f"{stats.avg_ms:.0f}",
                max=f"{stats.max_ms:.0f}",
            )
        else:
            stats_text = t("textual.network_card_stats", min="--", avg="--", max="--")
        self.query_one(f"#{prefix}-stats", Label).update(stats_text)

        cls = self._ping_status_class(ms, threshold)
        for widget in (digits, spark):
            widget.remove_class("ping-ok", "ping-warn", "ping-bad", "ping-timeout")
            widget.add_class(cls)

    def _render_speed_table(self, snapshot: dict) -> None:
        table = self.query_one("#network-speed-table", DataTable)
        table.clear(columns=True)
        table.add_columns(
            t("stalker.speed_provider"),
            t("stalker.speed_download"),
            t("stalker.speed_upload"),
            t("stalker.speed_ping"),
        )
        results = snapshot.get("results_by_provider", {})
        for provider, result in results.items():
            try:
                down = f"{float(result.download_mbps):.0f} Mbps"
                up = f"{float(result.upload_mbps):.0f} Mbps"
                ping = f"{float(result.ping_ms):.0f} ms"
            except (ValueError, TypeError, AttributeError):
                continue
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
        self.query_one("#dashboard-summary", RichRenderable).update(
            build_dashboard_summary(recording, language)
        )
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
