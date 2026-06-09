"""Shared state and Rich renderables for the Varedura interfaces."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Callable, Iterable

from rich import box
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from i18n import t

PREFS_FILE = Path.home() / ".varedura_prefs.json"
MCP_CONFIG_FILE = Path(".vscode") / "mcp.json"

CLEANUP_STEPS = [
    ("containers", "cleanup_prefs.step_containers", True),
    ("images", "cleanup_prefs.step_images", True),
    ("volumes", "cleanup_prefs.step_volumes", True),
    ("networks", "cleanup_prefs.step_networks", True),
    ("builder", "cleanup_prefs.step_builder", True),
    ("stop_docker", "cleanup_prefs.step_stop_docker", False),
    ("wsl_sparse", "cleanup_prefs.step_wsl_sparse", False),
    ("compact_vhdx", "cleanup_prefs.step_compact_vhdx", False),
    ("temp_files", "cleanup_prefs.step_temp_files", False),
    ("recycle_bin", "cleanup_prefs.step_recycle_bin", False),
]

STEP_WEIGHT = {
    "containers": 10,
    "images": 15,
    "volumes": 10,
    "networks": 5,
    "builder": 10,
    "stop_docker": 15,
    "wsl_sparse": 10,
    "compact_vhdx": 20,
    "temp_files": 10,
    "recycle_bin": 5,
}

CleanupProgressCallback = Callable[[int, int, str], None]


def load_prefs() -> dict:
    """Load all preferences from disk."""
    try:
        if PREFS_FILE.exists():
            return json.loads(PREFS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def save_prefs(data: dict) -> None:
    """Save preferences to disk."""
    try:
        PREFS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def load_recording_pref() -> bool:
    """Load recording preference from disk."""
    return bool(load_prefs().get("recording_enabled", True))


def save_recording_pref(enabled: bool) -> None:
    """Save recording preference to disk."""
    data = load_prefs()
    data["recording_enabled"] = enabled
    save_prefs(data)


# Default network monitor settings (mirror monitor.stalker.StalkerConfig /
# monitor.speed_tester.SpeedTestConfig so we don't import those heavy modules).
NETWORK_DEFAULTS: dict[str, object] = {
    "gateway_ip": "",  # empty -> autodetect on first run
    "external_host": "ec2.sa-east-1.amazonaws.com",
    "lag_threshold_ms": 100,
    "contracted_down": 500.0,
    "contracted_up": 100.0,
}


def load_network_config() -> dict:
    """Load the network monitor configuration, merged over defaults."""
    saved = load_prefs().get("network", {})
    config = dict(NETWORK_DEFAULTS)
    if isinstance(saved, dict):
        config.update({k: saved[k] for k in NETWORK_DEFAULTS if k in saved})
    return config


def save_network_config(config: dict) -> None:
    """Persist the network monitor configuration."""
    data = load_prefs()
    current = data.get("network", {})
    if not isinstance(current, dict):
        current = {}
    current.update({k: config[k] for k in NETWORK_DEFAULTS if k in config})
    data["network"] = current
    save_prefs(data)


def load_cleanup_steps() -> dict[str, bool] | None:
    """Load cleanup step preferences, if they were configured."""
    return load_prefs().get("cleanup_steps")


def save_cleanup_steps(steps: dict[str, bool]) -> None:
    """Save cleanup step preferences."""
    data = load_prefs()
    data["cleanup_steps"] = steps
    save_prefs(data)


def get_cleanup_steps() -> dict[str, bool]:
    """Get cleanup step preferences, falling back to defaults."""
    saved = load_cleanup_steps()
    if saved is not None:
        return saved
    return {key: default for key, _, default in CLEANUP_STEPS}


def cleanup_label(step_key: str) -> str:
    """Return the localized label for a cleanup step key."""
    for key, label_key, _default in CLEANUP_STEPS:
        if key == step_key:
            return t(label_key)
    return step_key


def cleanup_summary(steps: dict[str, bool] | None = None) -> str:
    """Return the localized cleanup enabled-count summary."""
    current = steps or get_cleanup_steps()
    enabled_count = sum(1 for value in current.values() if value)
    return t("cleanup_prefs.summary", count=enabled_count, total=len(CLEANUP_STEPS))


def is_mcp_configured() -> bool:
    """Check whether the workspace MCP server is configured."""
    try:
        if MCP_CONFIG_FILE.exists():
            data = json.loads(MCP_CONFIG_FILE.read_text(encoding="utf-8"))
            return "varedura" in data.get("servers", {})
    except Exception:
        pass
    return False


def toggle_mcp_config() -> list[tuple[str, str]]:
    """Toggle the workspace MCP server config and return styled messages."""
    messages: list[tuple[str, str]] = []
    try:
        if is_mcp_configured():
            data = json.loads(MCP_CONFIG_FILE.read_text(encoding="utf-8"))
            data.get("servers", {}).pop("varedura", None)
            if not data.get("servers"):
                MCP_CONFIG_FILE.unlink(missing_ok=True)
            else:
                MCP_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            messages.append(("yellow", t("mcp.removed")))
        else:
            messages.append(("cyan", t("mcp.installing")))
            MCP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {}
            if MCP_CONFIG_FILE.exists():
                try:
                    data = json.loads(MCP_CONFIG_FILE.read_text(encoding="utf-8"))
                except Exception:
                    data = {}

            data.setdefault("servers", {})
            data["servers"]["varedura"] = {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "python", "-m", "mcp_server"],
            }
            MCP_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

            messages.extend(
                [
                    ("green", t("mcp.installed")),
                    ("dim", t("mcp.config_path", path=str(MCP_CONFIG_FILE.resolve()))),
                    ("dim", t("mcp.usage_hint")),
                    ("dim", t("mcp.run_hint")),
                ]
            )
    except Exception as exc:
        messages.append(("red", t("mcp.error", error=str(exc))))
    return messages


def build_cleanup_steps_table(steps: dict[str, bool] | None = None) -> Table:
    """Build a Rich table with cleanup step state."""
    current = steps or get_cleanup_steps()
    table = Table(box=box.ROUNDED, expand=True, show_header=False)
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("", width=8)
    table.add_column("Step", style="white")

    for index, (key, label_key, _default) in enumerate(CLEANUP_STEPS, 1):
        enabled = current.get(key, False)
        icon = "[bold green]+[/]" if enabled else "[dim]-[/]"
        status = f"[green]{t('cleanup_prefs.on')}[/]" if enabled else f"[dim]{t('cleanup_prefs.off')}[/]"
        table.add_row(str(index), f"{icon} {status}", t(label_key))
    return table


def build_cleanup_status_panel(steps: dict[str, bool] | None = None) -> Panel:
    """Build a compact cleanup preference summary."""
    return Panel(
        Text(cleanup_summary(steps), style="cyan"),
        title=t("settings.option_cleanup"),
        border_style="cyan",
    )


def build_settings_status_table(recording_enabled: bool, current_language: str) -> Table:
    """Build the shared settings status table."""
    table = Table(box=box.SIMPLE, show_header=True, expand=True)
    table.add_column(t("settings.current_status"), style="bold cyan")
    table.add_column("", style="white")
    table.add_row(
        t("settings.option_rec"),
        f"{t('settings.rec_on') if recording_enabled else t('settings.rec_off')}",
    )
    table.add_row(t("settings.option_lang"), current_language)
    table.add_row(t("settings.option_cleanup"), cleanup_summary())
    table.add_row(
        t("mcp.option"),
        t("mcp.status_on") if is_mcp_configured() else t("mcp.status_off"),
    )
    return table


def build_dashboard_summary(recording_enabled: bool, current_language: str) -> Panel:
    """Build the dashboard overview as a Rich renderable."""
    status_table = build_settings_status_table(recording_enabled, current_language)
    return Panel(status_table, title=t("menu.title"), border_style="blue")


def _fmt_ping(ms: float | None, threshold: int) -> Text:
    """Format a latency value with a status color."""
    if ms is None:
        return Text(t("stalker.timeout"), style="bold red")
    style = "green" if ms <= threshold else ("yellow" if ms <= threshold * 1.5 else "bold red")
    return Text(f"{ms:.0f} ms", style=style)


def build_dashboard_status(
    recording_enabled: bool, current_language: str, network: dict | None = None
) -> Panel:
    """Build a live at-a-glance status overview for the dashboard."""
    network = network or {}
    threshold = int(network.get("lag_threshold_ms", 100))
    gateway = str(network.get("gateway_ip") or "—")
    running = bool(network.get("running"))

    table = Table(box=box.SIMPLE, show_header=False, expand=True)
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="white")

    table.add_row(
        t("dashboard.network"),
        Text(t("dashboard.net_running"), style="green")
        if running
        else Text(t("dashboard.net_idle"), style="dim"),
    )
    table.add_row(t("dashboard.gateway", ip=gateway), _fmt_ping(network.get("local_ms"), threshold))
    table.add_row(t("dashboard.external"), _fmt_ping(network.get("ext_ms"), threshold))
    table.add_row(
        t("settings.option_rec"),
        t("settings.rec_on") if recording_enabled else t("settings.rec_off"),
    )
    table.add_row(t("settings.option_lang"), current_language)
    table.add_row(t("settings.option_cleanup"), cleanup_summary())
    table.add_row(
        t("mcp.option"),
        t("mcp.status_on") if is_mcp_configured() else t("mcp.status_off"),
    )
    return Panel(table, title=t("menu.title"), border_style="blue")


def build_tool_option(title: str, description: str, accent: str = "cyan") -> Panel:
    """Build a Rich renderable suitable for a Textual OptionList option."""
    body = Group(Text(title, style=f"bold {accent}"), Text(description, style="dim"))
    return Panel(body, border_style=accent, padding=(0, 1), expand=True)


def build_scanner_tables(state) -> tuple[Table, Table, Panel]:
    """Build Rich scanner tables from a PortScannerState-like object."""
    tcp_table = Table(
        title=t("scanner.tcp_listening", count=state.total_tcp),
        border_style="cyan",
        expand=True,
    )
    tcp_table.add_column(t("scanner.port"), style="bold yellow", justify="center")
    tcp_table.add_column(t("scanner.process"), style="bold green")
    tcp_table.add_column(t("scanner.address"), style="dim")
    for port in state.listening_tcp[:15]:
        tcp_table.add_row(str(port.porta), port.processo, port.endereco)

    conn_table = Table(
        title=t("scanner.top_connections", count=state.total_established),
        border_style="green",
        expand=True,
    )
    conn_table.add_column(t("scanner.process"), style="bold cyan")
    conn_table.add_column(t("scanner.connections"), style="bold yellow", justify="center")
    conn_table.add_column(t("scanner.ram_mb"), style="dim", justify="right")
    for proc in state.top_connections:
        ram_str = f"{proc.memoria_mb:.1f}" if proc.memoria_mb > 0 else "N/A"
        conn_table.add_row(proc.nome, str(proc.conexoes), ram_str)

    summary = Panel(
        f"[bold green]{t('scanner.summary')}[/] "
        f"{t('scanner.summary_detail', tcp=state.total_tcp, udp=state.total_udp, established=state.total_established)}\n"
        f"{t('scanner.last_scan', time=state.last_scan_time)}",
        border_style="blue",
    )
    return tcp_table, conn_table, summary


def selected_cleanup_keys(steps: dict[str, bool] | None = None) -> list[str]:
    """Return enabled cleanup step keys in configured display order."""
    current = steps or get_cleanup_steps()
    return [key for key, _label_key, _default in CLEANUP_STEPS if current.get(key, False)]


def run_cleanup_steps(
    step_keys: Iterable[str],
    console,
    progress_callback: CleanupProgressCallback | None = None,
) -> tuple[bool, list[str]]:
    """Run selected cleanup steps and report coarse progress."""
    from docker_cleaner.core import WSLDockerCleaner

    selected = list(step_keys)
    cleaner = WSLDockerCleaner(console=console)
    cleaner.daily_log_writer = None

    step_methods = {
        "containers": lambda: cleaner.docker_cleanup(prune_only="containers"),
        "images": lambda: cleaner.docker_cleanup(prune_only="images"),
        "volumes": lambda: cleaner.docker_cleanup(prune_only="volumes"),
        "networks": lambda: cleaner.docker_cleanup(prune_only="networks"),
        "builder": lambda: cleaner.docker_cleanup(prune_only="builder"),
        "stop_docker": cleaner.stop_docker_wsl,
        "wsl_sparse": cleaner.configure_wsl_sparse,
        "compact_vhdx": cleaner.compact_vhdx_files,
        "temp_files": cleaner.cleanup_temp_files,
        "recycle_bin": cleaner.cleanup_recycle_bin,
    }

    total_weight = sum(STEP_WEIGHT.get(key, 10) for key in selected)
    completed = 0
    failures: list[str] = []

    if progress_callback:
        progress_callback(completed, total_weight, t("menu.starting_cleanup"))

    for key in selected:
        label = cleanup_label(key)
        if progress_callback:
            progress_callback(completed, total_weight, label)
        method = step_methods.get(key)
        if method:
            try:
                if method() is False:
                    failures.append(label)
            except Exception as exc:
                failures.append(label)
                console.print(f"[red]{label}: {exc}[/]")
        completed += STEP_WEIGHT.get(key, 10)
        if progress_callback:
            progress_callback(completed, total_weight, label)

    return not failures, failures
