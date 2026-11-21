"""Tests for varedura.termux_env and Android/Termux compatibility paths."""

from __future__ import annotations

import builtins
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

from varedura import termux_env as te


def test_termux_env_import_is_100pct_stdlib_and_zero_io():
    script = (
        "import json, socket, subprocess, sys; "
        "bad = lambda *a, **k: (_ for _ in ()).throw(AssertionError('IO on import')); "
        "socket.getaddrinfo = bad; subprocess.run = bad; subprocess.Popen = bad; "
        "import varedura.termux_env; "
        "heavy = ['psutil', 'requests', 'textual', 'rich', 'PIL', 'selenium', 'matplotlib', 'reportlab']; "
        "print(json.dumps({m: m in sys.modules for m in heavy}))"
    )
    res = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    loaded = json.loads(res.stdout.strip())
    assert not any(loaded.values())


def test_env_detection_flags(monkeypatch, tmp_path):
    for key in ("TERMUX_VERSION", "PREFIX", "VAREDURA_TERMUX_MODE", "ANDROID_ROOT", "VAREDURA_SHOW_DOCKER"):
        monkeypatch.delenv(key, raising=False)

    assert not te.is_termux()
    assert not te.is_android()
    assert te.get_termux_prefix() == Path("/data/data/com.termux/files/usr")
    assert te.should_show_docker_tab() is True

    monkeypatch.setenv("TERMUX_VERSION", "0.118.3")
    assert te.is_termux()
    assert te.is_android()

    monkeypatch.delenv("TERMUX_VERSION")
    monkeypatch.setenv("PREFIX", "/data/data/com.termux/files/usr")
    assert te.is_termux()

    monkeypatch.delenv("PREFIX")
    monkeypatch.setenv("VAREDURA_TERMUX_MODE", "1")
    assert te.is_termux()

    monkeypatch.delenv("VAREDURA_TERMUX_MODE")
    monkeypatch.setenv("ANDROID_ROOT", "/system")
    assert not te.is_termux()
    assert te.is_android()

    monkeypatch.setattr(te.shutil, "which", lambda name: None)
    assert te.should_show_docker_tab() is False

    monkeypatch.setenv("VAREDURA_SHOW_DOCKER", "1")
    assert te.should_show_docker_tab() is True

    monkeypatch.delenv("VAREDURA_SHOW_DOCKER")
    monkeypatch.setattr(te.shutil, "which", lambda name: "/usr/bin/docker" if name == "docker" else None)
    assert te.has_docker() is True
    assert te.should_show_docker_tab() is True


def test_root_and_claro_suite_detection(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(te.shutil, "which", lambda name: "/sbin/tsu" if name == "tsu" else None)
    assert te.has_root() is True
    assert te.has_claro_suite() is False

    (tmp_path / ".claro_suite").mkdir()
    assert te.has_claro_suite() is True


def test_discover_termux_tools_builtins_claro_shortcuts_and_custom(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    bins = {
        "micro": "/usr/bin/micro",
        "btop": "/usr/bin/btop",
        "sudo": "/usr/bin/sudo",
        "tsu": "/usr/bin/tsu",
        "portscan": "/usr/bin/portscan",
        "vt-scan": "/usr/bin/vt-scan",
        "painel-web": "/usr/bin/painel-web",
        "vernet": "/usr/bin/vernet",
    }
    monkeypatch.setattr(te.shutil, "which", lambda name: bins.get(name))

    claro_dir = tmp_path / ".claro_suite"
    claro_dir.mkdir()
    (claro_dir / "claro_monitor.py").write_text("print('mon')", encoding="utf-8")
    (claro_dir / "claro_audit.py").write_text("print('aud')", encoding="utf-8")
    (claro_dir / "m35_tui.py").write_text("print('m35')", encoding="utf-8")

    shortcuts_dir = tmp_path / ".shortcuts"
    tasks_dir = shortcuts_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    for fname, body in [
        ("1_Monitor_Claro", "#!/bin/bash\nclaro-monitor\n"),
        ("2_Auditar_ZeroRating", "#!/bin/bash\nclaro-audit\n"),
        ("3_Scanner_Rede", "#!/bin/bash\nnetscan\n"),
        ("4_Centro_Controle", "#!/bin/bash\npython3 ~/.claro_suite/m35_tui.py\n"),
    ]:
        p = shortcuts_dir / fname
        p.write_text(body, encoding="utf-8")
        if os.name != "nt":
            os.chmod(p, 0o755)

    unique_task = tasks_dir / "Alternar_Modo_Banco"
    unique_task.write_text("#!/bin/bash\necho toggled\n", encoding="utf-8")
    if os.name != "nt":
        os.chmod(unique_task, 0o755)

    custom_json = tmp_path / ".varedura_termux_tools.json"
    custom_json.write_text(
        json.dumps(
            [
                {
                    "id": "my-ping",
                    "label": "Custom Ping",
                    "command": "ping -c 3 1.1.1.1",
                    "category": "custom",
                    "mode": "suspend_pause",
                    "description": "Quick check",
                },
                {"id": "broken"},  # missing label/command -> ignored
            ]
        ),
        encoding="utf-8",
    )

    tools = te.discover_termux_tools()
    by_id = {tool.id: tool for tool in tools}

    assert by_id["micro"].mode == "suspend"
    assert by_id["btop"].command == (
        "/usr/bin/sudo",
        "env",
        "LANG=en_US.UTF-8",
        "TERM=xterm-256color",
        "/usr/bin/btop",
    )
    assert by_id["portscan"].needs_arg is True
    assert by_id["vt-scan"].needs_arg is True
    assert by_id["painel-web"].mode == "background"
    assert by_id["claro-monitor"].source == "claro_suite"
    assert by_id["claro-audit"].mode == "suspend_pause"
    assert by_id["m35-center"].command == (sys.executable, str(claro_dir / "m35_tui.py"))

    # Redundant shortcuts filtered out; unique task shortcut preserved
    assert not any("1_Monitor_Claro" in tid for tid in by_id)
    assert not any("4_Centro_Controle" in tid for tid in by_id)
    assert "shortcut:task:Alternar_Modo_Banco" in by_id
    assert by_id["shortcut:task:Alternar_Modo_Banco"].category == "shortcuts"

    assert by_id["my-ping"].command == ("ping", "-c", "3", "1.1.1.1")
    assert by_id["my-ping"].source == "custom"


def test_discover_termux_tools_ignores_invalid_custom_json(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(te.shutil, "which", lambda _name: None)
    (tmp_path / ".varedura_termux_tools.json").write_text("{not valid json", encoding="utf-8")

    assert te.discover_termux_tools() == []


def test_collect_android_telemetry_parses_sysfs_proc_and_ip(monkeypatch):
    fake_files = {
        "/sys/class/power_supply/battery/capacity": "84\n",
        "/sys/class/power_supply/battery/status": "Discharging\n",
        "/sys/class/power_supply/battery/temp": "335\n",
        "/proc/net/dev": (
            "Inter-|   Receive |  Transmit\n"
            " face |bytes packets errs drop fifo frame compressed multicast|bytes packets\n"
            "  wlan0: 1000 10 0 0 0 0 0 0 2500 20 0 0 0 0 0 0\n"
            "  rmnet_data0: 400 4 0 0 0 0 0 0 800 8 0 0 0 0 0 0\n"
            "  rmnet_data1: 100 1 0 0 0 0 0 0 200 2 0 0 0 0 0 0\n"
        ),
        "/proc/meminfo": "MemTotal:        8000000 kB\nMemAvailable:    3000000 kB\n",
        "/proc/uptime": "7325.4 1000.0\n",
    }

    def fake_read(path: Path):
        return fake_files.get(path.as_posix())

    monkeypatch.setattr(te, "_read_text_optional", fake_read)
    monkeypatch.setattr(te.shutil, "which", lambda name: "/usr/bin/ip" if name == "ip" else None)

    def fake_run(cmd, **_kwargs):
        return types.SimpleNamespace(
            returncode=0,
            stdout=(
                "12: wlan0    inet 192.168.1.45/24 brd 192.168.1.255 scope global wlan0\n"
                "8: rmnet_data0    inet 10.42.0.9/32 scope global rmnet_data0\n"
            ),
            stderr="",
        )

    monkeypatch.setattr(te.subprocess, "run", fake_run)

    tel = te.collect_android_telemetry()
    assert tel.battery_pct == 84
    assert tel.battery_status == "Discharging"
    assert tel.battery_temp_c == 33.5
    assert tel.rx_bytes == 1000
    assert tel.tx_bytes == 2500
    assert tel.mobile_rx_bytes == 500
    assert tel.mobile_tx_bytes == 1000
    assert tel.wifi_ip == "192.168.1.45"
    assert tel.mobile_ip == "10.42.0.9"
    assert tel.mem_total_mb == pytest.approx(8000000 / 1024.0, abs=0.2)
    assert tel.mem_used_mb == pytest.approx(5000000 / 1024.0, abs=0.2)
    assert tel.uptime_str == "2h 02m"


def test_collect_android_telemetry_battery_api_fallback_and_never_raises(monkeypatch):
    monkeypatch.setattr(te, "_read_text_optional", lambda _p: None)
    monkeypatch.setattr(
        te.shutil,
        "which",
        lambda name: "/usr/bin/termux-battery-status" if name == "termux-battery-status" else None,
    )
    monkeypatch.setattr(
        te.subprocess,
        "run",
        lambda cmd, **_kw: types.SimpleNamespace(
            returncode=0,
            stdout='{"percentage": 67, "status": "CHARGING", "temperature": 31.4}',
            stderr="",
        ),
    )

    tel = te.collect_android_telemetry()
    assert tel.battery_pct == 67
    assert tel.battery_status == "CHARGING"
    assert tel.battery_temp_c == 31.4


def test_termux_services_list_and_toggle(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    prefix = tmp_path / "usr"
    (prefix / "var" / "run").mkdir(parents=True)
    (prefix / "var" / "run" / "termux-wake-lock").write_text("", encoding="utf-8")
    monkeypatch.setenv("PREFIX", str(prefix))

    monkeypatch.setattr(
        te.shutil,
        "which",
        lambda name: f"/bin/{name}" if name in {"sshd", "crond", "termux-wake-lock", "termux-wake-unlock", "pkill"} else None,
    )
    monkeypatch.setattr(te, "_pgrep_active", lambda pat, full=False: pat == "sshd")
    monkeypatch.setattr(te, "_pid_file_alive", lambda _p: False)

    services = {s.id: s for s in te.list_termux_services()}
    assert services["sshd"].active is True
    assert services["crond"].active is False
    assert services["wakelock"].active is True
    assert services["claro_daemon"].available is False

    (tmp_path / ".claro_suite").mkdir()
    (tmp_path / ".claro_suite" / "claro_monitor.py").write_text("import time", encoding="utf-8")
    services2 = {s.id: s for s in te.list_termux_services()}
    assert services2["claro_daemon"].available is True

    calls = []
    monkeypatch.setattr(
        te.subprocess,
        "run",
        lambda cmd, **_kw: (calls.append(cmd), types.SimpleNamespace(returncode=0, stdout="ok", stderr=""))[1],
    )
    ok, _ = te.toggle_termux_service("wakelock", False)
    assert ok is True
    assert calls[-1] == ["/bin/termux-wake-unlock"]

    ok_bad, _ = te.toggle_termux_service("nonexistent", True)
    assert ok_bad is False


def test_termux_api_helpers(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs.get("input")))
        if "termux-share" in cmd[0]:
            return types.SimpleNamespace(returncode=1, stdout="", stderr="fail")
        return types.SimpleNamespace(returncode=0, stdout="switched", stderr="")

    monkeypatch.setattr(te.subprocess, "run", fake_run)
    monkeypatch.setattr(te.shutil, "which", lambda name: f"/bin/{name}")

    assert te.send_termux_notification("Alert", "Down", vibrate=True) is True
    assert "--vibrate" in calls[-1][0]

    assert te.share_file(tmp_path / "r.csv", title="Report") is True
    assert calls[-1][0] == ["/bin/termux-open", str(tmp_path / "r.csv")]

    assert te.copy_to_clipboard("ssh -p 8022 u0@1.2.3.4") is True
    assert calls[-1][1] == "ssh -p 8022 u0@1.2.3.4"

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    ok, _ = te.toggle_keyboard_page()
    assert ok is False

    (tmp_path / ".claro_suite").mkdir()
    (tmp_path / ".claro_suite" / "termux_page_switcher.py").write_text("print('ok')", encoding="utf-8")
    ok, msg = te.toggle_keyboard_page()
    assert ok is True
    assert msg == "switched"


def test_android_dns_and_route_fallback_in_network_diagnostics(monkeypatch, tmp_path):
    from monitor import network_diagnostics as nd

    prefix = tmp_path / "prefix"
    (prefix / "etc").mkdir(parents=True)
    (prefix / "etc" / "resolv.conf").write_text("nameserver 1.1.1.1\n", encoding="utf-8")
    monkeypatch.setenv("PREFIX", str(prefix))

    orig_read_text = Path.read_text

    def fake_read_text(self, *args, **kwargs):
        if self.as_posix() == "/etc/resolv.conf":
            raise FileNotFoundError
        return orig_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    assert nd._read_dns_resolv_conf() == ("1.1.1.1",)

    # Empty resolv.conf -> getprop fallback on Android
    (prefix / "etc" / "resolv.conf").write_text("# empty\n", encoding="utf-8")
    monkeypatch.setenv("VAREDURA_TERMUX_MODE", "1")
    monkeypatch.setattr(
        nd.subprocess,
        "run",
        lambda cmd, **_kw: types.SimpleNamespace(
            returncode=0,
            stdout="8.8.8.8\n" if cmd[1] == "net.dns1" else "8.8.4.4\n",
        ),
    )
    assert nd._read_dns_resolv_conf() == ("8.8.8.8", "8.8.4.4")

    # ip route get 1.1.1.1 fallback in SnapshotCollector
    iface = nd.NetworkInterface(name="wlan0", is_up=True, ipv4=("192.168.1.50",))
    monkeypatch.setattr(nd, "_interface_addresses", lambda: (iface,))
    monkeypatch.setattr(nd, "_read_dns_resolv_conf", lambda: ("8.8.8.8",))
    monkeypatch.setattr(
        nd, "_collect_proxy_configuration", lambda *a, **k: nd.ProxyConfiguration()
    )
    monkeypatch.setattr(nd, "_process_security_flags", lambda cancel_event=None: (False, False))

    class AndroidRouteRunner:
        def __init__(self):
            self.calls = []

        def run(self, args, **_kwargs):
            cmd = tuple(args)
            self.calls.append(cmd)
            if cmd == ("ip", "route", "get", "1.1.1.1"):
                return nd.CommandResult(
                    cmd,
                    0,
                    stdout="1.1.1.1 via 192.168.1.1 dev wlan0 src 192.168.1.50 uid 10200\n",
                )
            return nd.CommandResult(cmd, 0, stdout="")

    runner = AndroidRouteRunner()
    snap = nd.SnapshotCollector(
        command_runner=runner,
        platform_name="linux",
        environ={},
        command_exists=lambda _name: None,
    ).collect(timeout=0.5)
    assert snap.route_present is True
    assert snap.default_gateway == "192.168.1.1"
    assert snap.active_interface == "wlan0"
    assert ("ip", "route", "get", "1.1.1.1") in runner.calls


def test_export_bundle_and_stalker_handle_missing_pdf_deps(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    from monitor.network_history import NetworkSessionHistory
    from monitor.ping_targets import PingProbeResult, PingStatus, PingTarget, TargetCategory
    from monitor import stalker

    history = NetworkSessionHistory()
    target = PingTarget("cf", "Cloudflare", "1.1.1.1", TargetCategory.INFRASTRUCTURE)
    history.add_result(
        PingProbeResult(
            target_id="cf",
            generation=1,
            host="1.1.1.1",
            status=PingStatus.SUCCESS,
            started_monotonic=1.0,
            completed_monotonic=1.02,
            latency_ms=20.0,
            observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        ),
        target,
    )

    real_import = builtins.__import__

    def no_reportlab(name, *args, **kwargs):
        if name.startswith("reportlab"):
            raise ImportError("no reportlab")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_reportlab)
    csv_path, pdf_path = history.export_bundle(directory=tmp_path)
    assert csv_path.exists()
    assert pdf_path is None

    # Also check stalker CSVs still written when matplotlib is missing
    monkeypatch.chdir(tmp_path)
    stalker.full_ping_history.clear()
    stalker.full_ping_history.append((datetime.now(), 10.0, 20.0))

    def no_matplotlib(name, *args, **kwargs):
        if name.startswith("matplotlib"):
            raise ImportError("no matplotlib")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", no_matplotlib)
    stalker._generate_combined_pdf_worker(full_history=False)
    status = stalker.get_export_status() or ""
    assert "matplotlib" in status.lower()
    assert list((tmp_path / "exports").glob("ping_history_*.csv"))
