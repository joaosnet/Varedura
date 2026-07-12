"""Shared state and Rich renderables for the Varedura interfaces."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import re
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

# Cleanup steps grouped into sections for a clearer Docker tab.
CLEANUP_GROUPS = [
    (
        "cleanup_prefs.group_docker",
        "🐳",
        ["containers", "images", "volumes", "networks", "builder"],
    ),
    ("cleanup_prefs.group_wsl", "🐧", ["stop_docker", "wsl_sparse", "compact_vhdx"]),
    ("cleanup_prefs.group_system", "🧹", ["temp_files", "recycle_bin"]),
]
# "Quick clean" preset: lightweight Docker prune only (no WSL/compaction).
QUICK_CLEANUP_KEYS = ["containers", "images", "volumes", "networks", "builder"]


def cleanup_label_key(step_key: str) -> str:
    """Return the i18n label key for a cleanup step key."""
    for key, label_key, _default in CLEANUP_STEPS:
        if key == step_key:
            return label_key
    return step_key


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


# Network preferences are intentionally plain data.  Keeping migration here
# avoids importing the monitor (and its optional network providers) while the
# first Textual frame is being composed.
NETWORK_SCHEMA_VERSION = 3
LEGACY_EXTERNAL_DEFAULT = "ec2.sa-east-1.amazonaws.com"

# Known legacy values can be migrated without importing the target catalogue.
_PRESET_HOST_IDS = {
    "1.1.1.1": "cloudflare_ipv4",
    "2606:4700:4700::1111": "cloudflare_ipv6",
    "8.8.8.8": "google_ipv4",
    "2001:4860:4860::8888": "google_ipv6",
    "9.9.9.9": "quad9_ipv4",
    "2620:fe::fe": "quad9_ipv6",
    "br1.api.riotgames.com": "lol_br1_api",
}

NETWORK_DEFAULTS: dict[str, object] = {
    "gateway_ip": "",  # empty -> autodetect on first run
    # ``external_host`` remains a read-only compatibility view for one release.
    "external_host": "",
    "lag_threshold_ms": 100,
    "contracted_down": 500.0,
    "contracted_up": 100.0,
    "network_schema_version": NETWORK_SCHEMA_VERSION,
    "target_onboarding_completed": False,
    "selected_target_ids": [],
    "primary_target_id": "",
    "custom_targets": [],
    "league_auto_detect": True,
    "include_full_ip_exports": False,
    "app_ca_file": "",
}


def _valid_legacy_host(value: str) -> bool:
    """Cheap, resolution-free migration guard kept outside monitor imports."""
    host = value.strip()
    if (
        not host
        or len(host) > 253
        or host.startswith("-")
        or any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in host)
        or any(token in host for token in ("://", "/", "?", "#", "@", "\\", "*"))
    ):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if ":" in host:
            return False
        try:
            ascii_host = host.rstrip(".").encode("idna").decode("ascii")
        except UnicodeError:
            return False
        labels = ascii_host.split(".")
        return bool(labels) and all(
            label
            and len(label) <= 63
            and re.fullmatch(r"[A-Za-z0-9-]+", label)
            and not label.startswith("-")
            and not label.endswith("-")
            for label in labels
        )
    return not (address.is_unspecified or address.is_multicast)


def _verified_stored_app_ca(value: object) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    try:
        path = Path(candidate).expanduser().resolve(strict=True)
        store = (Path.home() / ".varedura" / "certs").resolve()
        if (
            not path.is_file()
            or path.parent != store
            or path.suffix.casefold() != ".pem"
            or not re.fullmatch(r"[0-9a-f]{64}", path.stem)
            or path.stat().st_size > 5 * 1024 * 1024
        ):
            return ""
        material = path.read_bytes()
    except OSError:
        return ""
    return str(path) if hashlib.sha256(material).hexdigest() == path.stem else ""


def load_network_config() -> dict:
    """Load and migrate network preferences without writing to disk.

    Schema-v1/v2 installations used a single ``external_host``.  An explicit
    host is preserved as the sole primary target; the old speculative AWS
    default deliberately returns to onboarding so a new installation never
    starts external traffic without consent.
    """
    saved = load_prefs().get("network", {})
    config = dict(NETWORK_DEFAULTS)
    config["selected_target_ids"] = []
    config["custom_targets"] = []
    if isinstance(saved, dict):
        config.update({k: saved[k] for k in NETWORK_DEFAULTS if k in saved})

        try:
            schema = int(saved.get("network_schema_version", 0) or 0)
        except (TypeError, ValueError):
            schema = 0
        if schema < NETWORK_SCHEMA_VERSION:
            legacy_host = str(saved.get("external_host", "") or "").strip()
            if (
                legacy_host
                and legacy_host.lower() != LEGACY_EXTERNAL_DEFAULT
                and _valid_legacy_host(legacy_host)
            ):
                preset_id = _PRESET_HOST_IDS.get(legacy_host.lower())
                if preset_id:
                    config["selected_target_ids"] = [preset_id]
                    config["primary_target_id"] = preset_id
                else:
                    digest = hashlib.sha256(
                        legacy_host.lower().encode("utf-8")
                    ).hexdigest()[:12]
                    custom_id = f"custom_{digest}"
                    config["custom_targets"] = [
                        {"id": custom_id, "label": legacy_host, "host": legacy_host}
                    ]
                    config["selected_target_ids"] = [custom_id]
                    config["primary_target_id"] = custom_id
                config["target_onboarding_completed"] = True
            else:
                config["selected_target_ids"] = []
                config["primary_target_id"] = ""
                config["target_onboarding_completed"] = False
            config["network_schema_version"] = NETWORK_SCHEMA_VERSION

    selected = config.get("selected_target_ids")
    if not isinstance(selected, list):
        selected = []
    selected = [str(value) for value in selected if str(value).strip()][:5]
    config["selected_target_ids"] = list(dict.fromkeys(selected))

    custom = config.get("custom_targets")
    if not isinstance(custom, list):
        custom = []
    config["custom_targets"] = [item for item in custom if isinstance(item, dict)][:5]

    primary = str(config.get("primary_target_id", "") or "")
    if primary not in config["selected_target_ids"]:
        primary = (
            config["selected_target_ids"][0] if config["selected_target_ids"] else ""
        )
    config["primary_target_id"] = primary
    config["target_onboarding_completed"] = bool(
        config.get("target_onboarding_completed") and config["selected_target_ids"]
    )
    config["league_auto_detect"] = bool(config.get("league_auto_detect", True))
    config["include_full_ip_exports"] = bool(
        config.get("include_full_ip_exports", False)
    )
    config["app_ca_file"] = _verified_stored_app_ca(config.get("app_ca_file", ""))
    try:
        threshold = int(config.get("lag_threshold_ms", 100))
    except (TypeError, ValueError):
        threshold = 100
    config["lag_threshold_ms"] = threshold if threshold > 0 else 100
    for key, fallback in (("contracted_down", 500.0), ("contracted_up", 100.0)):
        try:
            value = float(config.get(key, fallback))
        except (TypeError, ValueError):
            value = fallback
        config[key] = value if value >= 0 else fallback

    # Compatibility for code that still expects the old scalar field.
    if primary:
        preset_host = next(
            (
                host
                for host, target_id in _PRESET_HOST_IDS.items()
                if target_id == primary
            ),
            "",
        )
        custom_host = next(
            (
                str(item.get("host", ""))
                for item in config["custom_targets"]
                if str(item.get("id", "")) == primary
            ),
            "",
        )
        config["external_host"] = preset_host or custom_host
    else:
        config["external_host"] = ""
    return config


def save_network_config(config: dict) -> None:
    """Persist schema-v3 network configuration atomically with other prefs."""
    data = load_prefs()
    current = data.get("network", {})
    if not isinstance(current, dict):
        current = {}
    current.update({k: config[k] for k in NETWORK_DEFAULTS if k in config})
    current["network_schema_version"] = NETWORK_SCHEMA_VERSION
    # v3 is authoritative; keep no stale scalar target on disk.
    current.pop("external_host", None)
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
        status = (
            f"[green]{t('cleanup_prefs.on')}[/]"
            if enabled
            else f"[dim]{t('cleanup_prefs.off')}[/]"
        )
        table.add_row(str(index), f"{icon} {status}", t(label_key))
    return table


def build_cleanup_status_panel(steps: dict[str, bool] | None = None) -> Panel:
    """Build a compact cleanup preference summary."""
    return Panel(
        Text(cleanup_summary(steps), style="cyan"),
        title=t("settings.option_cleanup"),
        border_style="cyan",
    )


def _add_common_status_rows(
    table: Table, recording_enabled: bool, current_language: str
) -> None:
    """Add the rows shared by the settings and dashboard status panels.

    Keeps recording / language / cleanup / MCP rows defined in one place so the
    two panels never drift apart.
    """
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


def build_settings_status_table(
    recording_enabled: bool, current_language: str
) -> Table:
    """Build the shared settings status table."""
    table = Table(box=box.SIMPLE, show_header=True, expand=True)
    table.add_column(t("settings.current_status"), style="bold cyan")
    table.add_column("", style="white")
    _add_common_status_rows(table, recording_enabled, current_language)
    return table


def _fmt_ping(ms: float | None, threshold: int) -> Text:
    """Format a latency value with a status color (dashboard glance)."""
    if ms is None:
        # No data / idle -> neutral dash rather than an alarming TIMEOUT.
        return Text("—", style="dim")
    style = (
        "green"
        if ms <= threshold
        else ("yellow" if ms <= threshold * 1.5 else "bold red")
    )
    return Text(f"{ms:.0f} ms", style=style)


def _fmt_data_mb(mb: float) -> str:
    """Format a megabyte count, scaling to GB once it gets large."""
    if mb >= 1024:
        return f"{mb / 1024:.1f} GB"
    return f"{mb:.0f} MB"


def _fmt_memory(percent: float, used_gb: float, total_gb: float) -> Text:
    """Format RAM usage with a status color (green/yellow/red)."""
    style = "green" if percent < 70 else ("yellow" if percent < 90 else "bold red")
    return Text(f"{percent:.0f}% · {used_gb:.1f}/{total_gb:.1f} GB", style=style)


def _fmt_traffic(sent_mb: float, recv_mb: float) -> Text:
    """Format cumulative network traffic (sent/received since boot)."""
    return Text(f"↑ {_fmt_data_mb(sent_mb)}   ↓ {_fmt_data_mb(recv_mb)}", style="white")


def build_dashboard_status(
    recording_enabled: bool,
    current_language: str,
    network: dict | None = None,
    system: dict | None = None,
) -> Panel:
    """Build a live at-a-glance status overview for the dashboard.

    ``system`` is an optional dict from ``port_scanner.get_system_network_stats``
    (memory + cumulative traffic) so the dashboard stays live even before the
    full network monitor is started.
    """
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
    table.add_row(
        t("dashboard.gateway", ip=gateway),
        _fmt_ping(network.get("local_ms"), threshold),
    )
    table.add_row(t("dashboard.external"), _fmt_ping(network.get("ext_ms"), threshold))

    if system:
        mem_pct = system.get("memoria_percent")
        if mem_pct is not None:
            table.add_row(
                t("dashboard.memory"),
                _fmt_memory(
                    float(mem_pct),
                    float(system.get("memoria_usada_gb", 0.0)),
                    float(system.get("memoria_total_gb", 0.0)),
                ),
            )
        sent = system.get("bytes_enviados_mb")
        recv = system.get("bytes_recebidos_mb")
        if sent is not None and recv is not None:
            table.add_row(
                t("dashboard.traffic"), _fmt_traffic(float(sent), float(recv))
            )

    _add_common_status_rows(table, recording_enabled, current_language)
    return Panel(table, title=t("menu.title"), border_style="blue")


def format_duration(seconds: float) -> str:
    """Format a duration in seconds as a compact human string (e.g. 1h05m).

    Shared helper for both the dashboard records panel and the network health
    card (streak), so the formatting lives in exactly one place.
    """
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    if seconds < 3600:
        return f"{seconds // 60}m{seconds % 60:02d}s"
    return f"{seconds // 3600}h{(seconds % 3600) // 60:02d}m"


def build_achievements_row(state) -> Panel:
    """Build the achievements badge wall from a GameState."""
    from cli.gamification import ACHIEVEMENTS

    table = Table.grid(padding=(0, 1), expand=True)
    table.add_column(justify="left", no_wrap=True)
    table.add_column(ratio=1)
    for ach in ACHIEVEMENTS:
        unlocked = ach.id in state.achievements
        icon = ach.emoji if unlocked else "🔒"
        name_style = "bold green" if unlocked else "dim"
        name = Text(t(ach.name_key), style=name_style)
        if unlocked:
            name.append(f"  {t(ach.desc_key)}", style="dim")
        table.add_row(icon, name)

    unlocked_count = sum(1 for a in ACHIEVEMENTS if a.id in state.achievements)
    return Panel(
        table,
        title=t("game.achievements")
        + f"  [dim]{unlocked_count}/{len(ACHIEVEMENTS)}[/]",
        border_style="yellow",
    )


def build_records_panel(state) -> Panel:
    """Build the personal-bests panel from a GameState."""
    table = Table(box=box.SIMPLE, show_header=False, expand=True)
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="white")
    best_ping = f"{state.best_ping:.0f} ms" if state.best_ping else "—"
    best_down = f"{state.best_download:.0f} Mbps" if state.best_download else "—"
    table.add_row(t("game.rec_best_ping"), best_ping)
    table.add_row(t("game.rec_best_download"), best_down)
    table.add_row(t("game.rec_best_streak"), format_duration(state.best_streak_s))
    table.add_row(t("game.rec_space_freed"), f"{state.total_space_freed_gb:.1f} GB")
    return Panel(table, title=t("game.records"), border_style="magenta")


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
    conn_table.add_column(
        t("scanner.connections"), style="bold yellow", justify="center"
    )
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


def anatel_minimums() -> tuple[float, float]:
    """Return (min_download, min_upload) Mbps for ANATEL compliance.

    Single source of truth for the 80% (configurable) contracted-speed floor,
    shared by the health-score compliance check and the speed table coloring.
    """
    try:
        from monitor.speed_tester import speed_config

        factor = speed_config.percentual_minimo / 100
        return (
            speed_config.velocidade_contratada_down * factor,
            speed_config.velocidade_contratada_up * factor,
        )
    except Exception:
        return (0.0, 0.0)


def build_ports_summary(state) -> Text:
    """Lay-friendly one-line summary + legend for the network ports view."""
    from monitor.port_catalog import is_exposed

    tcp = list(getattr(state, "listening_tcp", []) or [])
    udp = list(getattr(state, "listening_udp", []) or [])
    exposed = sum(1 for p in tcp + udp if is_exposed(p.endereco))
    text = Text(
        t(
            "ports.summary",
            local=len(tcp) + len(udp),
            exposed=exposed,
            tcp=getattr(state, "total_tcp", len(tcp)),
            udp=getattr(state, "total_udp", len(udp)),
            time=getattr(state, "last_scan_time", "") or "--",
        ),
        style="bold cyan",
    )
    text.append("\n" + t("ports.legend"), style="dim")
    return text


def selected_cleanup_keys(steps: dict[str, bool] | None = None) -> list[str]:
    """Return enabled cleanup step keys in configured display order."""
    current = steps or get_cleanup_steps()
    return [
        key for key, _label_key, _default in CLEANUP_STEPS if current.get(key, False)
    ]


def run_cleanup_steps(
    step_keys: Iterable[str],
    console,
    progress_callback: CleanupProgressCallback | None = None,
) -> tuple[bool, list[str], float]:
    """Run selected cleanup steps and report coarse progress.

    Returns ``(success, failures, space_saved_gb)``.
    """
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

    space_saved = float(getattr(cleaner, "total_space_saved", 0) or 0)
    return not failures, failures, space_saved
