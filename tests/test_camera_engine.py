"""Unit tests for the Unified Camera Engine."""

import pytest
from rtsp.camera_engine import (
    CameraFleetManager,
    CameraProtocol,
    UnifiedCameraSource,
    parse_camera_url,
)
from tests.test_xiongmai_p2p import MockNetIPServer


def test_parse_camera_url():
    # RTSP URL
    p1 = parse_camera_url("rtsp://admin:pass123@192.168.1.50:554/live/ch0")
    assert p1["protocol"] == CameraProtocol.RTSP
    assert p1["host"] == "192.168.1.50"
    assert p1["port"] == 554
    assert p1["username"] == "admin"
    assert p1["password"] == "pass123"
    assert p1["path"] == "/live/ch0"

    # iCSee / NetIP URL
    p2 = parse_camera_url("icsee://admin:@192.168.1.60")
    assert p2["protocol"] == CameraProtocol.ICSEE_NETIP
    assert p2["host"] == "192.168.1.60"
    assert p2["port"] == 34567

    # Sofia P2P URL
    p3 = parse_camera_url("p2p://admin:secret@d76a0123456789ab")
    assert p3["protocol"] == CameraProtocol.SOFIA_P2P
    assert p3["host"] == "d76a0123456789ab"
    assert p3["username"] == "admin"
    assert p3["password"] == "secret"


def test_unified_camera_source_netip():
    server = MockNetIPServer()
    try:
        source = UnifiedCameraSource(
            url=f"icsee://admin:pass123@{server.host}:{server.port}",
            camera_id="test_cam_01",
            name="Front Porch",
        )

        assert source.protocol == CameraProtocol.ICSEE_NETIP
        assert source.camera_id == "test_cam_01"

        meta = source.validate()
        assert meta.is_online is True
        assert meta.capabilities.ptz is True

        snap = source.capture_snapshot()
        assert snap is not None
        assert snap.startswith(b"\xff\xd8")

        assert source.ptz_move("DirectionUp", step=4) is True
        assert source.ptz_stop() is True

        source.close()
    finally:
        server.stop()


def test_camera_fleet_manager():
    fleet = CameraFleetManager()
    cam1 = fleet.register_camera("rtsp://admin:pass@192.168.1.10/stream")
    cam2 = fleet.register_camera("icsee://admin:1234@192.168.1.20:34567")

    assert len(fleet.list_cameras()) == 2
    assert fleet.get_camera(cam1.camera_id) is not None
    assert fleet.get_camera(cam2.camera_id) is not None

    fleet.close_all()
    assert len(fleet.list_cameras()) == 0
