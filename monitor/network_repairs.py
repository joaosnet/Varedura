"""Conservative, individually confirmed network repair actions.

Only a small allow-list of reversible or low-impact operations is executable.
Risky system-wide resets are returned as guidance and can never reach the
subprocess runner.  Every executable action is rebuilt from a recent diagnosis
before execution, which prevents callers from injecting arbitrary commands into
a :class:`RepairAction` instance.
"""

from __future__ import annotations

import ctypes
import base64
import binascii
import hashlib
import os
import platform
import re
import shutil
import socket
import ssl
import subprocess
import threading
import time
import urllib.parse
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from monitor.network_diagnostics import (
    CommandResult,
    DiagnosisReport,
    NetworkInterface,
    NetworkSnapshot,
    NetworkState,
    ProbeKind,
)


class RepairKind(StrEnum):
    REFRESH_STATUS = "refresh_status"
    OPEN_CAPTIVE_PORTAL = "open_captive_portal"
    FLUSH_DNS = "flush_dns"
    RENEW_DHCP = "renew_dhcp"
    RECONNECT_INTERFACE = "reconnect_interface"
    ENABLE_WIFI = "enable_wifi"
    CONFIGURE_APP_CA = "configure_app_ca"


class RepairImpact(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"


class RepairStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"
    NOT_CONFIRMED = "not_confirmed"
    ELEVATION_REQUIRED = "elevation_required"
    POSTCHECK_FAILED = "postcheck_failed"


@dataclass(frozen=True, slots=True)
class RepairAction:
    action_id: str
    kind: RepairKind
    title: str
    description: str
    scope: str
    platform: str
    interface: str | None = None
    eligible: bool = True
    blocked_reason: str | None = None
    requires_confirmation: bool = True
    requires_elevation: bool = False
    impact: RepairImpact = RepairImpact.LOW
    command_preview: tuple[tuple[str, ...], ...] = ()
    rollback_preview: tuple[tuple[str, ...], ...] = ()
    partial: bool = False
    ca_file: str | None = None


@dataclass(frozen=True, slots=True)
class RepairGuidance:
    title: str
    explanation: str
    requires_it: bool = True


@dataclass(frozen=True, slots=True)
class RepairResult:
    action: RepairAction
    status: RepairStatus
    message: str
    duration_ms: float
    commands: tuple[CommandResult, ...] = ()
    rollback_attempted: bool = False
    rollback_succeeded: bool | None = None
    post_report: DiagnosisReport | None = None
    app_ca_file: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.status is RepairStatus.SUCCEEDED


class RepairRunner(Protocol):
    def run(
        self,
        args: tuple[str, ...],
        *,
        timeout: float,
        cancel_event: threading.Event | None = None,
        elevated: bool = False,
    ) -> CommandResult: ...


_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_WIFI_NAME = re.compile(r"(?i)(wi-?fi|wireless|wlan|airport|802\.11|^wl[a-z0-9_.-]*$)")
_WINDOWS_HELPER = "varedura-network-helper"
_WINDOWS_HELPER_OPERATIONS = {
    "flush_dns",
    "renew_dhcp",
    "adapter_disable",
    "adapter_enable",
    "enable_wifi",
}
_REPAIR_MUTATION_LOCK = threading.Lock()

_MACOS_DHCP_REFRESH_SCRIPT = r"""
ObjC.import('SystemConfiguration');
ObjC.import('CoreFoundation');
function run(argv) {
    if (argv.length !== 1) throw new Error('one interface is required');
    const requested = String(argv[0]);
    const interfaces = $.SCNetworkInterfaceCopyAll();
    if (!interfaces) throw new Error('SCNetworkInterfaceCopyAll failed');
    try {
        const count = $.CFArrayGetCount(interfaces);
        for (let index = 0; index < count; index++) {
            const networkInterface = $.CFArrayGetValueAtIndex(interfaces, index);
            const bsdName = $.SCNetworkInterfaceGetBSDName(networkInterface);
            if (bsdName && ObjC.unwrap(bsdName) === requested) {
                if (!$.SCNetworkInterfaceForceConfigurationRefresh(networkInterface)) {
                    throw new Error('SCNetworkInterfaceForceConfigurationRefresh failed');
                }
                return 'ok';
            }
        }
        throw new Error('exact macOS interface not found');
    } finally {
        $.CFRelease(interfaces);
    }
}
""".strip()


def _normalize_platform(value: str | None) -> str:
    name = (value or platform.system()).casefold()
    if name in {"win32", "cygwin", "windows"}:
        return "windows"
    if name in {"darwin", "mac", "macos"}:
        return "darwin"
    return "linux" if name == "linux" else name


def _valid_interface_name(value: str | None) -> bool:
    return bool(value and len(value) <= 256 and not _CONTROL_CHARS.search(value))


def _is_windows_admin() -> bool:
    if platform.system().lower() != "windows":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except (AttributeError, OSError):
        return False


def _powershell_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _windows_system_powershell() -> str:
    """Return the protected inbox PowerShell path without trusting ``PATH``."""

    buffer = ctypes.create_unicode_buffer(32_768)
    length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
    if not length or length >= len(buffer):
        raise ctypes.WinError()
    path = Path(buffer.value) / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    if not path.is_file():
        raise FileNotFoundError("protected Windows PowerShell was not found")
    return str(path)


_WINDOWS_JOB_AND_IP_HELPER = r"""
using System;
using System.Runtime.InteropServices;

public static class VareduraNative {
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_BASIC_LIMIT_INFORMATION {
        public long PerProcessUserTimeLimit;
        public long PerJobUserTimeLimit;
        public uint LimitFlags;
        public UIntPtr MinimumWorkingSetSize;
        public UIntPtr MaximumWorkingSetSize;
        public uint ActiveProcessLimit;
        public UIntPtr Affinity;
        public uint PriorityClass;
        public uint SchedulingClass;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct IO_COUNTERS {
        public ulong ReadOperationCount;
        public ulong WriteOperationCount;
        public ulong OtherOperationCount;
        public ulong ReadTransferCount;
        public ulong WriteTransferCount;
        public ulong OtherTransferCount;
    }
    [StructLayout(LayoutKind.Sequential)]
    public struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION {
        public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
        public IO_COUNTERS IoInfo;
        public UIntPtr ProcessMemoryLimit;
        public UIntPtr JobMemoryLimit;
        public UIntPtr PeakProcessMemoryUsed;
        public UIntPtr PeakJobMemoryUsed;
    }
    [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Ansi)]
    public struct IP_ADAPTER_INDEX_MAP {
        public int Index;
        [MarshalAs(UnmanagedType.ByValTStr, SizeConst=128)]
        public string Name;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)]
    public static extern IntPtr CreateJobObject(IntPtr attributes, string name);
    [DllImport("kernel32.dll")]
    public static extern bool SetInformationJobObject(
        IntPtr job, int infoClass, IntPtr info, uint length);
    [DllImport("kernel32.dll")]
    public static extern bool AssignProcessToJobObject(IntPtr job, IntPtr process);
    [DllImport("iphlpapi.dll")]
    public static extern uint IpRenewAddress(ref IP_ADAPTER_INDEX_MAP adapter);
}
"""


def _windows_elevated_script(
    operation: str,
    interface: str = "",
    stable_id: str = "",
) -> str:
    """Build a closed, allow-listed script copied into the UAC command line.

    The elevated process never imports the editable Varedura checkout and does
    not exchange results through a user-replaceable temporary file.  Its job
    object makes any native child (notably ``ipconfig``) die with the helper.
    """

    if operation not in _WINDOWS_HELPER_OPERATIONS:
        raise ValueError("helper-operation-not-allowed")
    if operation != "flush_dns":
        if not _valid_interface_name(interface) or not re.fullmatch(
            r"[0-9a-fA-F-]{36}", stable_id.strip("{}")
        ):
            raise ValueError("invalid-interface-identity")
    if operation == "renew_dhcp" and any(char in interface for char in "*?"):
        raise ValueError("wildcards-are-not-valid-for-ipconfig")

    name = _powershell_single_quote(interface)
    guid = _powershell_single_quote(stable_id.strip("{}").lower())
    identity = (
        f"$name={name}; $guid=[Guid]{guid}; "
        "$adapter=@(Get-NetAdapter | Where-Object { "
        "$_.Name -ceq $name -and $_.InterfaceGuid -eq $guid }); "
        "if ($adapter.Count -ne 1) { exit 31 }; "
    )
    if operation == "flush_dns":
        body = "Clear-DnsClientCache;"
    elif operation in {"adapter_enable", "enable_wifi"}:
        body = identity + "$adapter[0] | Enable-NetAdapter -Confirm:$false;"
    elif operation == "adapter_disable":
        body = identity + "$adapter[0] | Disable-NetAdapter -Confirm:$false;"
    else:
        body = (
            identity + "$map=New-Object VareduraNative+IP_ADAPTER_INDEX_MAP; "
            "$map.Index=[int]$adapter[0].ifIndex; $map.Name=''; "
            "$renew=[VareduraNative]::IpRenewAddress([ref]$map); "
            "if ($renew -ne 0) { exit 32 }; "
            "$ipconfig=Join-Path ([Environment]::GetFolderPath('System')) "
            "'ipconfig.exe'; & $ipconfig /renew6 $name | Out-Null; "
            "if ($LASTEXITCODE -ne 0) { exit 33 };"
        )

    return (
        "$ErrorActionPreference='Stop'; "
        "Add-Type -TypeDefinition @'\n" + _WINDOWS_JOB_AND_IP_HELPER + "\n'@\n"
        "$job=[VareduraNative]::CreateJobObject([IntPtr]::Zero,$null); "
        "if ($job -eq [IntPtr]::Zero) { exit 34 }; "
        "$limits=New-Object "
        "VareduraNative+JOBOBJECT_EXTENDED_LIMIT_INFORMATION; "
        "$basic=$limits.BasicLimitInformation; $basic.LimitFlags=0x2000; "
        "$limits.BasicLimitInformation=$basic; "
        "$size=[Runtime.InteropServices.Marshal]::SizeOf($limits); "
        "$memory=[Runtime.InteropServices.Marshal]::AllocHGlobal($size); "
        "try { "
        "[Runtime.InteropServices.Marshal]::StructureToPtr($limits,$memory,$false); "
        "if (-not [VareduraNative]::SetInformationJobObject($job,9,$memory,$size)) "
        "{ exit 35 }; "
        "if (-not [VareduraNative]::AssignProcessToJobObject("
        "$job,[Diagnostics.Process]::GetCurrentProcess().Handle)) { exit 36 }; "
        + body
        + " } finally { [Runtime.InteropServices.Marshal]::FreeHGlobal($memory) }; "
        "exit 0"
    )


def _kill_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    children = []
    try:
        import psutil

        parent = psutil.Process(process.pid)
        children = parent.children(recursive=True)
        for child in reversed(children):
            try:
                child.terminate()
            except (psutil.Error, OSError):
                pass
        _, alive = psutil.wait_procs(children, timeout=0.35)
        for child in alive:
            try:
                child.kill()
            except (psutil.Error, OSError):
                pass
    except (ImportError, OSError, RuntimeError):
        pass
    try:
        process.terminate()
        process.wait(timeout=0.45)
    except (OSError, subprocess.TimeoutExpired):
        try:
            process.kill()
            process.wait(timeout=0.45)
        except (OSError, subprocess.TimeoutExpired):
            pass


class SubprocessRepairRunner:
    """Run allow-listed commands without a shell or password interception.

    On Unix, ``sudo --`` inherits the user's terminal, so authentication (when
    required) is handled by sudo itself.  On Windows, elevated actions are
    refused unless the current process is already elevated; the UI may inject a
    one-shot UAC helper implementing :class:`RepairRunner`.
    """

    def __init__(
        self,
        *,
        platform_name: str | None = None,
        is_windows_admin: Callable[[], bool] = _is_windows_admin,
    ) -> None:
        self.platform_name = _normalize_platform(platform_name)
        self.is_windows_admin = is_windows_admin

    def _run_windows_helper(
        self,
        args: tuple[str, ...],
        *,
        timeout: float,
        cancel_event: threading.Event | None,
    ) -> CommandResult:
        started = time.monotonic()
        operation = args[1] if len(args) > 1 else ""
        interface = args[2] if len(args) > 2 else ""
        stable_id = args[3] if len(args) > 3 else ""
        if operation not in _WINDOWS_HELPER_OPERATIONS or len(args) > 4:
            return CommandResult(
                args,
                None,
                stderr="helper-operation-not-allowed",
                duration_ms=(time.monotonic() - started) * 1000,
            )
        try:
            script = _windows_elevated_script(operation, interface, stable_id)
            powershell = _windows_system_powershell()
        except (OSError, ValueError) as exc:
            return CommandResult(
                args,
                None,
                stderr=str(exc)[:4096],
                duration_ms=(time.monotonic() - started) * 1000,
            )
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        powershell_command = (
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-EncodedCommand",
            encoded,
        )
        if self.is_windows_admin():
            result = self.run(
                powershell_command,
                timeout=timeout,
                cancel_event=cancel_event,
                elevated=False,
            )
            return CommandResult(
                args,
                result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                timed_out=result.timed_out,
                cancelled=result.cancelled,
                duration_ms=result.duration_ms,
            )

        process_handle = None
        kernel32 = None
        cancelled = False
        timed_out = False
        returncode: int | None = None
        try:
            import ctypes.wintypes as wintypes

            class ShellExecuteInfo(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("fMask", ctypes.c_ulong),
                    ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR),
                    ("lpFile", wintypes.LPCWSTR),
                    ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR),
                    ("nShow", ctypes.c_int),
                    ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p),
                    ("lpClass", wintypes.LPCWSTR),
                    ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD),
                    ("hIconOrMonitor", wintypes.HANDLE),
                    ("hProcess", wintypes.HANDLE),
                ]

            info = ShellExecuteInfo()
            info.cbSize = ctypes.sizeof(info)
            info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
            info.lpVerb = "runas"
            info.lpFile = powershell
            info.lpParameters = subprocess.list2cmdline(list(powershell_command[1:]))
            info.nShow = 0
            shell32 = ctypes.WinDLL("shell32", use_last_error=True)
            shell32.ShellExecuteExW.argtypes = [ctypes.POINTER(ShellExecuteInfo)]
            shell32.ShellExecuteExW.restype = wintypes.BOOL
            if not shell32.ShellExecuteExW(ctypes.byref(info)):
                error = ctypes.get_last_error()
                reason = "elevation-denied" if error == 1223 else f"uac-error-{error}"
                return CommandResult(
                    args,
                    None,
                    stderr=reason,
                    duration_ms=(time.monotonic() - started) * 1000,
                )
            process_handle = info.hProcess
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            kernel32.WaitForSingleObject.restype = wintypes.DWORD
            kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
            kernel32.TerminateProcess.restype = wintypes.BOOL
            kernel32.GetExitCodeProcess.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.DWORD),
            ]
            kernel32.GetExitCodeProcess.restype = wintypes.BOOL
            kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
            kernel32.CloseHandle.restype = wintypes.BOOL
            # UAC decision time belongs to the user and must not consume the
            # bounded execution budget of the already-approved helper.
            deadline = time.monotonic() + timeout
            while True:
                wait_status = kernel32.WaitForSingleObject(process_handle, 25)
                if wait_status == 0:
                    break
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    kernel32.TerminateProcess(process_handle, 1)
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    kernel32.TerminateProcess(process_handle, 1)
                    break
            kernel32.WaitForSingleObject(process_handle, 500)
            exit_code = wintypes.DWORD()
            if kernel32.GetExitCodeProcess(process_handle, ctypes.byref(exit_code)):
                returncode = int(exit_code.value)
        except (OSError, ValueError) as exc:
            return CommandResult(
                args,
                None,
                stderr=str(exc)[:4096],
                duration_ms=(time.monotonic() - started) * 1000,
            )
        finally:
            if process_handle:
                try:
                    if kernel32 is not None:
                        kernel32.CloseHandle(process_handle)
                except OSError:
                    pass

        if cancelled or timed_out:
            returncode = None
        message = "ok" if returncode == 0 else f"helper-exit-{returncode}"
        return CommandResult(
            args,
            returncode,
            stdout=message if returncode == 0 else "",
            stderr=message if returncode != 0 else "",
            timed_out=timed_out,
            cancelled=cancelled,
            duration_ms=(time.monotonic() - started) * 1000,
        )

    def run(
        self,
        args: tuple[str, ...],
        *,
        timeout: float,
        cancel_event: threading.Event | None = None,
        elevated: bool = False,
    ) -> CommandResult:
        started = time.monotonic()
        command = tuple(args)
        force_checkpoint_restore = bool(
            self.platform_name == "linux"
            and len(command) >= 3
            and command[:3] == ("nmcli", "device", "checkpoint")
        )
        if (
            elevated
            and self.platform_name == "windows"
            and command
            and command[0] == _WINDOWS_HELPER
        ):
            return self._run_windows_helper(
                command,
                timeout=timeout,
                cancel_event=cancel_event,
            )
        if elevated and self.platform_name == "windows" and not self.is_windows_admin():
            return CommandResult(
                command,
                None,
                stderr="elevation-required",
                duration_ms=(time.monotonic() - started) * 1000,
            )
        if elevated and self.platform_name in {"linux", "darwin"}:
            command = ("/usr/bin/sudo", "--", *command)

        startupinfo = None
        creationflags = 0
        if self.platform_name == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process: subprocess.Popen[str] | None = None
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE if force_checkpoint_restore else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=False,
                startupinfo=startupinfo,
                creationflags=creationflags,
                env={**os.environ, "LC_ALL": "C"}
                if self.platform_name == "linux"
                else None,
            )
            if force_checkpoint_restore and process.stdin is not None:
                # A reconnect has no intended persistent configuration change.
                # Queueing an explicit negative answer makes NetworkManager
                # restore its checkpoint as soon as the child command exits,
                # without racing Textual for terminal input.
                process.stdin.write("No\n")
                process.stdin.flush()
                process.stdin.close()
                process.stdin = None
        except (OSError, ValueError) as exc:
            if process is not None:
                _kill_process(process)
            return CommandResult(
                command,
                None,
                stderr=str(exc)[:4096],
                duration_ms=(time.monotonic() - started) * 1000,
            )

        deadline = started + timeout
        cancelled = False
        timed_out = False
        while process.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                _kill_process(process)
                break
            if time.monotonic() >= deadline:
                timed_out = True
                _kill_process(process)
                break
            time.sleep(0.025)
        try:
            stdout, stderr = process.communicate(timeout=0.25)
        except subprocess.TimeoutExpired:
            _kill_process(process)
            try:
                stdout, stderr = process.communicate(timeout=0.5)
            except subprocess.TimeoutExpired:
                stdout, stderr = "", "process-tree-did-not-exit"
        return CommandResult(
            command,
            process.returncode,
            stdout[:16_384],
            stderr[:16_384],
            timed_out,
            cancelled,
            (time.monotonic() - started) * 1000,
        )


def _action_id(kind: RepairKind, system: str, interface: str | None = None) -> str:
    suffix = interface or "system"
    return f"{kind.value}:{system}:{suffix}"


def _selected_interface(report: DiagnosisReport) -> NetworkInterface | None:
    return report.snapshot.selected_interface


def _wifi_interface(report: DiagnosisReport) -> NetworkInterface | None:
    candidates = [
        item
        for item in report.snapshot.interfaces
        if (_WIFI_NAME.search(item.name) or _WIFI_NAME.search(item.service_name or ""))
        and not item.is_virtual
    ]
    candidates.sort(key=lambda item: (item.is_up, item.name.casefold()))
    return candidates[0] if candidates else None


def _disruptive_block_reason(report: DiagnosisReport) -> str | None:
    snapshot = report.snapshot
    if snapshot.remote_session:
        return "blocked during a remote session to avoid losing access"
    if snapshot.vpn_active:
        return "blocked while a VPN or tunnel is active"
    if snapshot.proxy.has_pac:
        return "blocked on a network controlled by PAC/WPAD policy"
    if snapshot.dot1x_suspected:
        return "blocked on a possible 802.1X/domain-managed connection"
    if snapshot.managed_network:
        return "blocked on a managed institutional connection"
    interface = snapshot.selected_interface
    if interface and (interface.is_virtual or interface.is_loopback):
        return "virtual and loopback interfaces cannot be reconfigured"
    return None


def _portal_url(report: DiagnosisReport) -> str | None:
    probe = report.probe(ProbeKind.CAPTIVE_PORTAL)
    candidate = str(probe.details.get("final_url", "")) if probe else ""
    try:
        parsed = urllib.parse.urlsplit(candidate)
    except ValueError:
        return None
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return None
    host = f"[{parsed.hostname}]" if ":" in parsed.hostname else parsed.hostname
    port = f":{parsed.port}" if parsed.port else ""
    return urllib.parse.urlunsplit(
        (parsed.scheme, f"{host}{port}", parsed.path or "/", parsed.query, "")
    )


def _flush_preview(system: str) -> tuple[tuple[str, ...], ...]:
    if system == "windows":
        return ((_WINDOWS_HELPER, "flush_dns"),)
    if system == "darwin":
        return (("/usr/bin/dscacheutil", "-flushcache"),)
    return (("resolvectl", "flush-caches"),)


def _renew_preview(
    system: str, interface: NetworkInterface | str
) -> tuple[tuple[str, ...], ...]:
    name = interface.name if isinstance(interface, NetworkInterface) else interface
    if system == "windows":
        stable_id = (
            interface.stable_id if isinstance(interface, NetworkInterface) else ""
        )
        return ((_WINDOWS_HELPER, "renew_dhcp", name, stable_id or ""),)
    if system == "darwin":
        return (
            (
                "/usr/bin/osascript",
                "-l",
                "JavaScript",
                "-e",
                _MACOS_DHCP_REFRESH_SCRIPT,
                name,
            ),
        )
    return (("networkctl", "renew", name),)


def _reconnect_preview(
    system: str,
    interface: NetworkInterface,
) -> tuple[tuple[tuple[str, ...], ...], tuple[tuple[str, ...], ...]]:
    if system == "windows":
        return (
            (
                (
                    _WINDOWS_HELPER,
                    "adapter_disable",
                    interface.name,
                    interface.stable_id or "",
                ),
            ),
            (
                (
                    _WINDOWS_HELPER,
                    "adapter_enable",
                    interface.name,
                    interface.stable_id or "",
                ),
            ),
        )
    if system == "darwin":
        service = interface.service_name or "<network-service>"
        prefix = ("/usr/sbin/networksetup", "-setnetworkserviceenabled", service)
        return ((prefix + ("off",),), (prefix + ("on",),))
    connection_uuid = interface.connection_uuid or "<active-connection-uuid>"
    return (
        (
            (
                "nmcli",
                "device",
                "checkpoint",
                "--timeout",
                "20",
                interface.name,
                "--",
                "nmcli",
                "--wait",
                "10",
                "connection",
                "down",
                "uuid",
                connection_uuid,
            ),
        ),
        (),
    )


def list_repair_actions(
    report: DiagnosisReport,
    *,
    platform_name: str | None = None,
    app_ca_file: str | None = None,
    max_report_age: float = 30.0,
) -> tuple[RepairAction, ...]:
    """Return individually confirmable actions derived from a diagnosis."""

    system = _normalize_platform(platform_name or report.snapshot.platform)
    actions: list[RepairAction] = [
        RepairAction(
            _action_id(RepairKind.REFRESH_STATUS, system),
            RepairKind.REFRESH_STATUS,
            "Run diagnostics again",
            "Refresh local and external evidence without changing system settings.",
            "application",
            system,
            requires_confirmation=False,
            impact=RepairImpact.NONE,
        )
    ]
    stale_reason = (
        "diagnosis is stale; refresh it before repairing"
        if report.age_seconds() > max_report_age
        else None
    )

    portal = _portal_url(report)
    if report.state is NetworkState.CAPTIVE_PORTAL and portal:
        actions.append(
            RepairAction(
                _action_id(RepairKind.OPEN_CAPTIVE_PORTAL, system),
                RepairKind.OPEN_CAPTIVE_PORTAL,
                "Open captive portal",
                "Open the detected sign-in page in the default browser.",
                portal,
                system,
                eligible=not stale_reason,
                blocked_reason=stale_reason,
                requires_elevation=False,
                impact=RepairImpact.NONE,
            )
        )

    if report.state in {
        NetworkState.LIMITED,
        NetworkState.LOCAL_ONLY,
        NetworkState.OFFLINE,
        NetworkState.UNKNOWN,
        NetworkState.TLS_POLICY_BLOCKED,
    }:
        actions.append(
            RepairAction(
                _action_id(RepairKind.FLUSH_DNS, system),
                RepairKind.FLUSH_DNS,
                "Clear DNS cache",
                "Clear only the operating-system resolver cache.",
                "system DNS cache",
                system,
                eligible=not stale_reason,
                blocked_reason=stale_reason,
                requires_elevation=True,
                impact=RepairImpact.LOW,
                command_preview=_flush_preview(system),
                partial=system == "darwin",
            )
        )

    interface = _selected_interface(report)
    disruptive_states = {
        NetworkState.LIMITED,
        NetworkState.LOCAL_ONLY,
        NetworkState.OFFLINE,
        NetworkState.UNKNOWN,
    }
    if (
        interface
        and _valid_interface_name(interface.name)
        and report.state in disruptive_states
    ):
        stable_identity_reason = (
            "the Windows adapter GUID could not be identified"
            if system == "windows" and not interface.stable_id
            else None
        )
        disruptive_reason = (
            stale_reason or _disruptive_block_reason(report) or stable_identity_reason
        )
        dhcp_reason = (
            None
            if interface.dhcp_enabled is True
            else (
                "the interface uses static addressing"
                if interface.dhcp_enabled is False
                else "DHCP could not be confirmed for the selected interface"
            )
        )
        actions.extend(
            (
                RepairAction(
                    _action_id(RepairKind.RENEW_DHCP, system, interface.name),
                    RepairKind.RENEW_DHCP,
                    "Renew DHCP configuration",
                    "Request fresh addressing for the selected adapter only.",
                    interface.name,
                    system,
                    interface.name,
                    eligible=not (disruptive_reason or dhcp_reason),
                    blocked_reason=disruptive_reason or dhcp_reason,
                    requires_elevation=True,
                    impact=RepairImpact.MEDIUM,
                    command_preview=_renew_preview(system, interface),
                ),
            )
        )
        commands, rollback = _reconnect_preview(system, interface)
        mac_service_reason = (
            "the macOS network service for this adapter could not be identified"
            if system == "darwin" and not interface.service_name
            else None
        )
        linux_connection_reason = (
            "the active NetworkManager connection UUID could not be identified"
            if system == "linux" and not interface.connection_uuid
            else None
        )
        reconnect_reason = (
            disruptive_reason or mac_service_reason or linux_connection_reason
        )
        actions.append(
            RepairAction(
                _action_id(RepairKind.RECONNECT_INTERFACE, system, interface.name),
                RepairKind.RECONNECT_INTERFACE,
                "Reconnect selected adapter",
                "Temporarily reconnect one adapter and always attempt restoration.",
                interface.service_name or interface.name,
                system,
                interface.name,
                eligible=not reconnect_reason,
                blocked_reason=reconnect_reason,
                requires_elevation=True,
                impact=RepairImpact.MEDIUM,
                command_preview=commands,
                rollback_preview=rollback,
            )
        )

    wifi = _wifi_interface(report)
    if wifi and not wifi.is_up and _valid_interface_name(wifi.name):
        reason = (
            stale_reason
            or _disruptive_block_reason(report)
            or (
                "the Windows adapter GUID could not be identified"
                if system == "windows" and not wifi.stable_id
                else None
            )
        )
        if system == "windows":
            preview = (
                (
                    _WINDOWS_HELPER,
                    "enable_wifi",
                    wifi.name,
                    wifi.stable_id or "",
                ),
            )
        elif system == "darwin":
            preview = (("/usr/sbin/networksetup", "-setairportpower", wifi.name, "on"),)
        else:
            preview = (("nmcli", "radio", "wifi", "on"),)
        actions.append(
            RepairAction(
                _action_id(RepairKind.ENABLE_WIFI, system, wifi.name),
                RepairKind.ENABLE_WIFI,
                "Enable Wi-Fi",
                "Enable the detected wireless adapter without changing profiles.",
                wifi.name,
                system,
                wifi.name,
                eligible=not reason,
                blocked_reason=reason,
                requires_elevation=True,
                impact=RepairImpact.LOW,
                command_preview=preview,
            )
        )

    if app_ca_file is not None and report.state is NetworkState.TLS_POLICY_BLOCKED:
        actions.append(
            RepairAction(
                _action_id(RepairKind.CONFIGURE_APP_CA, system),
                RepairKind.CONFIGURE_APP_CA,
                "Use a CA supplied by IT in Varedura",
                "Validate a CA file for Varedura only; the system trust store is not modified.",
                "application TLS context",
                system,
                eligible=not stale_reason,
                blocked_reason=stale_reason,
                requires_elevation=False,
                impact=RepairImpact.LOW,
                ca_file=app_ca_file,
            )
        )
    return tuple(actions)


def list_repair_guidance(report: DiagnosisReport) -> tuple[RepairGuidance, ...]:
    """Non-executable guidance for operations that are unsafe to automate."""

    items = [
        RepairGuidance(
            "Do not reset the complete network stack automatically",
            "Winsock, TCP/IP and full network resets can remove institutional or VPN configuration.",
        ),
        RepairGuidance(
            "Do not change DNS, proxy, routes, MTU, firewall or IPv6 automatically",
            "Those settings may be enforced by the provider, FortiGate, domain policy or MDM.",
        ),
        RepairGuidance(
            "Do not disable VPN, FortiClient or security software",
            "Ask the institution's IT team to validate its policy and certificates.",
        ),
        RepairGuidance(
            "Never trust Fortinet_CA_Untrusted",
            "Only use a CA file explicitly supplied by the institution's IT team.",
        ),
    ]
    if report.snapshot.remote_session:
        items.insert(
            0,
            RepairGuidance(
                "Keep the current connection active",
                "Reconnect and DHCP actions are blocked because this is a remote session.",
                False,
            ),
        )
    return tuple(items)


def _der_tlvs(data: bytes) -> list[tuple[int, bytes]]:
    """Decode one DER level with strict bounds and no indefinite lengths."""

    items: list[tuple[int, bytes]] = []
    offset = 0
    while offset < len(data):
        tag = data[offset]
        offset += 1
        if offset >= len(data):
            raise ValueError("truncated DER certificate")
        first_length = data[offset]
        offset += 1
        if first_length & 0x80:
            width = first_length & 0x7F
            if width == 0 or width > 4 or offset + width > len(data):
                raise ValueError("invalid DER length")
            length = int.from_bytes(data[offset : offset + width], "big")
            offset += width
        else:
            length = first_length
        end = offset + length
        if end > len(data):
            raise ValueError("truncated DER value")
        items.append((tag, data[offset:end]))
        offset = end
    return items


def _certificate_is_ca(der: bytes) -> bool:
    """Require the X.509 BasicConstraints extension with ``CA=true``."""

    basic_constraints_oid = b"\x55\x1d\x13"  # 2.5.29.19

    def visit(blob: bytes, depth: int = 0) -> bool:
        if depth > 12:
            return False
        children = _der_tlvs(blob)
        for index, (tag, value) in enumerate(children):
            if tag != 0x06 or value != basic_constraints_oid:
                continue
            extension_value = next(
                (
                    candidate
                    for candidate_tag, candidate in children[index + 1 :]
                    if candidate_tag == 0x04
                ),
                None,
            )
            if extension_value is None:
                continue
            wrapped = _der_tlvs(extension_value)
            if len(wrapped) != 1 or wrapped[0][0] != 0x30:
                continue
            constraints = _der_tlvs(wrapped[0][1])
            return bool(
                constraints
                and constraints[0][0] == 0x01
                and constraints[0][1]
                and constraints[0][1] != b"\x00"
            )
        for tag, value in children:
            if tag & 0x20 and visit(value, depth + 1):
                return True
        return False

    top = _der_tlvs(der)
    return len(top) == 1 and top[0][0] == 0x30 and visit(top[0][1])


def _normalized_ca_pem(material: bytes) -> tuple[bytes, bytes]:
    blocks = re.findall(
        rb"-----BEGIN CERTIFICATE-----\s*(.*?)\s*-----END CERTIFICATE-----",
        material,
        flags=re.DOTALL,
    )
    if b"-----BEGIN CERTIFICATE-----" in material:
        if len(blocks) != 1:
            raise ValueError("CA bundles are not accepted; select one CA certificate")
        try:
            der = base64.b64decode(re.sub(rb"\s+", b"", blocks[0]), validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("invalid PEM certificate") from exc
    else:
        der = material
    try:
        pem = ssl.DER_cert_to_PEM_cert(der).encode("ascii")
    except (ValueError, ssl.SSLError) as exc:
        raise ValueError("invalid X.509 certificate") from exc
    if not _certificate_is_ca(der):
        raise ValueError("certificate must declare BasicConstraints CA=true")
    return pem, der


def _store_app_ca(material: bytes, directory: Path) -> str:
    directory = directory.expanduser().resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    digest = hashlib.sha256(material).hexdigest()
    destination = directory / f"{digest}.pem"
    try:
        descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        if destination.is_file() and destination.read_bytes() == material:
            return str(destination)
        raise ValueError(
            "stored CA fingerprint collision or modified CA file"
        ) from None
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(material)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return str(destination)


def _validate_app_ca(
    path_value: str,
    *,
    store_directory: Path | None = None,
) -> str:
    path = Path(path_value).expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > 5 * 1024 * 1024:
        raise ValueError("CA file must be a regular file no larger than 5 MiB")
    if path.suffix.casefold() not in {".pem", ".crt", ".cer"}:
        raise ValueError("CA file must use .pem, .crt or .cer")
    material = path.read_bytes()
    if (
        b"fortinet_ca_untrusted" in material.lower()
        or "fortinet_ca_untrusted" in str(path).casefold()
    ):
        raise ValueError("Fortinet_CA_Untrusted must never be trusted")
    normalized, _der = _normalized_ca_pem(material)
    try:
        certificate_description = str(
            ssl._ssl._test_decode_cert(str(path))  # type: ignore[attr-defined]
        ).casefold()
    except (AttributeError, OSError, ssl.SSLError, ValueError):
        certificate_description = ""
    if "fortinet_ca_untrusted" in certificate_description:
        raise ValueError("Fortinet_CA_Untrusted must never be trusted")
    ssl.create_default_context(cadata=normalized.decode("ascii"))
    destination = store_directory or (Path.home() / ".varedura" / "certs")
    return _store_app_ca(normalized, destination)


class RepairExecutor:
    def __init__(
        self,
        *,
        platform_name: str | None = None,
        runner: RepairRunner | None = None,
        post_test: Callable[[], DiagnosisReport] | None = None,
        command_exists: Callable[[str], str | None] = shutil.which,
        browser_open: Callable[[str], bool] = webbrowser.open,
        preflight_snapshot: Callable[[], NetworkSnapshot] | None = None,
        ca_store_directory: Path | None = None,
        max_report_age: float = 30.0,
    ) -> None:
        self.platform_name = _normalize_platform(platform_name)
        self.runner = runner or SubprocessRepairRunner(platform_name=self.platform_name)
        self.post_test = post_test
        self.command_exists = command_exists
        self.browser_open = browser_open
        self.preflight_snapshot = preflight_snapshot
        self.ca_store_directory = ca_store_directory
        self.max_report_age = max_report_age

    def _result(
        self,
        action: RepairAction,
        status: RepairStatus,
        message: str,
        started: float,
        *,
        commands: tuple[CommandResult, ...] = (),
        rollback_attempted: bool = False,
        rollback_succeeded: bool | None = None,
        post_report: DiagnosisReport | None = None,
        app_ca_file: str | None = None,
    ) -> RepairResult:
        return RepairResult(
            action,
            status,
            message,
            (time.monotonic() - started) * 1000,
            commands,
            rollback_attempted,
            rollback_succeeded,
            post_report,
            app_ca_file,
        )

    def _run(
        self,
        args: tuple[str, ...],
        *,
        timeout: float,
        cancel_event: threading.Event | None,
        elevated: bool,
    ) -> CommandResult:
        return self.runner.run(
            args,
            timeout=timeout,
            cancel_event=cancel_event,
            elevated=elevated,
        )

    @staticmethod
    def _command_status(result: CommandResult) -> RepairStatus:
        if result.cancelled:
            return RepairStatus.CANCELLED
        if result.returncode is None and any(
            marker in result.stderr
            for marker in ("elevation-required", "elevation-denied")
        ):
            return RepairStatus.ELEVATION_REQUIRED
        return RepairStatus.SUCCEEDED if result.returncode == 0 else RepairStatus.FAILED

    def _execute_flush(
        self,
        action: RepairAction,
        cancel_event: threading.Event | None,
    ) -> tuple[RepairStatus, tuple[CommandResult, ...], bool, bool | None]:
        command = _flush_preview(self.platform_name)[0]
        if self.platform_name == "linux" and not self.command_exists(command[0]):
            failure = CommandResult(command, None, stderr="resolvectl-unavailable")
            return RepairStatus.BLOCKED, (failure,), False, None
        result = self._run(
            command,
            timeout=8.0,
            cancel_event=cancel_event,
            elevated=action.requires_elevation,
        )
        return self._command_status(result), (result,), False, None

    def _execute_renew(
        self,
        action: RepairAction,
        report: DiagnosisReport,
        cancel_event: threading.Event | None,
    ) -> tuple[RepairStatus, tuple[CommandResult, ...], bool, bool | None]:
        assert action.interface is not None
        if self.platform_name == "windows":
            result = self._run(
                action.command_preview[0],
                timeout=25.0,
                cancel_event=cancel_event,
                elevated=True,
            )
            return self._command_status(result), (result,), False, None
        if self.platform_name == "darwin":
            result = self._run(
                action.command_preview[0],
                timeout=20.0,
                cancel_event=cancel_event,
                elevated=True,
            )
            return self._command_status(result), (result,), False, None
        try:
            interface_index = socket.if_nametoindex(action.interface)
        except OSError:
            interface_index = -1
        managed_by_networkd = (
            interface_index > 0
            and Path(f"/run/systemd/netif/links/{interface_index}").exists()
        )
        if self.command_exists("networkctl") and managed_by_networkd:
            result = self._run(
                ("networkctl", "renew", action.interface),
                timeout=20.0,
                cancel_event=cancel_event,
                elevated=True,
            )
            return self._command_status(result), (result,), False, None
        # NetworkManager has no standalone DHCP-renew verb.  Its protected
        # reconnect path is used and always attempts to restore the device.
        return self._execute_reconnect(action, report, cancel_event)

    def _execute_reconnect(
        self,
        action: RepairAction,
        report: DiagnosisReport,
        cancel_event: threading.Event | None,
    ) -> tuple[RepairStatus, tuple[CommandResult, ...], bool, bool | None]:
        assert action.interface is not None
        interface = report.snapshot.selected_interface
        if interface is None:
            return RepairStatus.BLOCKED, (), False, None
        if self.platform_name == "linux" and not interface.connection_uuid:
            failure = CommandResult(
                ("nmcli",),
                None,
                stderr="active-networkmanager-connection-uuid-unavailable",
            )
            return RepairStatus.BLOCKED, (failure,), False, None
        commands, rollback_commands = _reconnect_preview(self.platform_name, interface)
        if self.platform_name == "linux" and not self.command_exists("nmcli"):
            failure = CommandResult(commands[0], None, stderr="nmcli-unavailable")
            return RepairStatus.BLOCKED, (failure,), False, None

        if self.platform_name == "linux":
            # The command disconnects the exact active profile inside a
            # NetworkManager checkpoint.  SubprocessRepairRunner queues "No"
            # on stdin, so the checkpoint itself performs the restoration and
            # no broad ``device connect`` fallback can create a new profile.
            try:
                result = self._run(
                    commands[0],
                    timeout=30.0,
                    cancel_event=cancel_event,
                    elevated=action.requires_elevation,
                )
            except Exception as exc:
                result = CommandResult(commands[0], None, stderr=str(exc)[:4096])
            rollback_succeeded = (
                None if result.cancelled or result.timed_out else result.returncode == 0
            )
            return (
                self._command_status(result),
                (result,),
                True,
                rollback_succeeded,
            )

        results: list[CommandResult] = []
        rollback_attempted = False
        rollback_succeeded: bool | None = None
        status = RepairStatus.FAILED
        try:
            try:
                first = self._run(
                    commands[0],
                    timeout=15.0,
                    cancel_event=cancel_event,
                    elevated=action.requires_elevation,
                )
            except Exception as exc:
                first = CommandResult(
                    commands[0],
                    None,
                    stderr=str(exc)[:4096],
                )
            results.append(first)
            status = self._command_status(first)
        finally:
            rollback_attempted = True
            # Restoration ignores user cancellation: once an adapter may have
            # been disabled, re-enabling it is the mandatory rollback.
            try:
                rollback = self._run(
                    rollback_commands[0],
                    timeout=25.0,
                    cancel_event=None,
                    elevated=action.requires_elevation,
                )
            except Exception as exc:
                rollback = CommandResult(
                    rollback_commands[0],
                    None,
                    stderr=str(exc)[:4096],
                )
            results.append(rollback)
            rollback_succeeded = rollback.returncode == 0
        if status is RepairStatus.SUCCEEDED and not rollback_succeeded:
            status = self._command_status(results[-1])
        return status, tuple(results), rollback_attempted, rollback_succeeded

    def _execute_wifi(
        self,
        action: RepairAction,
        cancel_event: threading.Event | None,
    ) -> tuple[RepairStatus, tuple[CommandResult, ...], bool, bool | None]:
        assert action.interface is not None
        if self.platform_name == "windows":
            command = action.command_preview[0]
        elif self.platform_name == "darwin":
            command = (
                "/usr/sbin/networksetup",
                "-setairportpower",
                action.interface,
                "on",
            )
        else:
            command = ("nmcli", "radio", "wifi", "on")
            if not self.command_exists("nmcli"):
                failure = CommandResult(command, None, stderr="nmcli-unavailable")
                return RepairStatus.BLOCKED, (failure,), False, None
        result = self._run(
            command,
            timeout=15.0,
            cancel_event=cancel_event,
            elevated=action.requires_elevation,
        )
        return self._command_status(result), (result,), False, None

    def execute(
        self,
        action: RepairAction,
        report: DiagnosisReport,
        *,
        confirmed: bool = False,
        cancel_event: threading.Event | None = None,
    ) -> RepairResult:
        """Execute one canonical action and optionally perform a post-test."""

        started = time.monotonic()
        canonical = next(
            (
                item
                for item in list_repair_actions(
                    report,
                    platform_name=self.platform_name,
                    app_ca_file=action.ca_file,
                    max_report_age=self.max_report_age,
                )
                if item.action_id == action.action_id and item.kind is action.kind
            ),
            None,
        )
        if canonical is None:
            return self._result(
                action,
                RepairStatus.BLOCKED,
                "The action is not valid for the current diagnosis.",
                started,
            )
        action = canonical
        if not action.eligible:
            return self._result(
                action,
                RepairStatus.BLOCKED,
                action.blocked_reason or "The action is blocked by preflight checks.",
                started,
            )
        if action.requires_confirmation and not confirmed:
            return self._result(
                action,
                RepairStatus.NOT_CONFIRMED,
                "Individual confirmation is required.",
                started,
            )
        if cancel_event is not None and cancel_event.is_set():
            return self._result(
                action,
                RepairStatus.CANCELLED,
                "The action was cancelled before it started.",
                started,
            )

        disruptive = action.kind in {
            RepairKind.RENEW_DHCP,
            RepairKind.RECONNECT_INTERFACE,
            RepairKind.ENABLE_WIFI,
        }
        if disruptive and self.preflight_snapshot is not None:
            try:
                fresh = self.preflight_snapshot()
            except Exception as exc:
                return self._result(
                    action,
                    RepairStatus.BLOCKED,
                    f"Recent preflight failed: {exc}",
                    started,
                )
            if (
                fresh.remote_session
                or fresh.vpn_active
                or fresh.fortinet_client_active
                or fresh.proxy.has_pac
                or fresh.dot1x_suspected
                or fresh.managed_network
            ):
                return self._result(
                    action,
                    RepairStatus.BLOCKED,
                    "Recent preflight detected a managed, VPN, PAC, 802.1X, or remote session.",
                    started,
                )
            interface_names = {item.name for item in fresh.interfaces}
            if action.interface not in interface_names:
                return self._result(
                    action,
                    RepairStatus.BLOCKED,
                    "The exact interface changed after diagnosis.",
                    started,
                )
            fresh_interface = next(
                (item for item in fresh.interfaces if item.name == action.interface),
                None,
            )
            original_interface = next(
                (
                    item
                    for item in report.snapshot.interfaces
                    if item.name == action.interface
                ),
                None,
            )
            if self.platform_name == "windows":
                if (
                    original_interface is None
                    or fresh_interface is None
                    or not original_interface.stable_id
                    or fresh_interface.stable_id != original_interface.stable_id
                ):
                    return self._result(
                        action,
                        RepairStatus.BLOCKED,
                        "The Windows adapter GUID changed after diagnosis.",
                        started,
                    )
            if (
                self.platform_name == "linux"
                and action.kind
                in {RepairKind.RENEW_DHCP, RepairKind.RECONNECT_INTERFACE}
                and original_interface is not None
                and original_interface.connection_uuid
                and (
                    fresh_interface is None
                    or fresh_interface.connection_uuid
                    != original_interface.connection_uuid
                )
            ):
                return self._result(
                    action,
                    RepairStatus.BLOCKED,
                    "The active NetworkManager profile changed after diagnosis.",
                    started,
                )
            if action.kind is RepairKind.RENEW_DHCP and (
                fresh_interface is None or fresh_interface.dhcp_enabled is not True
            ):
                return self._result(
                    action,
                    RepairStatus.BLOCKED,
                    "Recent preflight could not confirm DHCP on the selected interface.",
                    started,
                )
            if (
                action.kind
                in {
                    RepairKind.RENEW_DHCP,
                    RepairKind.RECONNECT_INTERFACE,
                }
                and fresh.active_interface != action.interface
            ):
                return self._result(
                    action,
                    RepairStatus.BLOCKED,
                    "The active interface changed after diagnosis.",
                    started,
                )
            if cancel_event is not None and cancel_event.is_set():
                return self._result(
                    action,
                    RepairStatus.CANCELLED,
                    "The action was cancelled during preflight.",
                    started,
                )

        mutation_locked = action.kind is not RepairKind.REFRESH_STATUS
        if mutation_locked and not _REPAIR_MUTATION_LOCK.acquire(blocking=False):
            return self._result(
                action,
                RepairStatus.BLOCKED,
                "Another repair action is already running.",
                started,
            )

        commands: tuple[CommandResult, ...] = ()
        rollback_attempted = False
        rollback_succeeded: bool | None = None
        app_ca_file = None
        try:
            if action.kind is RepairKind.REFRESH_STATUS:
                status = RepairStatus.SUCCEEDED
            elif action.kind is RepairKind.OPEN_CAPTIVE_PORTAL:
                portal = _portal_url(report)
                status = (
                    RepairStatus.SUCCEEDED
                    if portal and self.browser_open(portal)
                    else RepairStatus.FAILED
                )
            elif action.kind is RepairKind.FLUSH_DNS:
                status, commands, rollback_attempted, rollback_succeeded = (
                    self._execute_flush(action, cancel_event)
                )
            elif action.kind is RepairKind.RENEW_DHCP:
                status, commands, rollback_attempted, rollback_succeeded = (
                    self._execute_renew(action, report, cancel_event)
                )
            elif action.kind is RepairKind.RECONNECT_INTERFACE:
                status, commands, rollback_attempted, rollback_succeeded = (
                    self._execute_reconnect(action, report, cancel_event)
                )
            elif action.kind is RepairKind.ENABLE_WIFI:
                status, commands, rollback_attempted, rollback_succeeded = (
                    self._execute_wifi(action, cancel_event)
                )
            elif action.kind is RepairKind.CONFIGURE_APP_CA:
                assert action.ca_file is not None
                app_ca_file = _validate_app_ca(
                    action.ca_file,
                    store_directory=self.ca_store_directory,
                )
                status = RepairStatus.SUCCEEDED
            else:  # pragma: no cover - StrEnum exhaustiveness guard
                status = RepairStatus.BLOCKED
        except Exception as exc:
            if mutation_locked:
                _REPAIR_MUTATION_LOCK.release()
            return self._result(
                action,
                RepairStatus.FAILED,
                str(exc)[:4096],
                started,
                commands=commands,
                rollback_attempted=rollback_attempted,
                rollback_succeeded=rollback_succeeded,
            )

        post_report = None
        if (
            status is RepairStatus.SUCCEEDED
            and action.kind is RepairKind.CONFIGURE_APP_CA
            and self.post_test is None
        ):
            if mutation_locked:
                _REPAIR_MUTATION_LOCK.release()
            return self._result(
                action,
                RepairStatus.POSTCHECK_FAILED,
                "The CA was validated but no post-test was available to confirm it.",
                started,
                app_ca_file=None,
            )
        if status is RepairStatus.SUCCEEDED and self.post_test is not None:
            try:
                post_report = self.post_test()
            except Exception as exc:
                if mutation_locked:
                    _REPAIR_MUTATION_LOCK.release()
                return self._result(
                    action,
                    RepairStatus.POSTCHECK_FAILED,
                    f"The action completed, but the post-test failed: {exc}",
                    started,
                    commands=commands,
                    rollback_attempted=rollback_attempted,
                    rollback_succeeded=rollback_succeeded,
                    app_ca_file=app_ca_file,
                )
            postcheck_bad = bool(post_report.cancelled or post_report.timed_out)
            if action.kind is RepairKind.CONFIGURE_APP_CA:
                postcheck_bad = postcheck_bad or post_report.state not in {
                    NetworkState.ONLINE,
                    NetworkState.ONLINE_MANAGED,
                }
            if postcheck_bad:
                if mutation_locked:
                    _REPAIR_MUTATION_LOCK.release()
                return self._result(
                    action,
                    RepairStatus.POSTCHECK_FAILED,
                    "The action completed, but the post-test did not confirm connectivity.",
                    started,
                    commands=commands,
                    rollback_attempted=rollback_attempted,
                    rollback_succeeded=rollback_succeeded,
                    post_report=post_report,
                    app_ca_file=None,
                )

        messages = {
            RepairStatus.SUCCEEDED: "The action completed and no broader settings were changed.",
            RepairStatus.CANCELLED: "The action was cancelled.",
            RepairStatus.ELEVATION_REQUIRED: "A one-shot elevated helper is required.",
            RepairStatus.BLOCKED: "The action is unavailable on this system.",
            RepairStatus.FAILED: "The action failed; no additional repair was attempted.",
        }
        if mutation_locked:
            _REPAIR_MUTATION_LOCK.release()
        return self._result(
            action,
            status,
            messages.get(status, "The action did not complete."),
            started,
            commands=commands,
            rollback_attempted=rollback_attempted,
            rollback_succeeded=rollback_succeeded,
            post_report=post_report,
            app_ca_file=app_ca_file,
        )


__all__ = [
    "RepairAction",
    "RepairExecutor",
    "RepairGuidance",
    "RepairImpact",
    "RepairKind",
    "RepairResult",
    "RepairStatus",
    "SubprocessRepairRunner",
    "list_repair_actions",
    "list_repair_guidance",
]
