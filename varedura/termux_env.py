"""Termux/Android environment detection, tool discovery, telemetry and API helpers.

All top-level imports are 100% Python stdlib with zero I/O at import time so
the CLI startup stays lazy on every platform.
"""

from __future__ import annotations

from dataclasses import dataclass
import getpass
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys

_VALID_MODES = frozenset({"suspend", "suspend_pause", "background", "action"})

_SHORTCUT_ALIASES: dict[str, tuple[str, ...]] = {
    "1_monitor_claro": ("claro-monitor",),
    "monitor_claro": ("claro-monitor",),
    "2_auditar_zerorating": ("claro-audit",),
    "auditar_zerorating": ("claro-audit",),
    "3_scanner_rede": ("netscan", "vernet"),
    "scanner_rede": ("netscan", "vernet"),
    "4_centro_controle": ("m35-center",),
    "centro_controle": ("m35-center",),
}

_REDUNDANT_BODY_TOKENS: dict[str, tuple[str, ...]] = {
    "claro-monitor": ("claro-monitor", "claro_monitor.py"),
    "claro-audit": ("claro-audit", "claro_audit.py"),
    "m35-center": ("m35-center", "m35_tui.py"),
    "netscan": ("netscan",),
    "vernet": ("vernet",),
    "portscan": ("portscan",),
    "packetcap": ("packetcap",),
    "painel-web": ("painel-web",),
}


@dataclass
class TermuxTool:
    """Discoverable native or user-defined Termux tool."""

    id: str
    label: str
    command: tuple[str, ...]
    category: str
    mode: str  # "suspend" | "suspend_pause" | "background" | "action"
    description: str = ""
    source: str = "builtin"
    needs_arg: bool = False
    arg_placeholder: str = ""


@dataclass
class AndroidTelemetry:
    """Snapshot of Android/Termux device battery, network, memory and session."""

    battery_pct: int | None = None
    battery_status: str = ""
    battery_temp_c: float | None = None
    wifi_ip: str = ""
    mobile_ip: str = ""
    rx_bytes: int = 0
    tx_bytes: int = 0
    mobile_rx_bytes: int = 0
    mobile_tx_bytes: int = 0
    mem_used_mb: float = 0.0
    mem_total_mb: float = 0.0
    uptime_str: str = ""
    user: str = ""
    has_root: bool = False


@dataclass
class TermuxService:
    """Status descriptor for a local Termux background service."""

    id: str
    label: str
    active: bool
    available: bool = True
    detail: str = ""


def is_termux() -> bool:
    """Return True when running inside Termux (or forced via VAREDURA_TERMUX_MODE)."""
    return (
        "TERMUX_VERSION" in os.environ
        or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
        or os.environ.get("VAREDURA_TERMUX_MODE") == "1"
    )


def is_android() -> bool:
    """Return True when running on Android/Termux."""
    return is_termux() or "ANDROID_ROOT" in os.environ


def get_termux_prefix() -> Path:
    """Return the Termux $PREFIX path (defaults to standard Termux prefix)."""
    prefix = os.environ.get("PREFIX") or "/data/data/com.termux/files/usr"
    return Path(prefix)


def has_docker() -> bool:
    """Return True if the docker CLI binary is present in PATH."""
    return shutil.which("docker") is not None


def should_show_docker_tab() -> bool:
    """Show Docker tab on desktop always; on Android only if docker or override exists."""
    if not is_android():
        return True
    return has_docker() or os.environ.get("VAREDURA_SHOW_DOCKER") == "1"


def has_root() -> bool:
    """Return True if su or tsu is available."""
    return bool(shutil.which("su") or shutil.which("tsu"))


def has_claro_suite() -> bool:
    """Return True if ~/.claro_suite directory exists."""
    return (Path.home() / ".claro_suite").is_dir()


def _safe_resolve(path_str: str) -> str:
    try:
        return str(Path(path_str).resolve())
    except OSError:
        return path_str


def _is_redundant_shortcut(path: Path, discovered_ids: set[str]) -> bool:
    stem_norm = path.stem.lower()
    mapped = _SHORTCUT_ALIASES.get(stem_norm)
    if mapped and any(tool_id in discovered_ids for tool_id in mapped):
        return True

    try:
        snippet = path.read_text(encoding="utf-8", errors="ignore")[:4096].lower()
    except OSError:
        return False

    for tool_id, tokens in _REDUNDANT_BODY_TOKENS.items():
        if tool_id in discovered_ids and any(token in snippet for token in tokens):
            return True
    return False


def _load_custom_termux_tools() -> list[TermuxTool]:
    custom_path = Path.home() / ".varedura_termux_tools.json"
    if not custom_path.is_file():
        return []
    try:
        raw = json.loads(custom_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return []
    if not isinstance(raw, list):
        return []

    tools: list[TermuxTool] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        tool_id = str(entry.get("id") or "").strip()
        label = str(entry.get("label") or "").strip()
        raw_cmd = entry.get("command")
        if isinstance(raw_cmd, str):
            try:
                cmd = tuple(shlex.split(raw_cmd))
            except ValueError:
                cmd = ()
        elif isinstance(raw_cmd, list):
            cmd = tuple(str(part) for part in raw_cmd if str(part).strip())
        else:
            cmd = ()

        if not tool_id or not label or not cmd:
            continue

        mode = str(entry.get("mode") or "suspend_pause").strip()
        if mode not in _VALID_MODES:
            mode = "suspend_pause"
        category = str(entry.get("category") or "custom").strip() or "custom"
        description = str(entry.get("description") or "").strip()
        needs_arg = bool(entry.get("needs_arg", False))
        arg_placeholder = str(entry.get("arg_placeholder") or "").strip()

        tools.append(
            TermuxTool(
                id=tool_id,
                label=label,
                command=cmd,
                category=category,
                mode=mode,
                description=description,
                source="custom",
                needs_arg=needs_arg,
                arg_placeholder=arg_placeholder,
            )
        )
    return tools


def discover_termux_tools() -> list[TermuxTool]:
    """Discover installed Termux builtins, Claro Suite tools, shortcuts and custom tools."""
    tools: list[TermuxTool] = []
    seen_ids: set[str] = set()
    seen_targets: set[str] = set()

    def _register(tool: TermuxTool, resolved_target: str | None = None) -> None:
        if tool.id in seen_ids:
            return
        if resolved_target and resolved_target in seen_targets:
            return
        seen_ids.add(tool.id)
        if resolved_target:
            seen_targets.add(resolved_target)
        tools.append(tool)

    if micro_path := shutil.which("micro"):
        _register(
            TermuxTool(
                id="micro",
                label="micro",
                command=(micro_path,),
                category="editor",
                mode="suspend",
                description="Terminal text editor",
            ),
            _safe_resolve(micro_path),
        )

    if btop_path := shutil.which("btop"):
        if has_root() and (sudo_path := shutil.which("sudo")):
            cmd: tuple[str, ...] = (
                sudo_path,
                "env",
                "LANG=en_US.UTF-8",
                "TERM=xterm-256color",
                btop_path,
            )
        else:
            cmd = (btop_path,)
        _register(
            TermuxTool(
                id="btop",
                label="btop",
                command=cmd,
                category="system",
                mode="suspend",
                description="System resource monitor",
            ),
            _safe_resolve(btop_path),
        )

    builtin_specs: list[tuple[str, str, str, str, str, bool, str]] = [
        ("vernet", "vernet", "network", "suspend", "Network scanner", False, ""),
        ("netscan", "netscan", "network", "suspend", "LAN scanner", False, ""),
        (
            "portscan",
            "portscan",
            "network",
            "suspend_pause",
            "TCP/UDP port scanner",
            True,
            "192.168.1.1",
        ),
        (
            "packetcap",
            "packetcap",
            "network",
            "suspend_pause",
            "Packet capture",
            False,
            "",
        ),
        (
            "vt-status",
            "vt-status",
            "security",
            "suspend_pause",
            "VirusTotal status",
            False,
            "",
        ),
        (
            "vt-scan",
            "vt-scan",
            "security",
            "suspend_pause",
            "VirusTotal scan",
            True,
            "file / URL / hash",
        ),
    ]
    for tool_id, binary, category, mode, desc, needs_arg, placeholder in builtin_specs:
        if exe := shutil.which(binary):
            _register(
                TermuxTool(
                    id=tool_id,
                    label=binary,
                    command=(exe,),
                    category=category,
                    mode=mode,
                    description=desc,
                    needs_arg=needs_arg,
                    arg_placeholder=placeholder,
                ),
                _safe_resolve(exe),
            )

    for web_name in ("painel-web", "WEB"):
        if web_exe := shutil.which(web_name):
            _register(
                TermuxTool(
                    id=web_name.lower(),
                    label=web_name,
                    command=(web_exe,),
                    category="system",
                    mode="background",
                    description="Web dashboard server",
                ),
                _safe_resolve(web_exe),
            )

    claro_dir = Path.home() / ".claro_suite"
    claro_specs: list[tuple[str, str, str, str, str]] = [
        ("claro-monitor", "claro-monitor", "claro_monitor.py", "suspend", "Claro Zero-Rating monitor"),
        ("claro-audit", "claro-audit", "claro_audit.py", "suspend_pause", "Claro Zero-Rating audit"),
        ("m35-center", "m35-center", "m35_tui.py", "suspend", "M35 Control Center"),
    ]
    for tool_id, cmd_name, script_name, mode, desc in claro_specs:
        exe = shutil.which(cmd_name)
        script_path = claro_dir / script_name
        if exe:
            _register(
                TermuxTool(
                    id=tool_id,
                    label=cmd_name,
                    command=(exe,),
                    category="claro",
                    mode=mode,
                    description=desc,
                    source="claro_suite",
                ),
                _safe_resolve(exe),
            )
        elif script_path.is_file():
            _register(
                TermuxTool(
                    id=tool_id,
                    label=cmd_name,
                    command=(sys.executable, str(script_path)),
                    category="claro",
                    mode=mode,
                    description=desc,
                    source="claro_suite",
                ),
                _safe_resolve(str(script_path)),
            )

    shortcut_dirs = [
        Path.home() / ".shortcuts",
        Path.home() / ".shortcuts" / "tasks",
    ]
    for directory in shortcut_dirs:
        if not directory.is_dir():
            continue
        try:
            entries = sorted(directory.iterdir(), key=lambda p: p.name.casefold())
        except OSError:
            continue
        for entry in entries:
            if (
                entry.name.startswith(".")
                or entry.name.endswith("~")
                or entry.suffix.lower() == ".bak"
                or not entry.is_file()
            ):
                continue
            if not os.access(entry, os.X_OK):
                continue
            if _is_redundant_shortcut(entry, seen_ids):
                continue
            resolved = _safe_resolve(str(entry))
            cmd = (
                (sys.executable, str(entry))
                if entry.suffix.lower() == ".py"
                else (str(entry),)
            )
            prefix = "task:" if directory.name == "tasks" else ""
            _register(
                TermuxTool(
                    id=f"shortcut:{prefix}{entry.stem}",
                    label=entry.stem.replace("_", " "),
                    command=cmd,
                    category="shortcuts",
                    mode="suspend_pause",
                    description=str(entry),
                    source="shortcuts",
                ),
                resolved,
            )

    for custom_tool in _load_custom_termux_tools():
        if custom_tool.id in seen_ids:
            tools = [t for t in tools if t.id != custom_tool.id]
            seen_ids.discard(custom_tool.id)
        _register(custom_tool)

    return tools


def _read_text_optional(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def _collect_battery(telemetry: AndroidTelemetry) -> None:
    base = Path("/sys/class/power_supply/battery")
    cap_raw = _read_text_optional(base / "capacity")
    status_raw = _read_text_optional(base / "status")
    temp_raw = _read_text_optional(base / "temp")

    if cap_raw is not None:
        try:
            telemetry.battery_pct = int(cap_raw.strip())
        except ValueError:
            pass
    if status_raw and status_raw.strip():
        telemetry.battery_status = status_raw.strip()
    if temp_raw is not None:
        try:
            telemetry.battery_temp_c = round(int(temp_raw.strip()) / 10.0, 1)
        except ValueError:
            pass

    if telemetry.battery_pct is None and (exe := shutil.which("termux-battery-status")):
        try:
            proc = subprocess.run(
                [exe],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=2,
            )
            if proc.returncode == 0 and proc.stdout.strip():
                payload = json.loads(proc.stdout)
                if isinstance(payload, dict):
                    if payload.get("percentage") is not None:
                        telemetry.battery_pct = int(payload["percentage"])
                    if payload.get("status"):
                        telemetry.battery_status = str(payload["status"])
                    if payload.get("temperature") is not None:
                        telemetry.battery_temp_c = round(
                            float(payload["temperature"]), 1
                        )
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError):
            pass


def read_mobile_data_bytes() -> int | None:
    """Total RX+TX de dados móveis desde o boot, ou None se indisponível."""
    if not Path("/proc/net/dev").exists():
        return None
    telemetry = AndroidTelemetry()
    _collect_proc_net_dev(telemetry)
    return telemetry.mobile_rx_bytes + telemetry.mobile_tx_bytes


def _collect_proc_net_dev(telemetry: AndroidTelemetry) -> None:
    raw = _read_text_optional(Path("/proc/net/dev"))
    if not raw:
        return

    wlan_rx = 0
    wlan_tx = 0
    found_wlan0 = False
    for line in raw.splitlines():
        if ":" not in line:
            continue
        iface_part, stats_part = line.split(":", 1)
        iface = iface_part.strip()
        fields = stats_part.split()
        if len(fields) < 9:
            continue
        try:
            rx = int(fields[0])
            tx = int(fields[8])
        except ValueError:
            continue

        if iface == "wlan0":
            telemetry.rx_bytes = rx
            telemetry.tx_bytes = tx
            found_wlan0 = True
        elif iface.startswith("wlan"):
            wlan_rx += rx
            wlan_tx += tx
        elif iface.startswith(("rmnet", "ccmni")):
            telemetry.mobile_rx_bytes += rx
            telemetry.mobile_tx_bytes += tx

    if not found_wlan0 and (wlan_rx or wlan_tx):
        telemetry.rx_bytes = wlan_rx
        telemetry.tx_bytes = wlan_tx


def _collect_ips(telemetry: AndroidTelemetry) -> None:
    if ip_exe := shutil.which("ip"):
        try:
            proc = subprocess.run(
                [ip_exe, "-4", "-o", "addr", "show"],
                capture_output=True,
                text=True,
                errors="replace",
                timeout=2,
            )
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    match = re.search(
                        r"^\d+:\s+(\S+)\s+inet\s+(\d{1,3}(?:\.\d{1,3}){3})/",
                        line.strip(),
                    )
                    if not match:
                        continue
                    iface, addr = match.group(1), match.group(2)
                    if iface.startswith("wlan") and not telemetry.wifi_ip:
                        telemetry.wifi_ip = addr
                    elif (
                        iface.startswith("rmnet") or iface.startswith("ccmni")
                    ) and not telemetry.mobile_ip:
                        telemetry.mobile_ip = addr
        except (OSError, subprocess.SubprocessError):
            pass

    if telemetry.wifi_ip and telemetry.mobile_ip:
        return

    try:
        import psutil  # lazy import only inside telemetry helper

        addrs = psutil.net_if_addrs()
        for iface, entries in addrs.items():
            for entry in entries:
                if entry.family != socket.AF_INET:
                    continue
                addr = (entry.address or "").split("%", 1)[0]
                if not addr or addr.startswith("127."):
                    continue
                if iface.startswith("wlan") and not telemetry.wifi_ip:
                    telemetry.wifi_ip = addr
                elif (
                    iface.startswith("rmnet") or iface.startswith("ccmni")
                ) and not telemetry.mobile_ip:
                    telemetry.mobile_ip = addr
    except (ImportError, OSError, RuntimeError):
        pass

    if not telemetry.wifi_ip and not is_android():
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("1.1.1.1", 80))
                local_ip = sock.getsockname()[0]
                if local_ip and not local_ip.startswith("127."):
                    telemetry.wifi_ip = local_ip
        except OSError:
            pass


def _collect_memory(telemetry: AndroidTelemetry) -> None:
    raw = _read_text_optional(Path("/proc/meminfo"))
    if raw:
        values_kb: dict[str, int] = {}
        for line in raw.splitlines():
            if ":" not in line:
                continue
            key, rest = line.split(":", 1)
            parts = rest.split()
            if parts and parts[0].isdigit():
                values_kb[key.strip()] = int(parts[0])
        total_kb = values_kb.get("MemTotal", 0)
        avail_kb = values_kb.get(
            "MemAvailable",
            values_kb.get("MemFree", 0)
            + values_kb.get("Buffers", 0)
            + values_kb.get("Cached", 0),
        )
        if total_kb > 0:
            telemetry.mem_total_mb = round(total_kb / 1024.0, 1)
            telemetry.mem_used_mb = round(max(0, total_kb - avail_kb) / 1024.0, 1)
            return

    try:
        import psutil

        vm = psutil.virtual_memory()
        telemetry.mem_total_mb = round(vm.total / (1024.0 * 1024.0), 1)
        telemetry.mem_used_mb = round(vm.used / (1024.0 * 1024.0), 1)
    except (ImportError, OSError, RuntimeError):
        pass


def _format_uptime(seconds: float) -> str:
    total = max(0, int(seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    if days > 0:
        return f"{days}d {hours:02d}h {minutes:02d}m"
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    return f"{minutes}m"


def _collect_uptime(telemetry: AndroidTelemetry) -> None:
    raw = _read_text_optional(Path("/proc/uptime"))
    if not raw:
        return
    parts = raw.split()
    if not parts:
        return
    try:
        telemetry.uptime_str = _format_uptime(float(parts[0]))
    except ValueError:
        pass


def collect_android_telemetry() -> AndroidTelemetry:
    """Safely collect device battery, network traffic, IPs, memory and uptime."""
    try:
        user = getpass.getuser()
    except Exception:
        user = os.environ.get("USER", "")

    telemetry = AndroidTelemetry(user=user, has_root=has_root())
    _collect_battery(telemetry)
    _collect_proc_net_dev(telemetry)
    _collect_ips(telemetry)
    _collect_memory(telemetry)
    _collect_uptime(telemetry)
    return telemetry


def _pid_file_alive(pid_path: Path) -> bool:
    raw = _read_text_optional(pid_path)
    if not raw or not raw.isdigit():
        return False
    pid = int(raw)
    if pid <= 0:
        return False
    proc_dir = Path(f"/proc/{pid}")
    if Path("/proc").is_dir():
        return proc_dir.exists()
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _pgrep_active(pattern: str, *, full: bool = False) -> bool:
    pgrep = shutil.which("pgrep")
    if not pgrep:
        return False
    cmd = [pgrep, "-f" if full else "-x", pattern]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=2,
        )
        return proc.returncode == 0 and bool(proc.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        return False


def list_termux_services() -> list[TermuxService]:
    """Return status descriptors for sshd, crond, wakelock and claro_daemon."""
    prefix = get_termux_prefix()
    var_run = prefix / "var" / "run"

    sshd_avail = shutil.which("sshd") is not None
    sshd_active = _pid_file_alive(var_run / "sshd.pid") or _pgrep_active("sshd")

    crond_avail = shutil.which("crond") is not None
    crond_active = _pid_file_alive(var_run / "crond.pid") or _pgrep_active("crond")

    wake_avail = bool(
        shutil.which("termux-wake-lock") or shutil.which("termux-wake-unlock")
    )
    wake_lock_file = var_run / "termux-wake-lock"
    wake_active = wake_lock_file.exists() or _pgrep_active(
        "termux-wake-lock", full=True
    )

    claro_script = Path.home() / ".claro_suite" / "claro_monitor.py"
    claro_avail = claro_script.is_file()
    claro_pid_file = Path.home() / ".claro_suite" / "claro_monitor.pid"
    claro_active = claro_avail and (
        _pid_file_alive(claro_pid_file) or _pgrep_active("claro_monitor.py", full=True)
    )

    return [
        TermuxService(
            id="sshd",
            label="OpenSSH (sshd)",
            active=sshd_active,
            available=sshd_avail,
            detail="port 8022",
        ),
        TermuxService(
            id="crond",
            label="Cron daemon (crond)",
            active=crond_active,
            available=crond_avail,
        ),
        TermuxService(
            id="wakelock",
            label="Termux Wake Lock",
            active=wake_active,
            available=wake_avail,
        ),
        TermuxService(
            id="claro_daemon",
            label="Claro Monitor Daemon",
            active=claro_active,
            available=claro_avail,
            detail=str(claro_script) if claro_avail else "",
        ),
    ]


def _run_service_cmd(cmd: list[str], timeout: float = 5.0) -> tuple[bool, str]:
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        msg = (proc.stdout or proc.stderr or "").strip()
        return proc.returncode == 0, msg or ("OK" if proc.returncode == 0 else "Failed")
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


def toggle_termux_service(service_id: str, enable: bool) -> tuple[bool, str]:
    """Start or stop one of the supported Termux services."""
    if service_id == "sshd":
        if enable:
            exe = shutil.which("sshd")
            if not exe:
                return False, "sshd not found"
            return _run_service_cmd([exe])
        pkill = shutil.which("pkill")
        if pkill:
            return _run_service_cmd([pkill, "-x", "sshd"])
        pid_file = get_termux_prefix() / "var" / "run" / "sshd.pid"
        raw = _read_text_optional(pid_file)
        if raw and raw.isdigit():
            try:
                os.kill(int(raw), signal.SIGTERM)
                return True, "sshd stopped"
            except OSError as exc:
                return False, str(exc)
        return False, "pkill not found"

    if service_id == "crond":
        if enable:
            exe = shutil.which("crond")
            if not exe:
                return False, "crond not found"
            return _run_service_cmd([exe])
        pkill = shutil.which("pkill")
        if pkill:
            return _run_service_cmd([pkill, "-x", "crond"])
        pid_file = get_termux_prefix() / "var" / "run" / "crond.pid"
        raw = _read_text_optional(pid_file)
        if raw and raw.isdigit():
            try:
                os.kill(int(raw), signal.SIGTERM)
                return True, "crond stopped"
            except OSError as exc:
                return False, str(exc)
        return False, "pkill not found"

    if service_id == "wakelock":
        binary = "termux-wake-lock" if enable else "termux-wake-unlock"
        exe = shutil.which(binary)
        if not exe:
            return False, f"{binary} not found"
        return _run_service_cmd([exe])

    if service_id == "claro_daemon":
        claro_dir = Path.home() / ".claro_suite"
        script = claro_dir / "claro_monitor.py"
        pid_file = claro_dir / "claro_monitor.pid"
        if enable:
            if not script.is_file():
                return False, "claro_monitor.py not found"
            try:
                proc = subprocess.Popen(
                    [sys.executable, str(script)],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                try:
                    pid_file.write_text(str(proc.pid), encoding="utf-8")
                except OSError:
                    pass
                return True, f"claro_daemon started (pid {proc.pid})"
            except OSError as exc:
                return False, str(exc)
        raw_pid = _read_text_optional(pid_file)
        if raw_pid and raw_pid.isdigit():
            try:
                os.kill(int(raw_pid), signal.SIGTERM)
                pid_file.unlink(missing_ok=True)
                return True, "claro_daemon stopped"
            except OSError:
                pass
        if pkill := shutil.which("pkill"):
            ok, msg = _run_service_cmd([pkill, "-f", "claro_monitor.py"])
            if ok:
                pid_file.unlink(missing_ok=True)
            return ok, msg
        return False, "Cannot stop claro_daemon"

    return False, f"Unknown service: {service_id}"


def send_termux_notification(
    title: str,
    content: str,
    *,
    notif_id: str = "varedura",
    vibrate: bool = False,
) -> bool:
    """Send an Android notification via Termux:API if available."""
    exe = shutil.which("termux-notification")
    if not exe:
        return False
    cmd = [exe, "--id", notif_id, "--title", title, "--content", content]
    if vibrate:
        cmd.extend(["--vibrate", "200"])
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=5,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def share_file(path: str | Path, *, title: str = "") -> bool:
    """Share a file via Termux:API (falling back to termux-open)."""
    target = str(path)
    if exe := shutil.which("termux-share"):
        cmd = [exe, "-a", "send"]
        if title:
            cmd.extend(["-t", title])
        cmd.append(target)
        try:
            proc = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
            if proc.returncode == 0:
                return True
        except (OSError, subprocess.SubprocessError):
            pass

    if open_exe := shutil.which("termux-open"):
        try:
            proc = subprocess.run(
                [open_exe, target],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
            return proc.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False
    return False


def open_file_or_url(target: str) -> bool:
    """Open a file path or URL via termux-open, xdg-open, or os.startfile on Windows."""
    if exe := shutil.which("termux-open"):
        try:
            proc = subprocess.run(
                [exe, target],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
            return proc.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    if exe := shutil.which("xdg-open"):
        try:
            proc = subprocess.run(
                [exe, target],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                errors="replace",
                timeout=10,
            )
            return proc.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return False

    if os.name == "nt" and hasattr(os, "startfile"):
        try:
            os.startfile(target)  # type: ignore[attr-defined]
            return True
        except OSError:
            return False
    return False


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard using termux-clipboard-set."""
    exe = shutil.which("termux-clipboard-set")
    if not exe:
        return False
    try:
        proc = subprocess.run(
            [exe],
            input=text,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=5,
        )
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


# ---------------------------------------------------------------------------
# Teclas extras do Termux (extra-keys) e digitação por diálogo nativo
# ---------------------------------------------------------------------------
# Tecla acrescentada à barra do usuário só enquanto o Varedura roda: com o
# mouse do terminal ativo (toda TUI), tocar na tela não abre mais o teclado.
VAREDURA_KEYBOARD_KEY = {"key": "KEYBOARD", "display": "\u2328"}
_EXTRA_KEYS_LINE = re.compile(r"^(\s*extra-keys\s*=\s*)(.+?)\s*$")
_MACRO_COMMAND = re.compile(r"^\n([A-Za-z0-9][\w .:/-]{0,60})\n$")


def termux_properties_path() -> Path:
    return Path.home() / ".termux" / "termux.properties"


def _read_extra_keys(path: Path) -> tuple[list[str], int, list] | None:
    """Devolve (linhas, índice da linha extra-keys, layout) ou None."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for index, line in enumerate(lines):
        if line.lstrip().startswith("#"):
            continue
        match = _EXTRA_KEYS_LINE.match(line)
        if not match:
            continue
        try:
            layout = json.loads(match.group(2))
        except ValueError:
            return None  # formato multi-linha/estilo Java: não mexemos
        if isinstance(layout, list) and all(isinstance(row, list) for row in layout):
            return lines, index, layout
        return None
    return None


def extra_key_macros(path: Path | None = None) -> tuple[str, ...]:
    """Comandos de shell digitados pelas teclas extras (macros ``"\\ncmd\\n"``)."""
    parsed = _read_extra_keys(path or termux_properties_path())
    if parsed is None:
        return ()
    found: list[str] = []

    def visit(node: object) -> None:
        if isinstance(node, dict):
            macro = node.get("macro")
            if isinstance(macro, str):
                match = _MACRO_COMMAND.match(macro)
                if match and match.group(1).strip() not in found:
                    found.append(match.group(1).strip())
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(parsed[2])
    return tuple(found)


def set_keyboard_key(
    enabled: bool, path: Path | None = None, *, reload: bool = True
) -> bool:
    """Acrescenta/remove a tecla de teclado na barra extra-keys do usuário.

    Só altera uma linha ``extra-keys = [...]`` já existente em JSON de uma
    linha; o restante do arquivo é preservado.  Devolve True se gravou.
    """
    target = path or termux_properties_path()
    parsed = _read_extra_keys(target)
    if parsed is None:
        return False
    lines, index, layout = parsed
    cleaned = [
        [key for key in row if key != VAREDURA_KEYBOARD_KEY] for row in layout
    ]
    if enabled and cleaned:
        cleaned[-1] = [dict(VAREDURA_KEYBOARD_KEY), *cleaned[-1]]
    if cleaned == layout:
        return False
    prefix = _EXTRA_KEYS_LINE.match(lines[index]).group(1)
    lines[index] = prefix + json.dumps(cleaned)
    try:
        tmp = target.with_name(target.name + ".varedura-tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(tmp, target)
    except OSError:
        return False
    if reload and shutil.which("termux-reload-settings"):
        try:
            subprocess.run(
                ["termux-reload-settings"],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    return True


def has_native_dialog() -> bool:
    return bool(shutil.which("termux-dialog"))


def native_text_dialog(
    title: str,
    hint: str = "",
    *,
    numeric: bool = False,
    password: bool = False,
    timeout: float = 300.0,
) -> str | None:
    """Pede um texto pelo diálogo nativo do Android (Termux:API).

    Devolve o texto confirmado ou None se o usuário cancelou/indisponível.
    """
    cmd = ["termux-dialog", "text", "-t", title[:80] or "Varedura"]
    if hint:
        cmd += ["-i", hint[:120]]
    if numeric:
        cmd.append("-n")
    if password:
        cmd.append("-p")
    try:
        proc = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
        payload = json.loads(proc.stdout or "{}")
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("code") != -1:
        return None
    return str(payload.get("text") or "")


def toggle_keyboard_page() -> tuple[bool, str]:
    """Run ~/.claro_suite/termux_page_switcher.py when present."""
    script = Path.home() / ".claro_suite" / "termux_page_switcher.py"
    if not script.is_file():
        return False, "termux_page_switcher.py not found"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=10,
        )
        output = (proc.stdout or proc.stderr or "").strip()
        return proc.returncode == 0, output or ("OK" if proc.returncode == 0 else "Failed")
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)


__all__ = [
    "AndroidTelemetry",
    "TermuxService",
    "TermuxTool",
    "collect_android_telemetry",
    "copy_to_clipboard",
    "discover_termux_tools",
    "get_termux_prefix",
    "has_claro_suite",
    "has_docker",
    "has_root",
    "is_android",
    "is_termux",
    "list_termux_services",
    "open_file_or_url",
    "send_termux_notification",
    "share_file",
    "should_show_docker_tab",
    "toggle_keyboard_page",
    "extra_key_macros",
    "set_keyboard_key",
    "has_native_dialog",
    "native_text_dialog",
    "termux_properties_path",
    "VAREDURA_KEYBOARD_KEY",
    "toggle_termux_service",
]
