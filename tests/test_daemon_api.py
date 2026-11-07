"""Unit tests for the Varedura Remote Node Manager Daemon API."""

import json
import urllib.request
import urllib.error
import pytest

from varedura.daemon_api import VareduraDaemonServer, _DAEMON_STATE


@pytest.fixture(scope="module")
def daemon_server():
    server = VareduraDaemonServer(host="127.0.0.1", port=0)
    server.start()
    port = server._server.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    server.stop()


def test_daemon_health(daemon_server):
    with urllib.request.urlopen(f"{daemon_server}/api/health", timeout=2) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["status"] == "ok"
        assert data["service"] == "Varedura Remote Daemon"


def test_daemon_system_stats(daemon_server):
    with urllib.request.urlopen(f"{daemon_server}/api/system/stats", timeout=2) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "cpu_percent" in data
        assert "memory" in data
        assert "disk" in data
        assert "network" in data


def test_daemon_docker_status(daemon_server):
    with urllib.request.urlopen(f"{daemon_server}/api/docker/status", timeout=2) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "available" in data
        assert "cleanup_progress" in data


def test_daemon_cameras_list_and_register(daemon_server):
    # 1. Register camera
    payload = json.dumps({
        "url": "rtsp://admin:pass123@192.168.1.100:554/stream",
        "name": "Driveway Camera",
        "id": "cam_driveway",
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{daemon_server}/api/cameras/register",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=4) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["id"] == "cam_driveway"

    # 2. List cameras
    with urllib.request.urlopen(f"{daemon_server}/api/cameras/list", timeout=2) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert "cameras" in data
        assert any(c["id"] == "cam_driveway" for c in data["cameras"])

    # 3. Snapshot endpoint
    with urllib.request.urlopen(f"{daemon_server}/api/cameras/cam_driveway/snapshot", timeout=2) as resp:
        assert resp.status == 200
        assert resp.headers.get("Content-Type") == "image/jpeg"
        content = resp.read()
        assert content.startswith(b"\xff\xd8")


def test_daemon_diagnostics_ping(daemon_server, monkeypatch):
    monkeypatch.setattr("varedura.daemon_api.run_ping", lambda h: 14.5)
    payload = json.dumps({"host": "1.1.1.1"}).encode("utf-8")
    req = urllib.request.Request(
        f"{daemon_server}/api/diagnostics/ping",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=2) as resp:
        assert resp.status == 200
        data = json.loads(resp.read().decode("utf-8"))
        assert data["host"] == "1.1.1.1"
        assert data["latency_ms"] == 14.5
