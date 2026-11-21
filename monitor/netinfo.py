"""Lightweight network information helpers (gateway autodetection)."""

from __future__ import annotations

import json
import platform
import re
import subprocess
from typing import Optional

_IPV4 = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def _run(cmd: list[str]) -> str:
    """Run a command quietly and return stdout (empty string on failure)."""
    try:
        startupinfo = None
        if platform.system().lower() == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            startupinfo=startupinfo,
            timeout=5,
        )
        return result.stdout or ""
    except Exception:
        return ""


def _detect_windows() -> Optional[str]:
    """Parse `route print` for the default route (locale-independent)."""
    out = _run(["route", "print", "-4", "0.0.0.0"])
    best_ip: Optional[str] = None
    best_metric = float("inf")
    for line in out.splitlines():
        parts = line.split()
        # Active default route row: 0.0.0.0  0.0.0.0  <gateway>  <iface>  <metric>
        if len(parts) >= 5 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
            gateway = parts[2]
            if not _IPV4.match(gateway):
                continue
            try:
                metric = int(parts[4])
            except ValueError:
                metric = 0
            if metric < best_metric:
                best_metric, best_ip = metric, gateway
    return best_ip


def _detect_unix() -> Optional[str]:
    """Parse `ip route`, Termux Wi-Fi info, rooted route table, or `netstat -rn`."""
    out = _run(["ip", "route", "show", "default"])
    match = re.search(r"default via (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})", out)
    if match and _IPV4.match(match.group(1)):
        return match.group(1)

    out = _run(["ip", "route", "get", "1.1.1.1"])
    match = re.search(r"\bvia\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", out)
    if match and _IPV4.match(match.group(1)):
        return match.group(1)

    out = _run(["termux-wifi-connectioninfo"])
    if out.strip():
        try:
            payload = json.loads(out)
            if isinstance(payload, dict):
                gw = str(payload.get("gateway") or "").strip()
                if _IPV4.match(gw):
                    return gw
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    out = _run(["su", "-c", "ip route show table all"])
    match = re.search(
        r"\bdefault\s+via\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b", out
    )
    if match and _IPV4.match(match.group(1)):
        return match.group(1)

    out = _run(["netstat", "-rn"])
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] in ("default", "0.0.0.0") and len(parts) >= 2:
            if _IPV4.match(parts[1]):
                return parts[1]
    return None


def detect_default_gateway() -> Optional[str]:
    """Best-effort detection of the default gateway IP, or None if unknown."""
    try:
        if platform.system().lower() == "windows":
            return _detect_windows()
        return _detect_unix()
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Rede ativa (tipo, SSID e gateway) — usada para escolher o perfil de plano.
# ---------------------------------------------------------------------------
_MOBILE_IFACE = re.compile(r"^(rmnet|ccmni|wwan|pdp|usb_rmnet|v4-rmnet)", re.IGNORECASE)
_WIFI_IFACE = re.compile(r"^(wlan|swlan|wl|wifi|ath|ra)", re.IGNORECASE)
_UNKNOWN_SSIDS = {"", "<unknown ssid>", "unknown ssid", "0x"}


def _clean_ssid(value: object) -> str:
    ssid = str(value or "").strip().strip('"')
    return "" if ssid.casefold() in _UNKNOWN_SSIDS else ssid[:64]


def parse_route_get(output: str) -> tuple[str, str]:
    """Extrai ``(interface, gateway)`` da saída de ``ip route get``."""
    dev = re.search(r"\bdev\s+(\S+)", output)
    via = re.search(r"\bvia\s+(\d{1,3}(?:\.\d{1,3}){3})\b", output)
    return (dev.group(1) if dev else "", via.group(1) if via else "")


def parse_netsh_wlan(output: str) -> str:
    """SSID conectado na saída de ``netsh wlan show interfaces`` (qualquer idioma)."""
    connected = False
    ssid = ""
    for line in output.splitlines():
        key, sep, value = line.partition(":")
        if not sep:
            continue
        key, value = key.strip().casefold(), value.strip()
        if key in {"state", "estado"}:
            connected = value.casefold() in {"connected", "conectado"}
        elif key == "ssid" and not ssid:
            ssid = value
    return _clean_ssid(ssid) if connected else ""


def _kind_from_interface(interface: str):
    from monitor.plan_profiles import NetworkKind

    if not interface:
        return NetworkKind.UNKNOWN
    if _MOBILE_IFACE.match(interface):
        return NetworkKind.MOBILE
    if _WIFI_IFACE.match(interface):
        return NetworkKind.WIFI
    if re.match(r"^(eth|en|em)", interface, re.IGNORECASE):
        return NetworkKind.ETHERNET
    return NetworkKind.UNKNOWN


def detect_active_network():
    """Best-effort: por qual rede o tráfego sai agora (nunca levanta exceção)."""
    from monitor.plan_profiles import ActiveNetwork, NetworkKind

    try:
        if platform.system().lower() == "windows":
            gateway = detect_default_gateway() or ""
            ssid = parse_netsh_wlan(_run(["netsh", "wlan", "show", "interfaces"]))
            if ssid:
                kind = NetworkKind.WIFI
            else:
                kind = NetworkKind.ETHERNET if gateway else NetworkKind.UNKNOWN
            return ActiveNetwork(kind, ssid, gateway, "")

        interface, gateway = parse_route_get(_run(["ip", "route", "get", "1.1.1.1"]))
        kind = _kind_from_interface(interface)
        ssid = ""
        if kind is NetworkKind.WIFI:
            out = _run(["termux-wifi-connectioninfo"])
            if out.strip():
                try:
                    payload = json.loads(out)
                except (json.JSONDecodeError, TypeError, ValueError):
                    payload = {}
                if isinstance(payload, dict):
                    ssid = _clean_ssid(payload.get("ssid"))
                    if not gateway:
                        candidate = str(payload.get("gateway") or "").strip()
                        gateway = candidate if _IPV4.match(candidate) else ""
            if not ssid:
                ssid = _clean_ssid(_run(["iwgetid", "-r"]))
        if kind is NetworkKind.MOBILE:
            gateway = ""  # o "gateway" da operadora muda a cada sessão de dados
        elif not gateway:
            gateway = detect_default_gateway() or ""
        return ActiveNetwork(kind, ssid, gateway, interface)
    except Exception:
        return ActiveNetwork()
