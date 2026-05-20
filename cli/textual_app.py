"""Textual application shell for Varedura."""

from __future__ import annotations

from typing import Callable

from rich.console import Console
from rich.panel import Panel
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
    Footer,
    Header,
    Label,
    OptionList,
    ProgressBar,
    RichLog,
    Select,
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


class ConfirmModal(ModalScreen[bool]):
    """Small reusable confirmation modal."""

    CSS = """
    ConfirmModal {
        align: center middle;
    }

    ConfirmModal > Container {
        width: 64;
        height: auto;
        border: thick $primary;
        background: $surface;
        padding: 1 2;
    }

    ConfirmModal Button {
        margin-right: 1;
    }
    """

    def __init__(self, title: str, message: str) -> None:
        super().__init__()
        self.modal_title = title
        self.message = message

    def compose(self) -> ComposeResult:
        with Container():
            yield Label(self.modal_title, classes="modal-title")
            yield Static(self.message, id="modal-message")
            with Horizontal(classes="button-row"):
                yield Button(t("textual.confirm"), id="confirm", variant="primary")
                yield Button(t("textual.cancel"), id="cancel")

    @on(Button.Pressed)
    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm")


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

    #modal-message {
        margin: 1 0;
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
        if option_id == "network":
            self.push_screen(
                ConfirmModal(t("menu.option_1"), t("textual.network_legacy_message")),
                self._handle_network_modal,
            )
        elif option_id in {"docker", "scanner", "settings"}:
            self.query_one("#main-tabs", TabbedContent).active = option_id
        elif option_id == "lmarena":
            self._write_dashboard_log(t("menu.starting_lmarena"))
            self.notify(t("textual.lmarena_legacy"))

    def _handle_network_modal(self, confirmed: bool | None) -> None:
        if confirmed:
            self.exit("network")

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


def run_textual_app(legacy_network_runner: Callable[[], None] | None = None) -> None:
    """Run the Textual app, temporarily handing off to legacy Network Stalker."""
    while True:
        result = VareduraTextualApp().run()
        if result == "network" and legacy_network_runner is not None:
            legacy_network_runner()
            continue
        return
