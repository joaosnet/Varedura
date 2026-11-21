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
