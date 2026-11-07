"""Unit tests for the sanitized Varedura camera bridge."""

from __future__ import annotations

import json
import logging
import subprocess
import time
import uuid
from datetime import UTC, datetime, timedelta
from os import utime
from pathlib import Path
from types import SimpleNamespace

import pytest

from rtsp.log import RedactingFilter, RedactingFormatter, redact_sensitive
from varedura.camera_bridge import (
    BridgeAlreadyRunning,
    CameraBridge,
    CameraSource,
    CaptureResult,
    FFmpegRunner,
    load_private_inventory,
)


def new_id() -> str:
    return str(uuid.uuid4())


def command(
    action: str,
    *,
    command_id: str | None = None,
    camera_id: str | None = None,
    session_id: str | None = None,
    **extra,
) -> dict:
    data = {
        "schemaVersion": 1,
        "commandId": command_id or new_id(),
        "action": action,
        "requestedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }
    if camera_id is not None:
        data["cameraId"] = camera_id
    if session_id is not None:
        data["sessionId"] = session_id
    data.update(extra)
    return data


def put_command(bridge: CameraBridge, data: dict) -> Path:
    bridge._ensure_directories()
    path = bridge.inbox_dir / f"{data['commandId']}.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class FakeProcess:
    def __init__(self):
        self.pid = 4321
        self.returncode = None
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True
        self.returncode = 0

    def kill(self):
        self.killed = True
        self.returncode = -9

    def wait(self, timeout=None):
        if self.returncode is None:
            raise subprocess.TimeoutExpired("ffmpeg", timeout)
        return self.returncode


class FakeRunner:
    available = True

    def __init__(self):
        self.process = FakeProcess()
        self.start_calls = 0
        self.capture_calls = 0

    def capture_snapshot(self, camera, destination):
        self.capture_calls += 1
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"jpeg")
        return CaptureResult(
            True,
            "online",
            "video_ok",
            revision="abc123",
            updated_at="2026-07-28T10:01:00Z",
        )

    def start_hls(self, camera, session_dir):
        self.start_calls += 1
        return self.process


def make_bridge(
    tmp_path: Path,
    camera: CameraSource,
    runner: FakeRunner | None = None,
) -> tuple[CameraBridge, FakeRunner]:
    fake_runner = runner or FakeRunner()
    bridge = CameraBridge(
        tmp_path / "runtime" / "cameras",
        state_path=tmp_path / "private-state.json",
        snapshot_interval=9999,
        session_ttl=45,
        ffmpeg_runner=fake_runner,
        inventory_loader=lambda: [camera],
    )
    bridge._ensure_directories()
    bridge.refresh_inventory()
    return bridge, fake_runner


def shutdown_executor(bridge: CameraBridge) -> None:
    bridge._executor.shutdown(wait=True, cancel_futures=True)


def test_redaction_removes_rtsp_userinfo_password_and_basic_auth():
    raw = (
        "open rtsp://admin:s3cret@192.168.1.50/live?"
        "password=other and (rtsps://cam.example.test:7441/private/path), "
        "IPv6 rtsp://user:pass@[fd00::1]:554/live, "
        "Authorization: Basic YWRtaW46czNjcmV0"
    )
    redacted = redact_sensitive(raw)
    for secret in (
        "admin",
        "s3cret",
        "192.168.1.50",
        "/live",
        "other",
        "cam.example.test",
        "/private/path",
        "fd00::1",
        "YWRtaW46czNjcmV0",
    ):
        assert secret not in redacted
    assert "rtsp://<redacted>" in redacted
    assert "rtsps://<redacted>" in redacted


def test_redacting_formatter_covers_exception_text():
    record = logging.LogRecord(
        "rtsp.test",
        logging.ERROR,
        __file__,
        1,
        "failed %s",
        ("rtsp://admin:secret@camera/live",),
        None,
    )
    RedactingFilter().filter(record)
    rendered = RedactingFormatter("%(message)s").format(record)
    assert "admin" not in rendered
    assert "secret" not in rendered
    assert "camera" not in rendered
    assert "/live" not in rendered
    assert "<redacted>" in rendered


def test_inventory_ids_are_stable_and_private_state_has_no_endpoint(tmp_path):
    known = {
        "192.168.1.50": SimpleNamespace(
            usuario="admin",
            senha="super-secret",
            caminho="/stream1",
            url="rtsp://admin:super-secret@192.168.1.50:554/stream1",
            codec="h264",
            resolucao="1920x1080",
        )
    }
    regions = [
        SimpleNamespace(
            rotulo="Portão",
            tipo="camera",
            endereco="192.168.1.50",
            porta=554,
            caminho="/stream1",
        )
    ]
    state = tmp_path / "camera_bridge_state.json"
    first = load_private_inventory(state, conhecidos=known, regioes=regions)
    second = load_private_inventory(state, conhecidos=known, regioes=regions)

    assert len(first) == 1
    assert first[0].id == second[0].id
    assert first[0].name == "Portão"
    assert first[0].codec == "h264"
    assert (first[0].width, first[0].height) == (1920, 1080)
    serialized = state.read_text(encoding="utf-8")
    for secret in ("192.168.1.50", "admin", "super-secret", "rtsp://"):
        assert secret not in serialized


def test_inventory_never_uses_ip_as_default_name(tmp_path):
    regions = [
        SimpleNamespace(
            rotulo="192.168.1.20",
            tipo="camera",
            endereco="192.168.1.20",
            porta=554,
            caminho="/live",
        )
    ]
    camera = load_private_inventory(
        tmp_path / "state.json",
        conhecidos={},
        regioes=regions,
    )[0]
    assert camera.name == "Câmera 01"
    assert "192.168" not in camera.name


def test_inventory_id_survives_password_change_inside_vendor_path(tmp_path):
    state = tmp_path / "state.json"

    def known(password):
        return {
            "camera.local": SimpleNamespace(
                usuario="admin",
                senha=password,
                caminho=f"/user=admin&password={password}&channel=1",
                url=(f"rtsp://camera.local/user=admin&password={password}&channel=1"),
                codec="h264",
                resolucao="640x480",
            )
        }

    first = load_private_inventory(state, conhecidos=known("old"), regioes=[])[0]
    second = load_private_inventory(state, conhecidos=known("new"), regioes=[])[0]
    assert first.id == second.id


def test_catalog_is_sanitized_and_atomic(tmp_path):
    camera = CameraSource(
        id=new_id(),
        name="Garagem",
        url="rtsp://admin:secret@10.0.0.8/live",
        codec="h264",
        width=1280,
        height=720,
    )
    bridge, _runner = make_bridge(tmp_path, camera)
    try:
        bridge.write_catalog()
        catalog = json.loads(bridge.catalog_path.read_text(encoding="utf-8"))
        assert catalog["schemaVersion"] == 1
        assert catalog["capabilities"]["maxLiveSessions"] == 1
        assert catalog["feeds"][0]["id"] == camera.id
        assert catalog["feeds"][0]["snapshotFile"] == f"snapshots/{camera.id}.jpg"
        assert "snapshotRevision" not in catalog["feeds"][0]
        assert "location" not in catalog["feeds"][0]
        serialized = json.dumps(catalog)
        for secret in ("10.0.0.8", "admin", "secret", "rtsp://"):
            assert secret not in serialized
        assert not list(bridge.output_dir.glob(".catalog.json.*.tmp"))
    finally:
        shutdown_executor(bridge)


def test_location_command_persists_privately_and_survives_restart(tmp_path):
    camera_id = new_id()
    camera = CameraSource(
        id=camera_id,
        name="Entrada",
        url="rtsp://admin:secret@192.168.1.50/live",
    )
    bridge, _runner = make_bridge(tmp_path, camera)
    location = {
        "latitude": -1.4558,
        "longitude": -48.4902,
        "accuracyMeters": 12.5,
        "source": "manual",
        "updatedAt": "2026-07-28T12:00:00+00:00",
    }
    request = command("set_location", camera_id=camera_id, location=location)

    try:
        put_command(bridge, request)
        bridge.process_commands()

        ack = json.loads(
            (bridge.outbox_dir / f"{request['commandId']}.json").read_text(
                encoding="utf-8"
            )
        )
        assert ack["status"] == "completed"
        assert "location" not in ack

        private = json.loads(bridge.locations_path.read_text(encoding="utf-8"))
        assert private == {
            "schemaVersion": 1,
            "locations": {camera_id: location},
        }
        serialized_private = json.dumps(private)
        for secret in ("192.168.1.50", "admin", "secret", "rtsp://", "/live"):
            assert secret not in serialized_private
        assert not list(bridge.output_dir.glob("..camera-locations.private.json.*.tmp"))

        catalog = json.loads(bridge.catalog_path.read_text(encoding="utf-8"))
        assert catalog["feeds"][0]["location"] == location
    finally:
        shutdown_executor(bridge)

    restarted_camera = CameraSource(
        id=camera_id,
        name="Entrada",
        url="rtsp://different:password@camera.invalid/stream",
    )
    restarted, _runner = make_bridge(tmp_path, restarted_camera)
    try:
        restarted.write_catalog()
        catalog = json.loads(restarted.catalog_path.read_text(encoding="utf-8"))
        assert catalog["feeds"][0]["location"] == location
    finally:
        shutdown_executor(restarted)


def test_clear_location_is_idempotent_and_keeps_camera_in_catalog(tmp_path):
    camera = CameraSource(id=new_id(), name="Garagem", url="rtsp://camera/live")
    bridge, _runner = make_bridge(tmp_path, camera)
    set_request = command(
        "set_location",
        camera_id=camera.id,
        location={
            "latitude": 0,
            "longitude": 0,
            "source": "device",
        },
    )
    clear_request = command("clear_location", camera_id=camera.id)
    clear_again = command("clear_location", camera_id=camera.id)

    try:
        for request in (set_request, clear_request, clear_again):
            put_command(bridge, request)
            bridge.process_commands()
            ack = json.loads(
                (bridge.outbox_dir / f"{request['commandId']}.json").read_text(
                    encoding="utf-8"
                )
            )
            assert ack["status"] == "completed"

        private = json.loads(bridge.locations_path.read_text(encoding="utf-8"))
        assert private["locations"] == {}
        catalog = json.loads(bridge.catalog_path.read_text(encoding="utf-8"))
        assert len(catalog["feeds"]) == 1
        assert "location" not in catalog["feeds"][0]
    finally:
        shutdown_executor(bridge)


@pytest.mark.parametrize(
    "location",
    [
        {"latitude": True, "longitude": 0, "source": "manual"},
        {"latitude": "1", "longitude": 0, "source": "manual"},
        {"latitude": float("nan"), "longitude": 0, "source": "manual"},
        {"latitude": float("inf"), "longitude": 0, "source": "manual"},
        {"latitude": 90.1, "longitude": 0, "source": "manual"},
        {"latitude": 0, "longitude": False, "source": "manual"},
        {"latitude": 0, "longitude": "1", "source": "manual"},
        {"latitude": 0, "longitude": float("-inf"), "source": "manual"},
        {"latitude": 0, "longitude": -180.1, "source": "manual"},
        {
            "latitude": 0,
            "longitude": 0,
            "accuracyMeters": True,
            "source": "manual",
        },
        {
            "latitude": 0,
            "longitude": 0,
            "accuracyMeters": "10",
            "source": "manual",
        },
        {
            "latitude": 0,
            "longitude": 0,
            "accuracyMeters": float("nan"),
            "source": "manual",
        },
        {
            "latitude": 0,
            "longitude": 0,
            "accuracyMeters": 0,
            "source": "manual",
        },
        {
            "latitude": 0,
            "longitude": 0,
            "accuracyMeters": -1,
            "source": "manual",
        },
        {
            "latitude": 0,
            "longitude": 0,
            "accuracyMeters": None,
            "source": "manual",
        },
        {"latitude": 0, "longitude": 0, "source": "geoip"},
        {"latitude": 0, "longitude": 0, "source": True},
        {
            "latitude": 0,
            "longitude": 0,
            "source": "manual",
            "updatedAt": 123,
        },
        {
            "latitude": 0,
            "longitude": 0,
            "source": "manual",
            "updatedAt": "2026-07-28T12:00:00",
        },
        {"latitude": 0, "longitude": 0, "source": "manual", "label": "Casa"},
        {"latitude": 0, "longitude": 0, "source": "manual", "endpoint": "hidden"},
    ],
)
def test_set_location_rejects_invalid_or_free_text_payload(location):
    request = command("set_location", camera_id=new_id(), location=location)
    assert CameraBridge._validate_command(request) == "invalid_location"


def test_location_actions_reject_wrong_command_shapes():
    camera_id = new_id()
    assert (
        CameraBridge._validate_command(command("set_location", camera_id=camera_id))
        == "invalid_location"
    )
    assert (
        CameraBridge._validate_command(
            command(
                "clear_location",
                camera_id=camera_id,
                location={
                    "latitude": 0,
                    "longitude": 0,
                    "source": "manual",
                },
            )
        )
        == "invalid_command_shape"
    )
    assert (
        CameraBridge._validate_command(
            command(
                "refresh",
                camera_id=camera_id,
                location={
                    "latitude": 0,
                    "longitude": 0,
                    "source": "manual",
                },
            )
        )
        == "invalid_command_shape"
    )


def test_partial_video_metadata_is_omitted_from_catalog(tmp_path):
    camera = CameraSource(
        id=new_id(),
        name="Garagem",
        url="rtsp://camera/live",
        codec="h264",
        width=None,
        height=None,
    )
    bridge, _runner = make_bridge(tmp_path, camera)
    try:
        bridge.write_catalog()
        feed = json.loads(bridge.catalog_path.read_text())["feeds"][0]
        assert "video" not in feed
        assert feed["snapshotFile"] == f"snapshots/{camera.id}.jpg"
    finally:
        shutdown_executor(bridge)


def test_snapshot_is_published_atomically_with_subprocess_mock(
    monkeypatch,
    tmp_path,
):
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        Path(args[-1]).write_bytes(b"valid-jpeg")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr("varedura.camera_bridge.subprocess.run", fake_run)
    runner = FFmpegRunner("ffmpeg", timeout=1)
    camera = CameraSource(
        id=new_id(),
        name="Entrada",
        url="rtsp://user:password@camera.local/live",
    )
    destination = tmp_path / "snapshots" / f"{camera.id}.jpg"
    result = runner.capture_snapshot(camera, destination)

    assert result.success is True
    assert destination.read_bytes() == b"valid-jpeg"
    assert calls[0][0][-1] != str(destination)
    assert calls[0][1]["timeout"] == 6
    assert not list(destination.parent.glob("*.tmp.jpg"))


@pytest.mark.parametrize(
    ("stderr", "status", "reason"),
    [
        (
            "server returned 401 Unauthorized",
            "auth_required",
            "authentication_required",
        ),
        ("Connection refused", "offline", "connection_failed"),
        ("Invalid video stream", "reachable_no_video", "no_video"),
        ("unexpected failure", "error", "snapshot_failed"),
    ],
)
def test_snapshot_failure_is_reduced_to_safe_enum(stderr, status, reason):
    result = FFmpegRunner._capture_failure(stderr)
    assert result.status == status
    assert result.reason == reason


def test_capture_logs_only_sanitized_state_transitions(monkeypatch, tmp_path):
    camera = CameraSource(
        id=new_id(),
        name="Entrada",
        url="rtsp://admin:secret@192.168.1.50/private-stream",
    )
    bridge, _runner = make_bridge(tmp_path, camera)
    messages = []

    def record(message, *args):
        messages.append(message % args)

    monkeypatch.setattr("varedura.camera_bridge._log.info", record)
    try:
        offline = CaptureResult(False, "offline", "connection_timeout")
        bridge._apply_capture(camera, offline)
        bridge._apply_capture(camera, offline)
        bridge._apply_capture(
            camera,
            CaptureResult(
                True,
                "online",
                "video_ok",
                revision="revision-1",
                updated_at="2026-08-04T12:00:00Z",
            ),
        )

        assert len(messages) == 2
        assert "status=offline reason=connection_timeout" in messages[0]
        assert "status=online reason=video_ok" in messages[1]
        serialized = "\n".join(messages)
        for secret in (
            "192.168.1.50",
            "admin",
            "secret",
            "private-stream",
            "rtsp://",
        ):
            assert secret not in serialized
    finally:
        shutdown_executor(bridge)


def test_hls_h264_uses_remux_without_audio(monkeypatch, tmp_path):
    captured = {}
    process = FakeProcess()

    def fake_popen(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return process

    monkeypatch.setattr("varedura.camera_bridge.subprocess.Popen", fake_popen)
    runner = FFmpegRunner("ffmpeg")
    camera = CameraSource(
        id=new_id(),
        name="Sala",
        url="rtsp://admin:secret@camera/live",
        codec="h264",
    )
    returned = runner.start_hls(camera, tmp_path)

    assert returned is process
    args = captured["args"]
    assert ["-c:v", "copy"] == args[args.index("-c:v") : args.index("-c:v") + 2]
    assert "-an" in args
    assert "-hls_time" in args
    assert "%06d.ts" in args
    assert "index.m3u8" == args[-1]
    assert captured["kwargs"]["cwd"] == tmp_path
    assert captured["kwargs"]["stderr"] is subprocess.DEVNULL


def test_command_session_lifecycle_and_single_session_limit(tmp_path):
    camera = CameraSource(
        id=new_id(),
        name="Portão",
        url="rtsp://admin:secret@camera/live",
    )
    bridge, runner = make_bridge(tmp_path, camera)
    session_id = new_id()
    try:
        start = command("start", camera_id=camera.id, session_id=session_id)
        put_command(bridge, start)
        bridge.process_commands()
        start_ack = json.loads(
            (bridge.outbox_dir / f"{start['commandId']}.json").read_text()
        )
        assert start_ack["status"] == "accepted"
        assert runner.start_calls == 1
        state_path = bridge.sessions_dir / session_id / "session.json"
        assert json.loads(state_path.read_text())["status"] == "starting"

        playlist = bridge.sessions_dir / session_id / "index.m3u8"
        playlist.write_text("#EXTM3U\n", encoding="utf-8")
        segment = bridge.sessions_dir / session_id / "000001.ts"
        segment.write_bytes(b"segment")
        bridge._update_session()
        assert json.loads(state_path.read_text())["status"] == "ready"

        second = command(
            "start",
            camera_id=camera.id,
            session_id=new_id(),
        )
        put_command(bridge, second)
        bridge.process_commands()
        second_ack = json.loads(
            (bridge.outbox_dir / f"{second['commandId']}.json").read_text()
        )
        assert second_ack["status"] == "rejected"
        assert second_ack["errorCode"] == "session_limit_reached"
        second_state = json.loads(
            (bridge.sessions_dir / second["sessionId"] / "session.json").read_text()
        )
        assert second_state["status"] == "error"
        assert second_state["errorCode"] == "session_replaced"
        assert runner.start_calls == 1

        heartbeat = command("heartbeat", session_id=session_id)
        put_command(bridge, heartbeat)
        bridge.process_commands()
        heartbeat_ack = json.loads(
            (bridge.outbox_dir / f"{heartbeat['commandId']}.json").read_text()
        )
        assert heartbeat_ack["status"] == "completed"

        stop = command("stop", session_id=session_id)
        put_command(bridge, stop)
        bridge.process_commands()
        stop_ack = json.loads(
            (bridge.outbox_dir / f"{stop['commandId']}.json").read_text()
        )
        assert stop_ack["status"] == "completed"
        assert runner.process.terminated is True
        final_state = json.loads(state_path.read_text())
        assert final_state["status"] == "stopped"
        assert final_state["errorCode"] == "stopped_by_request"
        assert not playlist.exists()
        assert not segment.exists()
    finally:
        shutdown_executor(bridge)


def test_session_expires_and_cleans_hls_media(tmp_path):
    camera = CameraSource(id=new_id(), name="Quintal", url="rtsp://camera/live")
    bridge, runner = make_bridge(tmp_path, camera)
    session_id = new_id()
    try:
        start = command("start", camera_id=camera.id, session_id=session_id)
        put_command(bridge, start)
        bridge.process_commands()
        session_dir = bridge.sessions_dir / session_id
        (session_dir / "index.m3u8").write_text("#EXTM3U\n")
        (session_dir / "000001.ts").write_bytes(b"segment")
        bridge.active_session.last_heartbeat = time.monotonic() - 100

        bridge._update_session()

        state = json.loads((session_dir / "session.json").read_text())
        assert state["status"] == "stopped"
        assert state["errorCode"] == "expired"
        assert runner.process.terminated is True
        assert not (session_dir / "index.m3u8").exists()
        assert not (session_dir / "000001.ts").exists()
    finally:
        shutdown_executor(bridge)


def test_live_session_watchdog_stops_stalled_ffmpeg(tmp_path):
    camera = CameraSource(id=new_id(), name="Quintal", url="rtsp://camera/live")
    bridge, runner = make_bridge(tmp_path, camera)
    session_id = new_id()
    try:
        start = command("start", camera_id=camera.id, session_id=session_id)
        put_command(bridge, start)
        bridge.process_commands()
        session_dir = bridge.sessions_dir / session_id
        (session_dir / "index.m3u8").write_text("#EXTM3U\n")
        (session_dir / "000001.ts").write_bytes(b"segment")
        bridge._update_session()
        assert bridge.active_session.status == "ready"

        bridge.active_session.last_media_progress = time.monotonic() - 30
        bridge._update_session()

        state = json.loads((session_dir / "session.json").read_text())
        assert state["status"] == "error"
        assert state["errorCode"] == "ffmpeg_start_failed"
        assert runner.process.terminated is True
        assert bridge.active_session is None
    finally:
        shutdown_executor(bridge)


def test_bridge_restart_terminates_only_matching_orphan_ffmpeg(
    monkeypatch,
    tmp_path,
):
    camera = CameraSource(id=new_id(), name="Quintal", url="rtsp://camera/live")
    bridge, _runner = make_bridge(tmp_path, camera)
    session_id = new_id()
    session_dir = bridge.sessions_dir / session_id
    session_dir.mkdir()
    created_at = datetime.now(UTC).isoformat()
    (session_dir / "session.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "sessionId": session_id,
                "cameraId": camera.id,
                "status": "ready",
                "createdAt": created_at,
                "updatedAt": created_at,
            }
        )
    )
    (session_dir / ".ffmpeg-process.json").write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "pid": 9123,
                "processCreatedAt": 123.0,
                "bridgeInstanceId": new_id(),
            }
        )
    )
    (session_dir / "index.m3u8").write_text("#EXTM3U\n")
    (session_dir / "000001.ts").write_bytes(b"segment")

    class Orphan:
        terminated = False

        def create_time(self):
            return 123.0

        def exe(self):
            return "C:/ffmpeg/bin/ffmpeg.exe"

        def cmdline(self):
            return ["ffmpeg", "-f", "hls", "index.m3u8"]

        def cwd(self):
            return str(session_dir)

        def is_running(self):
            return True

        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

    orphan = Orphan()
    monkeypatch.setattr(
        "varedura.camera_bridge.psutil.Process",
        lambda pid: orphan,
    )
    try:
        bridge._recover_orphan_sessions()
        assert orphan.terminated is True
        assert not (session_dir / ".ffmpeg-process.json").exists()
        assert not (session_dir / "index.m3u8").exists()
        assert not (session_dir / "000001.ts").exists()
        state = json.loads((session_dir / "session.json").read_text())
        assert state["status"] == "stopped"
        assert state["errorCode"] == "stopped_by_request"
    finally:
        shutdown_executor(bridge)


def test_invalid_command_cannot_inject_url_or_escape_session_dir(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, _runner = make_bridge(tmp_path, camera)
    try:
        malicious = command(
            "start",
            camera_id=camera.id,
            session_id="../../outside",
            url="rtsp://admin:secret@10.0.0.99/live",
        )
        put_command(bridge, malicious)
        bridge.process_commands()
        ack_path = bridge.outbox_dir / f"{malicious['commandId']}.json"
        ack = json.loads(ack_path.read_text())
        assert ack["status"] == "rejected"
        assert ack["errorCode"] == "unknown_fields"
        assert "rtsp://" not in ack_path.read_text()
        assert not (tmp_path / "outside").exists()
    finally:
        shutdown_executor(bridge)


def test_rejected_start_still_publishes_terminal_session_state(tmp_path):
    known = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, runner = make_bridge(tmp_path, known)
    missing_camera_id = new_id()
    session_id = new_id()
    try:
        start = command(
            "start",
            camera_id=missing_camera_id,
            session_id=session_id,
        )
        put_command(bridge, start)
        bridge.process_commands()

        state = json.loads(
            (bridge.sessions_dir / session_id / "session.json").read_text()
        )
        assert state["cameraId"] == missing_camera_id
        assert state["status"] == "error"
        assert state["errorCode"] == "camera_not_found"
        assert runner.start_calls == 0
    finally:
        shutdown_executor(bridge)


def test_stale_start_command_is_rejected_without_spawning(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, runner = make_bridge(tmp_path, camera)
    try:
        stale = command("start", camera_id=camera.id, session_id=new_id())
        stale["requestedAt"] = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
        put_command(bridge, stale)
        bridge.process_commands()

        ack = json.loads((bridge.outbox_dir / f"{stale['commandId']}.json").read_text())
        assert ack["status"] == "rejected"
        assert ack["errorCode"] == "command_expired"
        assert runner.start_calls == 0
        state = json.loads(
            (bridge.sessions_dir / stale["sessionId"] / "session.json").read_text()
        )
        assert state["status"] == "error"
        assert state["errorCode"] == "session_replaced"
    finally:
        shutdown_executor(bridge)


def test_command_idempotency_does_not_spawn_twice(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, runner = make_bridge(tmp_path, camera)
    start = command("start", camera_id=camera.id, session_id=new_id())
    try:
        put_command(bridge, start)
        bridge.process_commands()
        put_command(bridge, start)
        bridge.process_commands()
        assert runner.start_calls == 1
    finally:
        if bridge.active_session:
            bridge._stop_active("stopped_by_request")
        shutdown_executor(bridge)


def test_shutdown_command_stops_ffmpeg_and_requests_clean_exit(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, runner = make_bridge(tmp_path, camera)
    try:
        start = command("start", camera_id=camera.id, session_id=new_id())
        put_command(bridge, start)
        bridge.process_commands()

        shutdown = command("shutdown")
        put_command(bridge, shutdown)
        bridge.process_commands()

        ack = json.loads(
            (bridge.outbox_dir / f"{shutdown['commandId']}.json").read_text()
        )
        assert ack["status"] == "completed"
        assert bridge._stop_event.is_set()
        assert bridge.active_session is None
        assert runner.process.terminated is True
    finally:
        shutdown_executor(bridge)


def test_shutdown_tick_does_not_schedule_new_snapshots(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, runner = make_bridge(tmp_path, camera)
    shutdown = command("shutdown")
    try:
        put_command(bridge, shutdown)
        bridge.tick()
        assert bridge._stop_event.is_set()
        assert runner.capture_calls == 0
        assert not bridge._snapshot_futures
    finally:
        shutdown_executor(bridge)


def test_shutdown_in_once_mode_skips_all_snapshots(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    runner = FakeRunner()
    bridge = CameraBridge(
        tmp_path / "runtime" / "cameras",
        state_path=tmp_path / "private-state.json",
        ffmpeg_runner=runner,
        inventory_loader=lambda: [camera],
    )
    shutdown = command("shutdown")
    put_command(bridge, shutdown)

    bridge.run(once=True)

    assert runner.capture_calls == 0
    assert not bridge.pid_path.exists()
    assert not bridge.lock_path.exists()


def test_commands_are_processed_by_requested_at_not_uuid(monkeypatch, tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, _runner = make_bridge(tmp_path, camera)
    older_id = "ffffffff-ffff-4fff-bfff-ffffffffffff"
    newer_id = "00000000-0000-4000-8000-000000000000"
    now = datetime.now(UTC)
    older = command("refresh", command_id=older_id, camera_id=camera.id)
    older["requestedAt"] = (now - timedelta(seconds=2)).isoformat()
    newer = command("refresh", command_id=newer_id, camera_id=camera.id)
    newer["requestedAt"] = (now - timedelta(seconds=1)).isoformat()
    observed = []

    def fake_execute(data):
        observed.append(data["commandId"])
        return bridge._ack(data, "accepted")

    monkeypatch.setattr(bridge, "_execute_command", fake_execute)
    try:
        put_command(bridge, newer)
        put_command(bridge, older)
        bridge.process_commands()
        assert observed == [older_id, newer_id]
    finally:
        shutdown_executor(bridge)


def test_outbox_prunes_expired_ack_files(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, _runner = make_bridge(tmp_path, camera)
    try:
        old = bridge.outbox_dir / f"{new_id()}.json"
        old.write_text("{}")
        old_timestamp = time.time() - 7200
        utime(old, (old_timestamp, old_timestamp))
        recent = bridge.outbox_dir / f"{new_id()}.json"
        recent.write_text("{}")

        bridge._prune_outbox()

        assert not old.exists()
        assert recent.exists()
    finally:
        shutdown_executor(bridge)


def test_removed_camera_snapshot_is_pruned_after_retention(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, _runner = make_bridge(tmp_path, camera)
    old_orphan = bridge.snapshots_dir / f"{new_id()}.jpg"
    recent_orphan = bridge.snapshots_dir / f"{new_id()}.jpg"
    current = bridge.snapshots_dir / f"{camera.id}.jpg"
    for path in (old_orphan, recent_orphan, current):
        path.write_bytes(b"jpeg")
    old_timestamp = time.time() - (25 * 60 * 60)
    utime(old_orphan, (old_timestamp, old_timestamp))
    try:
        bridge._cleanup_orphan_snapshots()
        assert not old_orphan.exists()
        assert recent_orphan.exists()
        assert current.exists()
    finally:
        shutdown_executor(bridge)


def test_live_lock_rejects_second_bridge(monkeypatch, tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    first, _ = make_bridge(tmp_path, camera)
    second, _ = make_bridge(tmp_path, camera)
    monkeypatch.setattr(
        CameraBridge,
        "_record_is_live",
        staticmethod(lambda record, output: True),
    )
    try:
        first.acquire_lock()
        with pytest.raises(BridgeAlreadyRunning):
            second.acquire_lock()
    finally:
        first.release_lock()
        shutdown_executor(first)
        shutdown_executor(second)


def test_stale_lock_is_recovered(tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, _ = make_bridge(tmp_path, camera)
    bridge.lock_path.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "pid": 99999999,
                "instanceId": new_id(),
                "processCreatedAt": 1,
                "outputDir": str(bridge.output_dir),
            }
        )
    )
    stale_timestamp = time.time() - 10
    utime(bridge.lock_path, (stale_timestamp, stale_timestamp))
    try:
        bridge.acquire_lock()
        record = json.loads(bridge.lock_path.read_text())
        assert record["instanceId"] == bridge.instance_id
        pid_record = json.loads(bridge.pid_path.read_text())
        assert pid_record["command"] == "varedura-camera-bridge"
    finally:
        bridge.release_lock()
        shutdown_executor(bridge)


def test_startup_recovery_failure_rolls_back_pid_and_lock(monkeypatch, tmp_path):
    camera = CameraSource(id=new_id(), name="Sala", url="rtsp://private/live")
    bridge, _runner = make_bridge(tmp_path, camera)

    def fail_recovery():
        raise OSError("simulated locked media")

    monkeypatch.setattr(bridge, "_recover_orphan_sessions", fail_recovery)
    try:
        with pytest.raises(OSError):
            bridge.acquire_lock()
        assert not bridge.pid_path.exists()
        assert not bridge.lock_path.exists()
    finally:
        shutdown_executor(bridge)


def test_runtime_subdirectory_link_is_rejected(monkeypatch, tmp_path):
    output = tmp_path / "runtime" / "cameras"
    bridge = CameraBridge(
        output,
        state_path=tmp_path / "state.json",
        ffmpeg_runner=FakeRunner(),
        inventory_loader=lambda: [],
    )
    original_is_symlink = Path.is_symlink

    def fake_is_symlink(path):
        return path.name == "sessions" or original_is_symlink(path)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)
    try:
        with pytest.raises(OSError):
            bridge._ensure_directories()
    finally:
        shutdown_executor(bridge)
