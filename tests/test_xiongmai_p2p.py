"""Unit tests for Xiongmai NetIP and Sofia Cloud P2P protocol engine."""

import json
import socket
import struct
import threading
import time
import pytest

from rtsp.xiongmai import (
    DEFAULT_NETIP_PORT,
    NETIP_HEADER_FORMAT,
    NETIP_HEADER_SIZE,
    NETIP_MAGIC,
    NetIPMsgId,
    NetIPPacket,
    PTZCommand,
    SofiaP2PClient,
    XiongmaiDiscovery,
    XiongmaiNetIPClient,
    encrypt_xiongmai_digest,
    encrypt_xiongmai_password,
)


def test_netip_packet_serialization():
    payload = b'{"Test": 123}'
    pkt = NetIPPacket(
        session_id=0x12345678,
        sequence_number=42,
        total_packet=1,
        cur_packet=0,
        msg_id=NetIPMsgId.LOGIN_REQ,
        payload=payload,
    )
    raw = pkt.to_bytes()

    assert len(raw) == NETIP_HEADER_SIZE + len(payload)
    assert raw[:4] == NETIP_MAGIC

    decoded, consumed = NetIPPacket.from_bytes(raw)
    assert decoded is not None
    assert consumed == len(raw)
    assert decoded.session_id == 0x12345678
    assert decoded.sequence_number == 42
    assert decoded.total_packet == 1
    assert decoded.cur_packet == 0
    assert decoded.msg_id == NetIPMsgId.LOGIN_REQ
    assert decoded.payload == payload
    assert decoded.get_json() == {"Test": 123}


def test_netip_packet_incomplete_buffer():
    payload = b'{"Name": "Test"}'
    pkt = NetIPPacket(msg_id=1000, payload=payload)
    raw = pkt.to_bytes()

    # Buffer smaller than header
    d1, c1 = NetIPPacket.from_bytes(raw[:10])
    assert d1 is None and c1 == 0

    # Buffer smaller than total packet
    d2, c2 = NetIPPacket.from_bytes(raw[: NETIP_HEADER_SIZE + 2])
    assert d2 is None and c2 == 0


def test_xiongmai_password_encryption():
    assert encrypt_xiongmai_password("") == ""
    h1 = encrypt_xiongmai_password("admin")
    assert isinstance(h1, str) and len(h1) == 32
    assert h1 == "21232f297a57a5a743894a0e4a801fc3"

    d1 = encrypt_xiongmai_digest("admin")
    assert isinstance(d1, str) and len(d1) > 0


class MockNetIPServer:
    """In-memory mock Xiongmai NetIP server for integration testing."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((host, port))
        self.port = self.sock.getsockname()[1]
        self.host = host
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        self.sock.listen(5)
        self.sock.settimeout(0.5)
        while self.running:
            try:
                conn, _ = self.sock.accept()
            except socket.timeout:
                continue
            except Exception:
                break

            conn.settimeout(2.0)
            recv_buf = bytearray()
            session_id = 0x00000001

            while self.running:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    recv_buf.extend(chunk)
                    pkt, consumed = NetIPPacket.from_bytes(bytes(recv_buf))
                    if not pkt:
                        continue
                    recv_buf = recv_buf[consumed:]

                    # Handle request
                    if pkt.msg_id == NetIPMsgId.LOGIN_REQ:
                        resp_data = {
                            "Ret": 100,
                            "SessionID": f"0x{session_id:08x}",
                            "AliveInterval": 30,
                        }
                        resp_payload = json.dumps(resp_data).encode("utf-8") + b"\n\x00"
                        resp_pkt = NetIPPacket(
                            session_id=session_id,
                            sequence_number=pkt.sequence_number,
                            msg_id=NetIPMsgId.LOGIN_RESP,
                            payload=resp_payload,
                        )
                        conn.sendall(resp_pkt.to_bytes())

                    elif pkt.msg_id == NetIPMsgId.SYSINFO_REQ:
                        resp_data = {
                            "Ret": 100,
                            "SessionID": f"0x{session_id:08x}",
                            "SystemInfo": {
                                "DeviceModel": "XM530_iCSee",
                                "SoftWareVersion": "V4.02.R12.00035520.12002.140200.00000",
                                "ChannelNum": 1,
                            },
                        }
                        resp_payload = json.dumps(resp_data).encode("utf-8") + b"\n\x00"
                        resp_pkt = NetIPPacket(
                            session_id=session_id,
                            sequence_number=pkt.sequence_number,
                            msg_id=NetIPMsgId.SYSINFO_RESP,
                            payload=resp_payload,
                        )
                        conn.sendall(resp_pkt.to_bytes())

                    elif pkt.msg_id == NetIPMsgId.PTZ_REQ:
                        resp_data = {"Ret": 100, "SessionID": f"0x{session_id:08x}"}
                        resp_payload = json.dumps(resp_data).encode("utf-8") + b"\n\x00"
                        resp_pkt = NetIPPacket(
                            session_id=session_id,
                            sequence_number=pkt.sequence_number,
                            msg_id=NetIPMsgId.PTZ_RESP,
                            payload=resp_payload,
                        )
                        conn.sendall(resp_pkt.to_bytes())

                    elif pkt.msg_id == NetIPMsgId.SNAP_REQ:
                        # Return valid minimal JPEG SOI/EOI
                        fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
                        resp_pkt = NetIPPacket(
                            session_id=session_id,
                            sequence_number=pkt.sequence_number,
                            msg_id=NetIPMsgId.SNAP_RESP,
                            payload=fake_jpeg,
                        )
                        conn.sendall(resp_pkt.to_bytes())

                    elif pkt.msg_id == NetIPMsgId.CONFIG_SET_REQ:
                        resp_data = {"Ret": 100, "SessionID": f"0x{session_id:08x}"}
                        resp_payload = json.dumps(resp_data).encode("utf-8") + b"\n\x00"
                        resp_pkt = NetIPPacket(
                            session_id=session_id,
                            sequence_number=pkt.sequence_number,
                            msg_id=NetIPMsgId.CONFIG_SET_RESP,
                            payload=resp_payload,
                        )
                        conn.sendall(resp_pkt.to_bytes())

                    elif pkt.msg_id == NetIPMsgId.KEEPALIVE_REQ:
                        resp_data = {"Ret": 100, "SessionID": f"0x{session_id:08x}"}
                        resp_payload = json.dumps(resp_data).encode("utf-8") + b"\n\x00"
                        resp_pkt = NetIPPacket(
                            session_id=session_id,
                            sequence_number=pkt.sequence_number,
                            msg_id=NetIPMsgId.KEEPALIVE_RESP,
                            payload=resp_payload,
                        )
                        conn.sendall(resp_pkt.to_bytes())
                except Exception:
                    break
            conn.close()

    def stop(self):
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass


def test_netip_client_workflow():
    server = MockNetIPServer()
    try:
        client = XiongmaiNetIPClient(
            host=server.host,
            port=server.port,
            username="admin",
            password="password123",
            timeout=2.0,
        )

        # 1. Connect and login
        assert client.connect() is True
        assert client.session_id == 0x00000001

        # 2. System info query
        info = client.get_system_info()
        assert info.get("DeviceModel") == "XM530_iCSee"

        # 3. PTZ Control
        assert client.ptz_control(PTZCommand.UP, step=5, stop_after_delay=0.1) is True
        assert client.ptz_stop() is True

        # 4. Snapshot
        snap = client.capture_snapshot()
        assert snap is not None
        assert snap.startswith(b"\xff\xd8") and snap.endswith(b"\xff\xd9")

        # 5. Enable RTSP/ONVIF
        assert client.enable_onvif_rtsp(rtsp_port=554) is True

        # 6. Keepalive
        assert client.send_keepalive() is True

        # 7. Close
        client.close()
        assert client._connected is False
    finally:
        server.stop()
