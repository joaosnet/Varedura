"""Layered, policy-aware network diagnostics.

The module deliberately performs no network I/O at import time.  A diagnosis is
split into two phases: a local :class:`NetworkSnapshot` and bounded external
probes.  The latter respect explicit system proxies and refuse to bypass a PAC
configuration that this process cannot evaluate.

TLS verification is never disabled.  ``truststore.SSLContext`` is used when it
is installed so HTTPS probes honour the operating-system trust store (including
legitimate institutional CAs) without changing the global ``ssl`` module.
"""

from __future__ import annotations

import ipaddress
import json
import os
import platform
import queue
import re
import shutil
import signal
import socket
import ssl
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, TypeVar

import psutil


class NetworkState(StrEnum):
    """High-level connectivity state exposed to the user interface."""

    ONLINE = "online"
    ONLINE_MANAGED = "online_managed"
    LIMITED = "limited"
    LOCAL_ONLY = "local_only"
    CAPTIVE_PORTAL = "captive_portal"
    PROXY_AUTH_REQUIRED = "proxy_auth_required"
    POLICY_BLOCKED = "policy_blocked"
    TLS_POLICY_BLOCKED = "tls_policy_blocked"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class Confidence(StrEnum):
    CONFIRMED = "confirmed"
    LIKELY = "likely"
    POSSIBLE = "possible"


class ProbeKind(StrEnum):
    LINK = "link"
    ROUTE = "route"
    DNS = "dns"
    TCP = "tcp"
    CAPTIVE_PORTAL = "captive_portal"
    HTTPS = "https"
    ICMP = "icmp"


class ProbeStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


class FailureCause(StrEnum):
    NONE = "none"
    NO_ACTIVE_INTERFACE = "no_active_interface"
    APIPA_NO_DHCP_LEASE = "apipa_no_dhcp_lease"
    NO_DEFAULT_ROUTE = "no_default_route"
    DNS_RESOLUTION_FAILED = "dns_resolution_failed"
    TCP_CONNECT_FAILED = "tcp_connect_failed"
    PAC_PRESENT = "pac_present"
    PAC_UNAVAILABLE = "pac_unavailable"
    PROXY_AUTH_REQUIRED = "proxy_auth_required"
    CAPTIVE_PORTAL_DETECTED = "captive_portal_detected"
    TLS_CERT_UNTRUSTED = "tls_cert_untrusted"
    TLS_INTERCEPTION_SUSPECTED = "tls_interception_suspected"
    FORTIGATE_BLOCK_CERT = "fortigate_block_cert"
    POLICY_BLOCKED = "policy_blocked"
    VPN_ACTIVE = "vpn_active"
    ICMP_FILTERED_OR_UNSUPPORTED = "icmp_filtered_or_unsupported"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True, slots=True)
class NetworkInterface:
    name: str
    is_up: bool
    ipv4: tuple[str, ...] = ()
    ipv6: tuple[str, ...] = ()
    mac: str | None = None
    mtu: int = 0
    speed_mbps: int = 0
    is_loopback: bool = False
    is_virtual: bool = False
    service_name: str | None = None
    dhcp_enabled: bool | None = None
    stable_id: str | None = None
    connection_uuid: str | None = None


@dataclass(frozen=True, slots=True)
class ProxyConfiguration:
    """Credential-free proxy information safe to show and persist in reports."""

    proxies: tuple[tuple[str, str], ...] = ()
    pac_url: str | None = None
    auto_detect: bool = False
    credentials_redacted: bool = False

    @property
    def has_explicit_proxy(self) -> bool:
        return bool(self.proxies)

    @property
    def has_pac(self) -> bool:
        return bool(self.pac_url or self.auto_detect)

    def as_dict(self) -> dict[str, str]:
        return dict(self.proxies)


@dataclass(frozen=True, slots=True)
class NetworkSnapshot:
    captured_at: datetime
    platform: str
    interfaces: tuple[NetworkInterface, ...]
    active_interface: str | None
    default_gateway: str | None
    route_present: bool
    dns_servers: tuple[str, ...]
    proxy: ProxyConfiguration = field(default_factory=ProxyConfiguration)
    apipa: bool = False
    ipv6_only: bool = False
    vpn_active: bool = False
    fortinet_client_active: bool = False
    managed_network: bool = False
    dot1x_suspected: bool = False
    remote_session: bool = False
    command_errors: tuple[str, ...] = ()

    def age_seconds(self, now: datetime | None = None) -> float:
        current = now or datetime.now(timezone.utc)
        captured = self.captured_at
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        return max(0.0, (current - captured).total_seconds())

    @property
    def selected_interface(self) -> NetworkInterface | None:
        return next(
            (item for item in self.interfaces if item.name == self.active_interface),
            None,
        )


@dataclass(frozen=True, slots=True)
class ProbeResult:
    kind: ProbeKind
    status: ProbeStatus
    duration_ms: float
    cause: FailureCause = FailureCause.NONE
    message: str = ""
    target: str | None = None
    status_code: int | None = None
    details: Mapping[str, Any] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.status is ProbeStatus.SUCCESS


@dataclass(frozen=True, slots=True)
class Evidence:
    code: str
    message: str
    confidence: Confidence
    probe: ProbeKind | None = None
    details: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DiagnosisReport:
    state: NetworkState
    confidence: Confidence
    summary: str
    snapshot: NetworkSnapshot
    probes: tuple[ProbeResult, ...]
    evidence: tuple[Evidence, ...]
    started_at: datetime
    completed_at: datetime
    cancelled: bool = False
    timed_out: bool = False

    def age_seconds(self, now: datetime | None = None) -> float:
        current = now or datetime.now(timezone.utc)
        completed = self.completed_at
        if completed.tzinfo is None:
            completed = completed.replace(tzinfo=timezone.utc)
        return max(0.0, (current - completed).total_seconds())

    def probe(self, kind: ProbeKind) -> ProbeResult | None:
        return next((probe for probe in self.probes if probe.kind is kind), None)


@dataclass(frozen=True, slots=True)
class DiagnosticOptions:
    """Budgets and well-known endpoints for a bounded diagnosis."""

    overall_timeout: float = 10.0
    snapshot_timeout: float = 2.5
    per_probe_timeout: float = 1.8
    dns_host: str = "www.microsoft.com"
    tcp_host: str = "www.microsoft.com"
    tcp_port: int = 443
    captive_portal_url: str = "http://www.msftconnecttest.com/connecttest.txt"
    captive_expected_text: str = "Microsoft Connect Test"
    https_url: str = "https://www.microsoft.com/"
    icmp_target: str = "1.1.1.1"
    enable_icmp: bool = True
    ca_file: str | None = None

    def __post_init__(self) -> None:
        if self.overall_timeout <= 0 or self.snapshot_timeout <= 0:
            raise ValueError("diagnostic timeouts must be positive")
        if self.per_probe_timeout <= 0:
            raise ValueError("per_probe_timeout must be positive")
        if not 1 <= self.tcp_port <= 65535:
            raise ValueError("tcp_port must be between 1 and 65535")


@dataclass(frozen=True, slots=True)
class CommandResult:
    args: tuple[str, ...]
    returncode: int | None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    cancelled: bool = False
    duration_ms: float = 0.0


class CommandRunner(Protocol):
    def run(
        self,
        args: tuple[str, ...] | list[str],
        *,
        timeout: float,
        cancel_event: threading.Event | None = None,
    ) -> CommandResult: ...


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    if os.name != "nt":
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=0.5)
            return
        except (OSError, subprocess.TimeoutExpired):
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            return
    try:
        parent = psutil.Process(process.pid)
        descendants = parent.children(recursive=True)
        for child in descendants:
            try:
                child.terminate()
            except psutil.Error:
                pass
        process.terminate()
        _, alive = psutil.wait_procs(descendants, timeout=0.4)
        for child in alive:
            try:
                child.kill()
            except psutil.Error:
                pass
        process.wait(timeout=0.4)
    except (OSError, psutil.Error, subprocess.TimeoutExpired):
        try:
            process.kill()
        except OSError:
            pass


class SubprocessCommandRunner:
    """Cancellable, shell-free runner used only for read-only system probes."""

    def run(
        self,
        args: tuple[str, ...] | list[str],
        *,
        timeout: float,
        cancel_event: threading.Event | None = None,
    ) -> CommandResult:
        command = tuple(str(part) for part in args)
        started = time.monotonic()
        startupinfo = None
        creationflags = 0
        if platform.system().lower() == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                startupinfo=startupinfo,
                creationflags=creationflags,
                start_new_session=platform.system().lower() != "windows",
            )
        except (OSError, ValueError) as exc:
            return CommandResult(
                command,
                None,
                stderr=_redact_text(str(exc)),
                duration_ms=(time.monotonic() - started) * 1000,
            )

        deadline = started + timeout
        cancelled = False
        timed_out = False
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                _terminate_process(process)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                _terminate_process(process)
                break
            time.sleep(0.02)

        try:
            stdout, stderr = process.communicate(timeout=0.2)
        except subprocess.TimeoutExpired:
            _terminate_process(process)
            stdout, stderr = process.communicate()
        return CommandResult(
            command,
            process.returncode,
            _redact_text(stdout),
            _redact_text(stderr),
            timed_out,
            cancelled,
            (time.monotonic() - started) * 1000,
        )


_CREDENTIALS_IN_URL = re.compile(r"(?i)(https?://)[^\s/@:]+:[^\s/@]+@")
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_VIRTUAL_NAMES = re.compile(
    r"(?i)(loopback|virtual|vmware|vbox|hyper-v|docker|podman|wsl|bridge|veth|tap)"
)
_VPN_NAMES = re.compile(
    r"(?i)(vpn|wireguard|wg\d*|tun\d*|tap\d*|tailscale|zerotier|forti|anyconnect)"
)
_WIFI_NAMES = re.compile(r"(?i)(wi-?fi|wireless|wlan|airport|802\.11)")


def _redact_text(value: str | None) -> str:
    if not value:
        return ""
    redacted = _CREDENTIALS_IN_URL.sub(r"\1<credentials-redacted>@", value)
    return redacted[:16_384]


def _sanitize_proxy_url(value: str) -> tuple[str | None, bool]:
    raw = value.strip()
    if not raw or _CONTROL_CHARS.search(raw):
        return None, False
    candidate = raw if "://" in raw else f"http://{raw}"
    try:
        parsed = urllib.parse.urlsplit(candidate)
        hostname = parsed.hostname
        if not hostname:
            return None, False
        credentials = parsed.username is not None or parsed.password is not None
        host = f"[{hostname}]" if ":" in hostname else hostname
        port = f":{parsed.port}" if parsed.port else ""
        path = parsed.path.rstrip("/")
        return f"{parsed.scheme or 'http'}://{host}{port}{path}", credentials
    except (ValueError, UnicodeError):
        return None, False


def _sanitize_pac_url(value: str) -> tuple[str | None, bool]:
    raw = value.strip()
    if not raw or _CONTROL_CHARS.search(raw):
        return None, False
    try:
        parsed = urllib.parse.urlsplit(raw)
        if parsed.scheme == "file":
            if parsed.username is not None or parsed.password is not None:
                return None, True
            return urllib.parse.urlunsplit(
                ("file", parsed.netloc, parsed.path, "", "")
            ), False
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None, False
        credentials = parsed.username is not None or parsed.password is not None
        host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
        port = f":{parsed.port}" if parsed.port else ""
        return (
            urllib.parse.urlunsplit(
                (parsed.scheme, f"{host}{port}", parsed.path, parsed.query, "")
            ),
            credentials,
        )
    except (ValueError, UnicodeError):
        return None, False


T = TypeVar("T")


def _bounded_daemon_call(
    function: Callable[[], T],
    *,
    timeout: float,
    cancel_event: threading.Event | None,
) -> tuple[T | None, BaseException | None, bool, bool]:
    """Run a potentially blocking library call without blocking cancellation.

    Socket operations also receive their own timeout.  The daemon wrapper is a
    final guard for platform resolver APIs that occasionally ignore it.
    """

    result_queue: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            result_queue.put((True, function()))
        except BaseException as exc:  # returned to the caller, never swallowed
            result_queue.put((False, exc))

    worker = threading.Thread(target=invoke, daemon=True, name="network-probe")
    worker.start()
    deadline = time.monotonic() + timeout
    while True:
        if cancel_event is not None and cancel_event.is_set():
            return None, None, False, True
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return None, None, True, False
        try:
            ok, value = result_queue.get(timeout=min(0.025, remaining))
        except queue.Empty:
            continue
        if ok:
            return value, None, False, False
        return None, value, False, False


def _valid_ip(value: str) -> bool:
    try:
        ipaddress.ip_address(value.split("%", 1)[0])
        return True
    except ValueError:
        return False


def _read_dns_resolv_conf() -> tuple[str, ...]:
    try:
        lines = (
            Path("/etc/resolv.conf")
            .read_text(encoding="utf-8", errors="replace")
            .splitlines()
        )
    except OSError:
        return ()
    servers: list[str] = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 2 and parts[0].lower() == "nameserver":
            server = parts[1].split("%", 1)[0]
            if _valid_ip(server) and server not in servers:
                servers.append(server)
    return tuple(servers)


def _interface_addresses() -> tuple[NetworkInterface, ...]:
    try:
        address_map = psutil.net_if_addrs()
    except (OSError, RuntimeError):
        address_map = {}
    try:
        stats_map = psutil.net_if_stats()
    except (OSError, RuntimeError):
        stats_map = {}

    interfaces: list[NetworkInterface] = []
    for name in sorted(set(address_map) | set(stats_map), key=str.casefold):
        ipv4: list[str] = []
        ipv6: list[str] = []
        mac = None
        for address in address_map.get(name, ()):
            value = (address.address or "").split("%", 1)[0]
            if address.family == socket.AF_INET and _valid_ip(value):
                ipv4.append(value)
            elif address.family == socket.AF_INET6 and _valid_ip(value):
                ipv6.append(value)
            elif address.family == getattr(psutil, "AF_LINK", object()):
                mac = address.address or None
        stats = stats_map.get(name)
        loopback = (
            all(ipaddress.ip_address(value).is_loopback for value in (*ipv4, *ipv6))
            if ipv4 or ipv6
            else bool(re.search(r"(?i)^(lo|loopback)", name))
        )
        interfaces.append(
            NetworkInterface(
                name=name,
                is_up=bool(stats.isup) if stats is not None else False,
                ipv4=tuple(ipv4),
                ipv6=tuple(ipv6),
                mac=mac,
                mtu=int(stats.mtu) if stats is not None else 0,
                speed_mbps=int(stats.speed) if stats is not None else 0,
                is_loopback=loopback,
                is_virtual=bool(_VIRTUAL_NAMES.search(name)),
            )
        )
    return tuple(interfaces)


def _parse_route(
    system: str,
    output: str,
    interfaces: tuple[NetworkInterface, ...],
) -> tuple[str | None, str | None, bool]:
    gateway: str | None = None
    interface: str | None = None
    route_present = False
    if system == "windows":
        best_metric = float("inf")
        best_address = None
        for line in output.splitlines():
            parts = line.split()
            if len(parts) < 5 or parts[:2] != ["0.0.0.0", "0.0.0.0"]:
                continue
            if not _valid_ip(parts[2]) or not _valid_ip(parts[3]):
                continue
            try:
                metric = int(parts[4])
            except ValueError:
                metric = 0
            if metric < best_metric:
                gateway, best_address, best_metric = parts[2], parts[3], metric
                route_present = True
        if not route_present:
            for line in output.splitlines():
                parts = line.split()
                if "::/0" not in parts:
                    continue
                route_present = True
                prefix_index = parts.index("::/0")
                if prefix_index + 1 < len(parts) and _valid_ip(parts[prefix_index + 1]):
                    gateway = parts[prefix_index + 1].split("%", 1)[0]
                try:
                    interface_index = int(parts[0])
                except (ValueError, IndexError):
                    interface_index = -1
                for item in interfaces:
                    try:
                        if socket.if_nametoindex(item.name) == interface_index:
                            interface = item.name
                            break
                    except OSError:
                        continue
                break
        if best_address:
            interface = next(
                (item.name for item in interfaces if best_address in item.ipv4), None
            )
    elif system == "darwin":
        gateway_match = re.search(r"(?m)^\s*gateway:\s*(\S+)", output)
        interface_match = re.search(r"(?m)^\s*interface:\s*(\S+)", output)
        if gateway_match and _valid_ip(gateway_match.group(1)):
            gateway = gateway_match.group(1)
        if interface_match:
            interface = interface_match.group(1)
        route_present = bool(gateway or interface)
    else:
        defaults = [
            line for line in output.splitlines() if line.strip().startswith("default")
        ]

        def metric(line: str) -> int:
            found = re.search(r"\bmetric\s+(\d+)", line)
            return int(found.group(1)) if found else 0

        first = min(defaults, key=metric) if defaults else ""
        via = re.search(r"\bvia\s+(\S+)", first)
        dev = re.search(r"\bdev\s+(\S+)", first)
        if via and _valid_ip(via.group(1)):
            gateway = via.group(1)
        if dev:
            interface = dev.group(1)
        route_present = bool(first)
    return gateway, interface, route_present


def _default_route_command(system: str, *, ipv6: bool = False) -> tuple[str, ...]:
    if system == "windows":
        return (
            ("route.exe", "print", "-6", "::/0")
            if ipv6
            else ("route.exe", "print", "-4", "0.0.0.0")
        )
    if system == "darwin":
        return (
            ("route", "-n", "get", "-inet6", "default")
            if ipv6
            else ("route", "-n", "get", "default")
        )
    return (
        ("ip", "-6", "route", "show", "default")
        if ipv6
        else ("ip", "route", "show", "default")
    )


def _windows_dns_command() -> tuple[str, ...]:
    script = (
        "$dns=Get-DnsClientServerAddress | Select-Object InterfaceAlias,ServerAddresses;"
        "$ip=Get-NetIPInterface -AddressFamily IPv4 | Select-Object InterfaceAlias,Dhcp;"
        "$adapters=Get-NetAdapter | Select-Object Name,InterfaceGuid,InterfaceIndex;"
        "[PSCustomObject]@{Dns=$dns;Interfaces=$ip;Adapters=$adapters} | "
        "ConvertTo-Json -Depth 4 -Compress"
    )
    return (
        "powershell.exe",
        "-NoLogo",
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        script,
    )


def _parse_windows_dns(
    output: str, *, interface_name: str | None = None
) -> tuple[str, ...]:
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return ()
    if isinstance(payload, dict) and "Dns" in payload:
        payload = payload.get("Dns") or []
    rows = payload if isinstance(payload, list) else [payload]
    result: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        if interface_name and str(row.get("InterfaceAlias") or "") != interface_name:
            continue
        values = row.get("ServerAddresses") or ()
        if isinstance(values, str):
            values = (values,)
        for value in values:
            normalized = str(value).split("%", 1)[0]
            if _valid_ip(normalized) and normalized not in result:
                result.append(normalized)
    return tuple(result)


def _parse_windows_dhcp(output: str) -> dict[str, bool]:
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("Interfaces") or []
    if isinstance(rows, dict):
        rows = [rows]
    result: dict[str, bool] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("InterfaceAlias") or "").strip()
        value = row.get("Dhcp")
        if name and value in {0, 1, False, True}:
            result[name] = bool(value)
    return result


def _parse_windows_adapter_ids(output: str) -> dict[str, str]:
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    rows = payload.get("Adapters") or []
    if isinstance(rows, dict):
        rows = [rows]
    result: dict[str, str] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        name = str(row.get("Name") or "").strip()
        stable_id = str(row.get("InterfaceGuid") or "").strip()
        if name and re.fullmatch(r"\{?[0-9A-Fa-f-]{36}\}?", stable_id):
            result[name] = stable_id.strip("{}").lower()
    return result


def _parse_scutil_dns(output: str) -> tuple[str, ...]:
    result: list[str] = []
    for value in re.findall(r"nameserver\[\d+\]\s*:\s*(\S+)", output):
        normalized = value.split("%", 1)[0]
        if _valid_ip(normalized) and normalized not in result:
            result.append(normalized)
    return tuple(result)


def _parse_macos_network_services(output: str) -> dict[str, str]:
    """Map BSD device names to exact networksetup service names."""
    services: dict[str, str] = {}
    pending_service = ""
    for raw_line in output.splitlines():
        line = raw_line.strip()
        service = re.match(r"^\(\d+\)\s+(.+)$", line)
        if service:
            pending_service = service.group(1).lstrip("*").strip()
            continue
        device = re.search(r"\bDevice:\s*([^,)]+)", line)
        if pending_service and device:
            services[device.group(1).strip()] = pending_service
            pending_service = ""
    return services


_NM_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
    r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def _parse_nm_active_uuid(output: str, interface_name: str) -> str | None:
    """Return the UUID of the active NetworkManager profile on one device."""

    for raw_line in output.splitlines():
        uuid_value, separator, device = raw_line.strip().rpartition(":")
        if separator and device == interface_name and _NM_UUID.fullmatch(uuid_value):
            return uuid_value.casefold()
    return None


def _parse_nm_ipv4_method(output: str) -> bool | None:
    """Map NetworkManager's configured IPv4 method to DHCP eligibility."""

    method = next(
        (line.strip().casefold() for line in output.splitlines() if line.strip()), ""
    )
    if method == "auto":
        return True
    if method in {"disabled", "link-local", "manual", "shared"}:
        return False
    return None


def _parse_macos_dhcp_configuration(output: str) -> bool | None:
    """Interpret the configuration heading emitted by ``networksetup -getinfo``."""

    heading = next(
        (line.strip().casefold() for line in output.splitlines() if line.strip()), ""
    )
    if "dhcp configuration" in heading:
        return True
    if "manual configuration" in heading or "bootp configuration" in heading:
        return False
    return None


def _collect_linux_dhcp_configuration(
    interface_name: str,
    *,
    command_runner: CommandRunner,
    command_exists: Callable[[str], str | None],
    deadline: float,
    cancel_event: threading.Event | None,
) -> tuple[bool | None, str | None]:
    """Inspect NetworkManager first, then systemd-networkd, without blocking."""

    def remaining(cap: float) -> float:
        return max(0.0, min(cap, deadline - time.monotonic()))

    if cancel_event is not None and cancel_event.is_set():
        return None, None

    nmcli = command_exists("nmcli")
    if nmcli and remaining(0.4) >= 0.05:
        active = command_runner.run(
            (
                nmcli,
                "--terse",
                "--escape",
                "no",
                "--fields",
                "UUID,DEVICE",
                "connection",
                "show",
                "--active",
            ),
            timeout=remaining(0.4),
            cancel_event=cancel_event,
        )
        if active.cancelled or (cancel_event is not None and cancel_event.is_set()):
            return None, None
        active_uuid = (
            _parse_nm_active_uuid(active.stdout, interface_name)
            if active.returncode == 0
            else None
        )
        if active_uuid:
            if remaining(0.4) < 0.05:
                return None, active_uuid
            method = command_runner.run(
                (
                    nmcli,
                    "--terse",
                    "--get-values",
                    "ipv4.method",
                    "connection",
                    "show",
                    "uuid",
                    active_uuid,
                ),
                timeout=remaining(0.4),
                cancel_event=cancel_event,
            )
            if method.cancelled or (cancel_event is not None and cancel_event.is_set()):
                return None, active_uuid
            return (
                _parse_nm_ipv4_method(method.stdout)
                if method.returncode == 0
                else None,
                active_uuid,
            )

    busctl = command_exists("busctl")
    if not busctl or remaining(0.35) < 0.05:
        return None, None
    try:
        interface_index = socket.if_nametoindex(interface_name)
    except OSError:
        return None, None
    state = command_runner.run(
        (
            busctl,
            "--system",
            "get-property",
            "org.freedesktop.network1",
            f"/org/freedesktop/network1/link/_{interface_index}",
            "org.freedesktop.network1.DHCPv4Client",
            "State",
        ),
        timeout=remaining(0.35),
        cancel_event=cancel_event,
    )
    if state.cancelled or (cancel_event is not None and cancel_event.is_set()):
        return None, None
    # The DHCPv4Client interface only exists when networkd instantiated a
    # client for this link.  Its state may legitimately be selecting/rebinding
    # while the machine is offline, so successful introspection is sufficient.
    if state.returncode == 0 and re.fullmatch(r'\s*s\s+"[^"]*"\s*', state.stdout):
        return True, None
    return None, None


def _windows_proxy_metadata() -> tuple[str | None, bool]:
    if platform.system().lower() != "windows":
        return None, False
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            try:
                pac_url = str(winreg.QueryValueEx(key, "AutoConfigURL")[0]).strip()
            except OSError:
                pac_url = ""
            try:
                auto_detect = bool(winreg.QueryValueEx(key, "AutoDetect")[0])
            except OSError:
                auto_detect = False
        return pac_url or None, auto_detect
    except (OSError, ImportError):
        return None, False


def _collect_proxy_configuration(
    system: str,
    environ: Mapping[str, str],
    *,
    timeout: float = 0.35,
    cancel_event: threading.Event | None = None,
) -> ProxyConfiguration:
    value, error, timed_out, _ = _bounded_daemon_call(
        urllib.request.getproxies,
        timeout=max(0.025, timeout),
        cancel_event=cancel_event,
    )
    raw_proxies = (
        value if isinstance(value, dict) and not error and not timed_out else {}
    )
    proxies: list[tuple[str, str]] = []
    credentials_redacted = False
    discovered_pac: str | None = None
    for scheme, raw_url in sorted(raw_proxies.items()):
        if scheme.lower() in {"no", "no_proxy"}:
            continue
        if scheme.lower() in {"pac", "autoconfig", "autoconfig_url"}:
            discovered_pac = str(raw_url)
            continue
        sanitized, had_credentials = _sanitize_proxy_url(str(raw_url))
        credentials_redacted |= had_credentials
        if sanitized:
            proxies.append((scheme.lower(), sanitized))

    pac_url = (
        environ.get("PROXY_PAC_URL")
        or environ.get("proxy_pac_url")
        or environ.get("AUTOCONFIG_URL")
        or environ.get("autoconfig_url")
        or discovered_pac
    )
    auto_detect = bool(environ.get("WPAD_URL") or environ.get("wpad_url"))
    if system == "windows":
        registry_pac, registry_auto = _windows_proxy_metadata()
        pac_url = pac_url or registry_pac
        auto_detect = auto_detect or registry_auto
    if pac_url:
        pac_url, pac_credentials = _sanitize_pac_url(pac_url)
        credentials_redacted |= pac_credentials
    return ProxyConfiguration(
        tuple(proxies),
        pac_url,
        auto_detect,
        credentials_redacted,
    )


def _process_security_flags(
    cancel_event: threading.Event | None = None,
) -> tuple[bool, bool]:
    fortinet = False
    vpn = False
    try:
        processes = psutil.process_iter(["name"])
    except (OSError, RuntimeError):
        return fortinet, vpn
    for process in processes:
        if cancel_event is not None and cancel_event.is_set():
            break
        try:
            name = (process.info.get("name") or "").casefold()
        except (psutil.Error, AttributeError):
            continue
        if any(token in name for token in ("forticlient", "fortitray", "fortivpn")):
            fortinet = True
            vpn = True
        elif any(token in name for token in ("openvpn", "wireguard", "anyconnect")):
            vpn = True
    return fortinet, vpn


class SnapshotCollector:
    """Collect local evidence without requiring working internet access."""

    def __init__(
        self,
        *,
        command_runner: CommandRunner | None = None,
        platform_name: str | None = None,
        environ: Mapping[str, str] | None = None,
        command_exists: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.command_runner = command_runner or SubprocessCommandRunner()
        self.platform_name = (platform_name or platform.system()).lower()
        self.environ = environ if environ is not None else os.environ
        self.command_exists = command_exists

    def collect(
        self,
        *,
        timeout: float = 2.5,
        cancel_event: threading.Event | None = None,
    ) -> NetworkSnapshot:
        started = time.monotonic()
        deadline = started + timeout
        errors: list[str] = []
        interfaces: tuple[NetworkInterface, ...] = ()
        if cancel_event is None or not cancel_event.is_set():
            interface_budget = min(0.8, timeout, deadline - time.monotonic())
            if interface_budget > 0:
                value, interface_error, interface_timed_out, interface_cancelled = (
                    _bounded_daemon_call(
                        _interface_addresses,
                        timeout=interface_budget,
                        cancel_event=cancel_event,
                    )
                )
                if isinstance(value, tuple):
                    interfaces = value
                if interface_error is not None:
                    errors.append("interface-enumeration-failed")
                if interface_timed_out:
                    errors.append("interface-enumeration-timeout")
                if interface_cancelled:
                    errors.append("interface-enumeration-cancelled")
            else:
                errors.append("interface-enumeration-timeout")
        else:
            errors.append("interface-enumeration-cancelled")

        route_command = _default_route_command(self.platform_name)
        route_remaining = deadline - time.monotonic()
        if cancel_event is not None and cancel_event.is_set():
            route_result = CommandResult(route_command, None, cancelled=True)
        elif route_remaining <= 0:
            route_result = CommandResult(route_command, None, timed_out=True)
        else:
            route_result = self.command_runner.run(
                route_command,
                timeout=min(0.9, route_remaining),
                cancel_event=cancel_event,
            )
        gateway, route_interface, route_present = _parse_route(
            self.platform_name, route_result.stdout, interfaces
        )
        has_ipv6 = any(
            item.is_up and not item.is_loopback and item.ipv6 for item in interfaces
        )
        if not route_present and has_ipv6 and deadline - time.monotonic() > 0.08:
            ipv6_route = self.command_runner.run(
                _default_route_command(self.platform_name, ipv6=True),
                timeout=max(0.05, min(0.9, deadline - time.monotonic())),
                cancel_event=cancel_event,
            )
            gateway, route_interface, route_present = _parse_route(
                self.platform_name, ipv6_route.stdout, interfaces
            )
            if ipv6_route.returncode not in (0, None) or ipv6_route.timed_out:
                errors.append("ipv6-default-route-unavailable")
        if not route_present and (
            route_result.returncode not in (0, None) or route_result.timed_out
        ):
            errors.append("default-route-unavailable")

        active = route_interface
        if not active:
            candidates = [
                item
                for item in interfaces
                if item.is_up and not item.is_loopback and (item.ipv4 or item.ipv6)
            ]
            candidates.sort(key=lambda item: (item.is_virtual, item.name.casefold()))
            active = candidates[0].name if candidates else None

        dns_servers: tuple[str, ...] = ()
        dhcp_by_interface: dict[str, bool] = {}
        stable_ids: dict[str, str] = {}
        remaining = deadline - time.monotonic()
        if remaining > 0.08 and not (cancel_event and cancel_event.is_set()):
            if self.platform_name == "windows":
                dns_result = self.command_runner.run(
                    _windows_dns_command(),
                    # The combined DNS/DHCP/GUID query can take ~1.5 s on a
                    # cold Windows PowerShell start, while the outer snapshot
                    # deadline still caps the complete local phase at 2.5 s.
                    timeout=min(1.9, remaining),
                    cancel_event=cancel_event,
                )
                dns_servers = _parse_windows_dns(
                    dns_result.stdout, interface_name=active
                )
                dhcp_by_interface = _parse_windows_dhcp(dns_result.stdout)
                stable_ids = _parse_windows_adapter_ids(dns_result.stdout)
                if dns_result.timed_out:
                    errors.append("dns-enumeration-timeout")
            elif self.platform_name == "darwin":
                dns_result = self.command_runner.run(
                    ("scutil", "--dns"),
                    timeout=min(0.7, remaining),
                    cancel_event=cancel_event,
                )
                dns_servers = _parse_scutil_dns(dns_result.stdout)
            else:
                dns_servers = _read_dns_resolv_conf()

        if dhcp_by_interface or stable_ids:
            interfaces = tuple(
                replace(
                    item,
                    dhcp_enabled=dhcp_by_interface.get(item.name),
                    stable_id=stable_ids.get(item.name),
                )
                for item in interfaces
            )

        if (
            self.platform_name == "linux"
            and active
            and deadline - time.monotonic() > 0.08
            and not (cancel_event and cancel_event.is_set())
        ):
            dhcp_enabled, connection_uuid = _collect_linux_dhcp_configuration(
                active,
                command_runner=self.command_runner,
                command_exists=self.command_exists,
                deadline=deadline,
                cancel_event=cancel_event,
            )
            if dhcp_enabled is not None or connection_uuid is not None:
                interfaces = tuple(
                    replace(
                        item,
                        dhcp_enabled=dhcp_enabled,
                        connection_uuid=connection_uuid,
                    )
                    if item.name == active
                    else item
                    for item in interfaces
                )

        if (
            self.platform_name == "darwin"
            and deadline - time.monotonic() > 0.08
            and not (cancel_event and cancel_event.is_set())
        ):
            services_result = self.command_runner.run(
                ("networksetup", "-listnetworkserviceorder"),
                timeout=min(0.6, deadline - time.monotonic()),
                cancel_event=cancel_event,
            )
            service_names = _parse_macos_network_services(services_result.stdout)
            interfaces = tuple(
                replace(item, service_name=service_names.get(item.name))
                for item in interfaces
            )

            active_service = service_names.get(active or "")
            dhcp_remaining = deadline - time.monotonic()
            if (
                active_service
                and dhcp_remaining > 0.05
                and not (cancel_event and cancel_event.is_set())
            ):
                dhcp_result = self.command_runner.run(
                    ("networksetup", "-getinfo", active_service),
                    timeout=min(0.45, dhcp_remaining),
                    cancel_event=cancel_event,
                )
                dhcp_enabled = (
                    _parse_macos_dhcp_configuration(dhcp_result.stdout)
                    if dhcp_result.returncode == 0
                    else None
                )
                if dhcp_result.timed_out:
                    errors.append("dhcp-enumeration-timeout")
                if dhcp_enabled is not None:
                    interfaces = tuple(
                        replace(item, dhcp_enabled=dhcp_enabled)
                        if item.name == active
                        else item
                        for item in interfaces
                    )

        proxy_remaining = deadline - time.monotonic()
        if proxy_remaining > 0 and not (cancel_event and cancel_event.is_set()):
            proxy = _collect_proxy_configuration(
                self.platform_name,
                self.environ,
                timeout=min(0.35, proxy_remaining),
                cancel_event=cancel_event,
            )
        else:
            proxy = ProxyConfiguration()
        selected = next((item for item in interfaces if item.name == active), None)
        selected_v4 = selected.ipv4 if selected else ()
        selected_v6 = selected.ipv6 if selected else ()
        apipa = bool(selected_v4) and all(
            ipaddress.ip_address(value).is_link_local for value in selected_v4
        )
        ipv6_only = bool(selected_v6) and not selected_v4
        interface_vpn = any(
            item.is_up and _VPN_NAMES.search(item.name) for item in interfaces
        )
        fortinet, process_vpn = _process_security_flags(cancel_event)
        vpn_active = bool(interface_vpn or process_vpn)
        remote = bool(
            self.environ.get("SSH_CONNECTION")
            or self.environ.get("SSH_CLIENT")
            or self.environ.get("REMOTEHOST")
            or self.environ.get("SESSIONNAME", "").upper().startswith("RDP")
        )
        dot1x = any(
            token in self.environ
            for token in ("USERDNSDOMAIN", "MDM_ENROLLMENT_ID", "INTUNE_DEVICE_ID")
        )
        managed = bool(dot1x or proxy.has_explicit_proxy or proxy.has_pac or fortinet)
        return NetworkSnapshot(
            captured_at=datetime.now(timezone.utc),
            platform=self.platform_name,
            interfaces=interfaces,
            active_interface=active,
            default_gateway=gateway,
            route_present=route_present,
            dns_servers=dns_servers,
            proxy=proxy,
            apipa=apipa,
            ipv6_only=ipv6_only,
            vpn_active=vpn_active,
            fortinet_client_active=fortinet,
            managed_network=managed,
            dot1x_suspected=dot1x,
            remote_session=remote,
            command_errors=tuple(errors),
        )


@dataclass(frozen=True, slots=True)
class HttpObservation:
    status_code: int | None
    final_url: str
    body: str = ""
    headers: Mapping[str, str] = field(default_factory=dict)
    error: str = ""


class ProbeBackend(Protocol):
    def resolve(
        self,
        host: str,
        *,
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> tuple[str, ...]: ...

    def tcp_connect(
        self,
        host: str,
        port: int,
        *,
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> None: ...

    def http_get(
        self,
        url: str,
        *,
        proxies: Mapping[str, str],
        timeout: float,
        cancel_event: threading.Event | None,
        ca_file: str | None = None,
    ) -> HttpObservation: ...

    def ping(
        self,
        host: str,
        *,
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> CommandResult: ...


def _system_ssl_context(ca_file: str | None = None) -> ssl.SSLContext:
    try:
        import truststore

        context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except (ImportError, OSError):
        context = ssl.create_default_context()
    if ca_file:
        # Revalidate on every use.  This also converts a newly selected file
        # into the immutable, fingerprint-named app store before OpenSSL or
        # truststore sees it, closing path-replacement races after consent.
        from monitor.network_repairs import _validate_app_ca

        verified_ca = _validate_app_ca(ca_file)
        context.load_verify_locations(cafile=verified_ca)
    return context


class SystemProbeBackend:
    def __init__(self, command_runner: CommandRunner | None = None) -> None:
        self.command_runner = command_runner or SubprocessCommandRunner()

    def resolve(
        self,
        host: str,
        *,
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> tuple[str, ...]:
        value, error, timed_out, cancelled = _bounded_daemon_call(
            lambda: socket.getaddrinfo(host, None, type=socket.SOCK_STREAM),
            timeout=timeout,
            cancel_event=cancel_event,
        )
        if cancelled:
            raise DiagnosticCancelled
        if timed_out:
            raise TimeoutError("DNS resolution timed out")
        if error:
            raise error
        addresses: list[str] = []
        for item in value or ():
            address = item[4][0]
            if address not in addresses:
                addresses.append(address)
        return tuple(addresses)

    def tcp_connect(
        self,
        host: str,
        port: int,
        *,
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> None:
        def connect() -> None:
            with socket.create_connection((host, port), timeout=timeout):
                return None

        _, error, timed_out, cancelled = _bounded_daemon_call(
            connect, timeout=timeout, cancel_event=cancel_event
        )
        if cancelled:
            raise DiagnosticCancelled
        if timed_out:
            raise TimeoutError("TCP connection timed out")
        if error:
            raise error

    def http_get(
        self,
        url: str,
        *,
        proxies: Mapping[str, str],
        timeout: float,
        cancel_event: threading.Event | None,
        ca_file: str | None = None,
    ) -> HttpObservation:
        def request() -> HttpObservation:
            handlers: list[Any] = [urllib.request.ProxyHandler(dict(proxies))]
            if urllib.parse.urlsplit(url).scheme == "https":
                handlers.append(
                    urllib.request.HTTPSHandler(context=_system_ssl_context(ca_file))
                )
            opener = urllib.request.build_opener(*handlers)
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Varedura-Network-Diagnostics/1.0",
                    "Accept": "text/plain,text/html;q=0.5,*/*;q=0.1",
                    "Cache-Control": "no-cache",
                },
                method="GET",
            )
            try:
                with opener.open(req, timeout=timeout) as response:
                    body = response.read(4096).decode("utf-8", errors="replace")
                    headers = {
                        key.casefold(): _redact_text(value)
                        for key, value in response.headers.items()
                    }
                    return HttpObservation(
                        int(response.status),
                        _redact_text(response.geturl()),
                        body,
                        headers,
                    )
            except urllib.error.HTTPError as exc:
                try:
                    body = exc.read(4096).decode("utf-8", errors="replace")
                except OSError:
                    body = ""
                return HttpObservation(
                    exc.code,
                    _redact_text(exc.geturl()),
                    body,
                    {
                        key.casefold(): _redact_text(value)
                        for key, value in exc.headers.items()
                    },
                    _redact_text(str(exc)),
                )

        value, error, timed_out, cancelled = _bounded_daemon_call(
            request, timeout=timeout, cancel_event=cancel_event
        )
        if cancelled:
            raise DiagnosticCancelled
        if timed_out:
            raise TimeoutError("HTTP request timed out")
        if error:
            return HttpObservation(None, url, error=_redact_text(str(error)))
        assert value is not None
        return value

    def ping(
        self,
        host: str,
        *,
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> CommandResult:
        if platform.system().lower() == "windows":
            milliseconds = max(100, int(timeout * 1000))
            args = ("ping.exe", "-n", "1", "-w", str(milliseconds), host)
        elif platform.system().lower() == "darwin":
            milliseconds = max(100, int(timeout * 1000))
            args = ("ping", "-c", "1", "-W", str(milliseconds), host)
        else:
            seconds = max(1, int(timeout + 0.999))
            args = ("ping", "-c", "1", "-W", str(seconds), host)
        return self.command_runner.run(
            args, timeout=timeout + 0.2, cancel_event=cancel_event
        )


class DiagnosticCancelled(Exception):
    """Internal control-flow exception for prompt cancellation."""


_FORTINET_MARKERS = (
    "fortinet_ca_untrusted",
    "fortigate",
    "fortiguard",
    "fortinet",
)
_CERTIFICATE_MARKERS = (
    "certificate verify failed",
    "self signed certificate",
    "unable to get local issuer certificate",
    "unknown ca",
    "certificate_unknown",
)


def _http_failure_cause(observation: HttpObservation) -> FailureCause:
    material = " ".join(
        (
            observation.error,
            observation.body[:4096],
            " ".join(f"{key}:{value}" for key, value in observation.headers.items()),
        )
    ).casefold()
    if observation.status_code == 407:
        return FailureCause.PROXY_AUTH_REQUIRED
    if any(marker in material for marker in _FORTINET_MARKERS):
        if "untrusted" in material or "certificate" in material:
            return FailureCause.FORTIGATE_BLOCK_CERT
        return FailureCause.POLICY_BLOCKED
    if any(marker in material for marker in _CERTIFICATE_MARKERS):
        return FailureCause.TLS_CERT_UNTRUSTED
    if observation.status_code in {401, 403, 451}:
        return FailureCause.POLICY_BLOCKED
    return FailureCause.INCONCLUSIVE


def _failure_probe(
    kind: ProbeKind,
    started: float,
    cause: FailureCause,
    message: str,
    *,
    target: str | None = None,
    status_code: int | None = None,
    status: ProbeStatus = ProbeStatus.FAILURE,
    details: Mapping[str, Any] | None = None,
) -> ProbeResult:
    return ProbeResult(
        kind,
        status,
        (time.monotonic() - started) * 1000,
        cause,
        _redact_text(message),
        target,
        status_code,
        details or {},
    )


def _local_probes(snapshot: NetworkSnapshot) -> list[ProbeResult]:
    if snapshot.active_interface:
        link = ProbeResult(
            ProbeKind.LINK,
            ProbeStatus.SUCCESS,
            0.0,
            message=f"interface {snapshot.active_interface} is active",
            target=snapshot.active_interface,
        )
    else:
        link = ProbeResult(
            ProbeKind.LINK,
            ProbeStatus.FAILURE,
            0.0,
            FailureCause.NO_ACTIVE_INTERFACE,
            "no active network interface",
        )
    if snapshot.apipa:
        route = ProbeResult(
            ProbeKind.ROUTE,
            ProbeStatus.FAILURE,
            0.0,
            FailureCause.APIPA_NO_DHCP_LEASE,
            "active interface only has a link-local IPv4 address",
            target=snapshot.active_interface,
        )
    elif snapshot.route_present:
        route = ProbeResult(
            ProbeKind.ROUTE,
            ProbeStatus.SUCCESS,
            0.0,
            message="a default route is present",
            target=snapshot.default_gateway or snapshot.active_interface,
        )
    else:
        route = ProbeResult(
            ProbeKind.ROUTE,
            ProbeStatus.FAILURE,
            0.0,
            FailureCause.NO_DEFAULT_ROUTE,
            "no default route was found",
        )
    return [link, route]


def _evidence_for_snapshot(snapshot: NetworkSnapshot) -> list[Evidence]:
    evidence: list[Evidence] = []
    if snapshot.proxy.has_pac:
        evidence.append(
            Evidence(
                "pac-present",
                "automatic proxy configuration is present",
                Confidence.CONFIRMED,
                details={"pac_url": bool(snapshot.proxy.pac_url)},
            )
        )
    if snapshot.proxy.credentials_redacted:
        evidence.append(
            Evidence(
                "proxy-credentials-redacted",
                "proxy credentials were detected and deliberately not retained",
                Confidence.CONFIRMED,
            )
        )
    if snapshot.vpn_active:
        evidence.append(
            Evidence(
                "vpn-active",
                "a VPN or tunnel interface/client appears active",
                Confidence.LIKELY,
                details={"cause": FailureCause.VPN_ACTIVE.value},
            )
        )
    if snapshot.fortinet_client_active:
        evidence.append(
            Evidence(
                "fortinet-client-active",
                "a Fortinet client process appears active",
                Confidence.CONFIRMED,
            )
        )
    if snapshot.remote_session:
        evidence.append(
            Evidence(
                "remote-session",
                "the application appears to be running in a remote session",
                Confidence.LIKELY,
            )
        )
    return evidence


def classify_diagnosis(
    snapshot: NetworkSnapshot,
    probes: tuple[ProbeResult, ...] | list[ProbeResult],
) -> tuple[NetworkState, Confidence, str, tuple[Evidence, ...]]:
    """Classify structured probes without assuming that ICMP must work."""

    results = tuple(probes)
    evidence = _evidence_for_snapshot(snapshot)

    def find(kind: ProbeKind) -> ProbeResult | None:
        return next((probe for probe in results if probe.kind is kind), None)

    link = find(ProbeKind.LINK)
    route = find(ProbeKind.ROUTE)
    dns = find(ProbeKind.DNS)
    captive = find(ProbeKind.CAPTIVE_PORTAL)
    https = find(ProbeKind.HTTPS)
    icmp = find(ProbeKind.ICMP)

    for probe in results:
        if probe.status in {ProbeStatus.FAILURE, ProbeStatus.TIMED_OUT}:
            evidence.append(
                Evidence(
                    f"probe-{probe.kind.value}-{probe.cause.value}",
                    probe.message or f"{probe.kind.value} probe failed",
                    Confidence.CONFIRMED,
                    probe.kind,
                    {"cause": probe.cause.value, "target": probe.target},
                )
            )

    if link is None or not link.succeeded:
        return (
            NetworkState.OFFLINE,
            Confidence.CONFIRMED,
            "No active network interface was found.",
            tuple(evidence),
        )
    if snapshot.apipa:
        return (
            NetworkState.OFFLINE,
            Confidence.CONFIRMED,
            "The interface has an automatic link-local address and no DHCP lease.",
            tuple(evidence),
        )
    if route is None or not route.succeeded:
        return (
            NetworkState.LOCAL_ONLY,
            Confidence.CONFIRMED,
            "The local link is active, but there is no default route.",
            tuple(evidence),
        )

    causes = {probe.cause for probe in results}
    if FailureCause.CAPTIVE_PORTAL_DETECTED in causes:
        return (
            NetworkState.CAPTIVE_PORTAL,
            Confidence.CONFIRMED,
            "A captive portal intercepted the connectivity check.",
            tuple(evidence),
        )
    if FailureCause.PROXY_AUTH_REQUIRED in causes:
        return (
            NetworkState.PROXY_AUTH_REQUIRED,
            Confidence.CONFIRMED,
            "The configured proxy requires authentication.",
            tuple(evidence),
        )
    if FailureCause.POLICY_BLOCKED in causes:
        return (
            NetworkState.POLICY_BLOCKED,
            Confidence.LIKELY,
            "A gateway, proxy, or institutional policy appears to block the request.",
            tuple(evidence),
        )
    if FailureCause.FORTIGATE_BLOCK_CERT in causes:
        return (
            NetworkState.TLS_POLICY_BLOCKED,
            Confidence.CONFIRMED,
            "FortiGate presented an untrusted block certificate; contact the network administrator.",
            tuple(evidence),
        )
    if FailureCause.TLS_CERT_UNTRUSTED in causes:
        if snapshot.managed_network:
            evidence.append(
                Evidence(
                    "tls-interception-suspected",
                    "TLS interception is possible, but the presented CA is not trusted by the OS.",
                    Confidence.LIKELY,
                    ProbeKind.HTTPS,
                    {"cause": FailureCause.TLS_INTERCEPTION_SUSPECTED.value},
                )
            )
        return (
            NetworkState.TLS_POLICY_BLOCKED,
            Confidence.LIKELY,
            "HTTPS certificate validation failed; TLS verification was not bypassed.",
            tuple(evidence),
        )

    if https and https.succeeded:
        if icmp and not icmp.succeeded:
            evidence.append(
                Evidence(
                    "icmp-filtered",
                    "HTTPS works while ICMP does not; ping is probably filtered or unsupported.",
                    Confidence.LIKELY,
                    ProbeKind.ICMP,
                    {"cause": FailureCause.ICMP_FILTERED_OR_UNSUPPORTED.value},
                )
            )
        managed = bool(
            snapshot.managed_network
            or snapshot.proxy.has_explicit_proxy
            or snapshot.vpn_active
            or bool(https.details.get("app_ca"))
        )
        return (
            NetworkState.ONLINE_MANAGED if managed else NetworkState.ONLINE,
            Confidence.CONFIRMED,
            "Internet access is working through managed network policy."
            if managed
            else "Internet access is working.",
            tuple(evidence),
        )

    if snapshot.proxy.has_pac and not snapshot.proxy.has_explicit_proxy:
        evidence.append(
            Evidence(
                "pac-not-evaluated",
                "The PAC policy could not be evaluated safely; direct probes were not attempted.",
                Confidence.CONFIRMED,
                details={"cause": FailureCause.PAC_UNAVAILABLE.value},
            )
        )
        return (
            NetworkState.UNKNOWN,
            Confidence.POSSIBLE,
            "Connectivity is inconclusive because automatic proxy policy could not be evaluated.",
            tuple(evidence),
        )
    core_external = [
        probe
        for probe in results
        if probe.kind in {ProbeKind.TCP, ProbeKind.CAPTIVE_PORTAL, ProbeKind.HTTPS}
        and probe.status is not ProbeStatus.SKIPPED
    ]
    if core_external and all(
        probe.status in {ProbeStatus.FAILURE, ProbeStatus.TIMED_OUT}
        for probe in core_external
    ):
        return (
            NetworkState.OFFLINE,
            Confidence.LIKELY,
            "A local route exists, but no external transport or web probe succeeded.",
            tuple(evidence),
        )
    if dns and not dns.succeeded:
        return (
            NetworkState.LIMITED,
            Confidence.LIKELY,
            "A route exists, but DNS resolution failed.",
            tuple(evidence),
        )
    if captive and captive.succeeded:
        return (
            NetworkState.LIMITED,
            Confidence.LIKELY,
            "Plain HTTP works, but verified HTTPS did not complete.",
            tuple(evidence),
        )
    if any(
        probe.succeeded
        for probe in results
        if probe.kind not in {ProbeKind.LINK, ProbeKind.ROUTE}
    ):
        return (
            NetworkState.LIMITED,
            Confidence.LIKELY,
            "Some network layers work, but end-to-end HTTPS could not be confirmed.",
            tuple(evidence),
        )
    return (
        NetworkState.UNKNOWN,
        Confidence.POSSIBLE,
        "The available evidence is insufficient to determine connectivity.",
        tuple(evidence),
    )


class NetworkDiagnosticEngine:
    def __init__(
        self,
        *,
        snapshot_collector: SnapshotCollector | None = None,
        probe_backend: ProbeBackend | None = None,
    ) -> None:
        runner = SubprocessCommandRunner()
        self.snapshot_collector = snapshot_collector or SnapshotCollector(
            command_runner=runner
        )
        self.probe_backend = probe_backend or SystemProbeBackend(runner)

    def diagnose(
        self,
        *,
        snapshot: NetworkSnapshot | None = None,
        options: DiagnosticOptions | None = None,
        cancel_event: threading.Event | None = None,
    ) -> DiagnosisReport:
        settings = options or DiagnosticOptions()
        started_at = datetime.now(timezone.utc)
        started = time.monotonic()
        deadline = started + settings.overall_timeout
        cancelled = False
        timed_out = False

        if snapshot is None:
            snapshot_budget = min(settings.snapshot_timeout, settings.overall_timeout)
            snapshot = self.snapshot_collector.collect(
                timeout=snapshot_budget,
                cancel_event=cancel_event,
            )

        probes = _local_probes(snapshot)
        if cancel_event is not None and cancel_event.is_set():
            probes.append(
                ProbeResult(
                    ProbeKind.HTTPS,
                    ProbeStatus.CANCELLED,
                    0.0,
                    FailureCause.CANCELLED,
                    "diagnosis cancelled",
                )
            )
            state, confidence, summary, evidence = classify_diagnosis(snapshot, probes)
            return DiagnosisReport(
                state,
                confidence,
                summary,
                snapshot,
                tuple(probes),
                evidence,
                started_at,
                datetime.now(timezone.utc),
                cancelled=True,
            )
        if (
            not snapshot.active_interface
            or not snapshot.route_present
            or snapshot.apipa
        ):
            state, confidence, summary, evidence = classify_diagnosis(snapshot, probes)
            return DiagnosisReport(
                state,
                confidence,
                summary,
                snapshot,
                tuple(probes),
                evidence,
                started_at,
                datetime.now(timezone.utc),
            )

        def budget() -> float:
            return max(
                0.0, min(settings.per_probe_timeout, deadline - time.monotonic())
            )

        def check_cancel() -> None:
            if cancel_event is not None and cancel_event.is_set():
                raise DiagnosticCancelled
            if time.monotonic() >= deadline:
                raise TimeoutError("overall diagnostic deadline reached")

        try:
            check_cancel()
            probe_started = time.monotonic()
            try:
                addresses = self.probe_backend.resolve(
                    settings.dns_host,
                    timeout=budget(),
                    cancel_event=cancel_event,
                )
                probes.append(
                    ProbeResult(
                        ProbeKind.DNS,
                        ProbeStatus.SUCCESS,
                        (time.monotonic() - probe_started) * 1000,
                        message=f"resolved {len(addresses)} address(es)",
                        target=settings.dns_host,
                        details={"address_count": len(addresses)},
                    )
                )
            except DiagnosticCancelled:
                raise
            except TimeoutError as exc:
                probes.append(
                    _failure_probe(
                        ProbeKind.DNS,
                        probe_started,
                        FailureCause.TIMEOUT,
                        str(exc),
                        target=settings.dns_host,
                        status=ProbeStatus.TIMED_OUT,
                    )
                )
            except (OSError, socket.gaierror) as exc:
                probes.append(
                    _failure_probe(
                        ProbeKind.DNS,
                        probe_started,
                        FailureCause.DNS_RESOLUTION_FAILED,
                        str(exc),
                        target=settings.dns_host,
                    )
                )

            if snapshot.proxy.has_pac and not snapshot.proxy.has_explicit_proxy:
                for kind, target in (
                    (ProbeKind.TCP, settings.tcp_host),
                    (ProbeKind.CAPTIVE_PORTAL, settings.captive_portal_url),
                    (ProbeKind.HTTPS, settings.https_url),
                ):
                    probes.append(
                        ProbeResult(
                            kind,
                            ProbeStatus.SKIPPED,
                            0.0,
                            FailureCause.PAC_UNAVAILABLE,
                            "automatic proxy policy cannot be evaluated safely",
                            target,
                        )
                    )
            else:
                check_cancel()
                tcp_host, tcp_port = settings.tcp_host, settings.tcp_port
                if snapshot.proxy.has_explicit_proxy:
                    proxy_url = snapshot.proxy.as_dict().get("https") or next(
                        iter(snapshot.proxy.as_dict().values())
                    )
                    parsed = urllib.parse.urlsplit(proxy_url)
                    tcp_host = parsed.hostname or tcp_host
                    tcp_port = parsed.port or (443 if parsed.scheme == "https" else 80)
                probe_started = time.monotonic()
                try:
                    self.probe_backend.tcp_connect(
                        tcp_host,
                        tcp_port,
                        timeout=budget(),
                        cancel_event=cancel_event,
                    )
                    probes.append(
                        ProbeResult(
                            ProbeKind.TCP,
                            ProbeStatus.SUCCESS,
                            (time.monotonic() - probe_started) * 1000,
                            message="TCP connection succeeded",
                            target=f"{tcp_host}:{tcp_port}",
                        )
                    )
                except DiagnosticCancelled:
                    raise
                except TimeoutError as exc:
                    probes.append(
                        _failure_probe(
                            ProbeKind.TCP,
                            probe_started,
                            FailureCause.TIMEOUT,
                            str(exc),
                            target=f"{tcp_host}:{tcp_port}",
                            status=ProbeStatus.TIMED_OUT,
                        )
                    )
                except OSError as exc:
                    probes.append(
                        _failure_probe(
                            ProbeKind.TCP,
                            probe_started,
                            FailureCause.TCP_CONNECT_FAILED,
                            str(exc),
                            target=f"{tcp_host}:{tcp_port}",
                        )
                    )

                check_cancel()
                probe_started = time.monotonic()
                observation = self.probe_backend.http_get(
                    settings.captive_portal_url,
                    proxies=snapshot.proxy.as_dict(),
                    timeout=budget(),
                    cancel_event=cancel_event,
                )
                cause = _http_failure_cause(observation)
                expected = settings.captive_expected_text.strip()
                redirected = (
                    urllib.parse.urlsplit(observation.final_url).hostname
                    != urllib.parse.urlsplit(settings.captive_portal_url).hostname
                )
                portal = bool(
                    cause is FailureCause.INCONCLUSIVE
                    and observation.status_code is not None
                    and (redirected or (expected and expected not in observation.body))
                )
                if cause is FailureCause.PROXY_AUTH_REQUIRED:
                    probes.append(
                        _failure_probe(
                            ProbeKind.CAPTIVE_PORTAL,
                            probe_started,
                            cause,
                            "proxy authentication required",
                            target=settings.captive_portal_url,
                            status_code=observation.status_code,
                        )
                    )
                elif portal:
                    probes.append(
                        _failure_probe(
                            ProbeKind.CAPTIVE_PORTAL,
                            probe_started,
                            FailureCause.CAPTIVE_PORTAL_DETECTED,
                            "connectivity check was intercepted",
                            target=settings.captive_portal_url,
                            status_code=observation.status_code,
                            details={"final_url": observation.final_url},
                        )
                    )
                elif (
                    observation.status_code is not None
                    and 200 <= observation.status_code < 400
                ):
                    probes.append(
                        ProbeResult(
                            ProbeKind.CAPTIVE_PORTAL,
                            ProbeStatus.SUCCESS,
                            (time.monotonic() - probe_started) * 1000,
                            message="captive portal check passed",
                            target=settings.captive_portal_url,
                            status_code=observation.status_code,
                            details={"final_url": observation.final_url},
                        )
                    )
                else:
                    probes.append(
                        _failure_probe(
                            ProbeKind.CAPTIVE_PORTAL,
                            probe_started,
                            cause,
                            observation.error or "HTTP connectivity check failed",
                            target=settings.captive_portal_url,
                            status_code=observation.status_code,
                        )
                    )

                check_cancel()
                probe_started = time.monotonic()
                observation = self.probe_backend.http_get(
                    settings.https_url,
                    proxies=snapshot.proxy.as_dict(),
                    timeout=budget(),
                    cancel_event=cancel_event,
                    ca_file=settings.ca_file,
                )
                if (
                    observation.status_code is not None
                    and 200 <= observation.status_code < 400
                ):
                    probes.append(
                        ProbeResult(
                            ProbeKind.HTTPS,
                            ProbeStatus.SUCCESS,
                            (time.monotonic() - probe_started) * 1000,
                            message="verified HTTPS request succeeded",
                            target=settings.https_url,
                            status_code=observation.status_code,
                            details={
                                "final_url": observation.final_url,
                                "app_ca": bool(settings.ca_file),
                            },
                        )
                    )
                else:
                    cause = _http_failure_cause(observation)
                    probes.append(
                        _failure_probe(
                            ProbeKind.HTTPS,
                            probe_started,
                            cause,
                            observation.error or "verified HTTPS request failed",
                            target=settings.https_url,
                            status_code=observation.status_code,
                        )
                    )

            if settings.enable_icmp:
                check_cancel()
                probe_started = time.monotonic()
                ping = self.probe_backend.ping(
                    settings.icmp_target,
                    timeout=budget(),
                    cancel_event=cancel_event,
                )
                if ping.cancelled:
                    raise DiagnosticCancelled
                if ping.timed_out:
                    probes.append(
                        _failure_probe(
                            ProbeKind.ICMP,
                            probe_started,
                            FailureCause.TIMEOUT,
                            "ICMP probe timed out",
                            target=settings.icmp_target,
                            status=ProbeStatus.TIMED_OUT,
                        )
                    )
                elif ping.returncode == 0:
                    probes.append(
                        ProbeResult(
                            ProbeKind.ICMP,
                            ProbeStatus.SUCCESS,
                            (time.monotonic() - probe_started) * 1000,
                            message="ICMP reply received",
                            target=settings.icmp_target,
                        )
                    )
                else:
                    probes.append(
                        _failure_probe(
                            ProbeKind.ICMP,
                            probe_started,
                            FailureCause.ICMP_FILTERED_OR_UNSUPPORTED,
                            "no ICMP reply was received",
                            target=settings.icmp_target,
                        )
                    )
        except DiagnosticCancelled:
            cancelled = True
            probes.append(
                ProbeResult(
                    ProbeKind.HTTPS,
                    ProbeStatus.CANCELLED,
                    0.0,
                    FailureCause.CANCELLED,
                    "diagnosis cancelled",
                )
            )
        except TimeoutError:
            timed_out = True

        state, confidence, summary, evidence = classify_diagnosis(snapshot, probes)
        return DiagnosisReport(
            state,
            confidence,
            summary,
            snapshot,
            tuple(probes),
            evidence,
            started_at,
            datetime.now(timezone.utc),
            cancelled,
            timed_out,
        )


def collect_network_snapshot(
    *,
    timeout: float = 2.5,
    cancel_event: threading.Event | None = None,
    collector: SnapshotCollector | None = None,
) -> NetworkSnapshot:
    return (collector or SnapshotCollector()).collect(
        timeout=timeout, cancel_event=cancel_event
    )


def run_network_diagnosis(
    *,
    snapshot: NetworkSnapshot | None = None,
    options: DiagnosticOptions | None = None,
    cancel_event: threading.Event | None = None,
    engine: NetworkDiagnosticEngine | None = None,
) -> DiagnosisReport:
    return (engine or NetworkDiagnosticEngine()).diagnose(
        snapshot=snapshot,
        options=options,
        cancel_event=cancel_event,
    )


# Concise alias for callers that do not need to construct an engine.
diagnose_network = run_network_diagnosis


__all__ = [
    "CommandResult",
    "Confidence",
    "DiagnosisReport",
    "DiagnosticOptions",
    "Evidence",
    "FailureCause",
    "HttpObservation",
    "NetworkDiagnosticEngine",
    "NetworkInterface",
    "NetworkSnapshot",
    "NetworkState",
    "ProbeKind",
    "ProbeResult",
    "ProbeStatus",
    "ProxyConfiguration",
    "SnapshotCollector",
    "SubprocessCommandRunner",
    "SystemProbeBackend",
    "classify_diagnosis",
    "collect_network_snapshot",
    "diagnose_network",
    "run_network_diagnosis",
]
