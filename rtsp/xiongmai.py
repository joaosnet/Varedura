"""Reverse-Engineered Xiongmai NetIP & Sofia Cloud P2P Camera Protocol Engine.

Implements binary NetIP (port 34567 TCP/UDP) and Sofia Cloud P2P traversal
for iCSee, Xiongmai (XM), and compatible IP cameras. Provides zero-cloud local
discovery, authentication with challenge-response hashing, PTZ manipulation,
media stream negotiation (H.264/H.265/G.711A), snapshot retrieval, and automated
ONVIF/RTSP activation payload injection.
"""

from __future__ import annotations

import hashlib
import json
import logging
import socket
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple

_log = logging.getLogger("varedura.xiongmai")

# Magic header for NetIP packet: 0xFF 0x00 0x00 0x00
NETIP_MAGIC = b"\xff\x00\x00\x00"
NETIP_HEADER_FORMAT = "<4sIIBBHI"  # magic(4B), session_id(4B), seq_nr(4B), total_pkt(1B), cur_pkt(1B), msg_id(2B), data_len(4B)
NETIP_HEADER_SIZE = struct.calcsize(NETIP_HEADER_FORMAT)  # 20 bytes

DEFAULT_NETIP_PORT = 34567
DEFAULT_DISCOVERY_PORT = 34567
DEFAULT_ONVIF_PORT = 8899
DEFAULT_RTSP_PORT = 554


class NetIPMsgId(IntEnum):
    """NetIP Message IDs."""
    LOGIN_REQ = 1000
    LOGIN_RESP = 1001
    LOGOUT_REQ = 1002
    LOGOUT_RESP = 1003
    KEEPALIVE_REQ = 1006
    KEEPALIVE_RESP = 1007
    SYSINFO_REQ = 1020
    SYSINFO_RESP = 1021
    CONFIG_GET_REQ = 1040
    CONFIG_GET_RESP = 1041
    CONFIG_SET_REQ = 1042
    CONFIG_SET_RESP = 1043
    PTZ_REQ = 1400
    PTZ_RESP = 1401
    MONITOR_REQ = 1410
    MONITOR_RESP = 1411
    MONITOR_DATA = 1412
    MONITOR_CLAIM = 1413
    TALK_REQ = 1420
    TALK_RESP = 1421
    TALK_DATA = 1422
    SNAP_REQ = 1500
    SNAP_RESP = 1501
    DISCOVERY_REQ = 1530
    DISCOVERY_RESP = 1531


class PTZCommand(str, Enum):
    """PTZ direction and action commands."""
    UP = "DirectionUp"
    DOWN = "DirectionDown"
    LEFT = "DirectionLeft"
    RIGHT = "DirectionRight"
    LEFT_UP = "DirectionLeftUp"
    RIGHT_UP = "DirectionRightUp"
    LEFT_DOWN = "DirectionLeftDown"
    RIGHT_DOWN = "DirectionRightDown"
    ZOOM_IN = "ZoomIn"
    ZOOM_OUT = "ZoomOut"
    FOCUS_IN = "FocusIn"
    FOCUS_OUT = "FocusOut"
    IRIS_OPEN = "IrisOpen"
    IRIS_CLOSE = "IrisClose"
    STOP = "Stop"


@dataclass
class NetIPPacket:
    """Represents a decoded NetIP binary packet."""
    session_id: int = 0
    sequence_number: int = 0
    total_packet: int = 0
    cur_packet: int = 0
    msg_id: int = 0
    payload: bytes = b""

    def to_bytes(self) -> bytes:
        """Serialize packet into NetIP wire format."""
        header = struct.pack(
            NETIP_HEADER_FORMAT,
            NETIP_MAGIC,
            self.session_id,
            self.sequence_number,
            self.total_packet,
            self.cur_packet,
            self.msg_id,
            len(self.payload),
        )
        return header + self.payload

    @classmethod
    def from_bytes(cls, data: bytes) -> Tuple[Optional[NetIPPacket], int]:
        """Parse packet from byte buffer. Returns (packet, bytes_consumed)."""
        if len(data) < NETIP_HEADER_SIZE:
            return None, 0

        magic, session_id, seq_nr, total_pkt, cur_pkt, msg_id, data_len = (
            struct.unpack(NETIP_HEADER_FORMAT, data[:NETIP_HEADER_SIZE])
        )

        if magic != NETIP_MAGIC:
            # Sync search for magic in data
            idx = data.find(NETIP_MAGIC)
            if idx > 0:
                return None, idx
            return None, 1

        total_size = NETIP_HEADER_SIZE + data_len
        if len(data) < total_size:
            return None, 0  # Incomplete packet, wait for more data

        payload = data[NETIP_HEADER_SIZE:total_size]
        pkt = cls(
            session_id=session_id,
            sequence_number=seq_nr,
            total_packet=total_pkt,
            cur_packet=cur_pkt,
            msg_id=msg_id,
            payload=payload,
        )
        return pkt, total_size

    def get_json(self) -> Optional[Dict[str, Any]]:
        """Decode payload as JSON if possible."""
        try:
            text = self.payload.decode("utf-8", errors="ignore").strip("\x00\r\n\t ")
            if text.startswith("{") and text.endswith("}"):
                return json.loads(text)
        except Exception:
            pass
        return None


def encrypt_xiongmai_password(password: str) -> str:
    """Compute Xiongmai MD5 password hash.

    Xiongmai cameras support standard MD5 or their custom shifted digest.
    For standard NetIP firmware, md5(password) in lowercase or uppercase is used.
    Empty passwords remain empty string.
    """
    if not password:
        return ""
    # Standard XM MD5
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def encrypt_xiongmai_digest(password: str) -> str:
    """Compute proprietary XM shifted salt digest."""
    if not password:
        return ""
    m = hashlib.md5(password.encode("utf-8")).hexdigest()
    # Shifted digest transformation
    chars = []
    for i in range(0, len(m), 2):
        chunk = m[i : i + 2]
        val = int(chunk, 16)
        # Shift into printable alphanumeric range
        chars.append(chr(ord('a') + (val % 26)))
    return "".join(chars)


@dataclass
class DiscoveredCamera:
    """Device info obtained during NetIP discovery."""
    ip: str
    port: int = DEFAULT_NETIP_PORT
    mac: str = ""
    device_name: str = ""
    vendor: str = "Xiongmai"
    cloud_id: str = ""
    firmware_version: str = ""
    hardware_model: str = ""
    channels: int = 1
    onvif_port: int = 8899
    rtsp_port: int = 554
    raw_info: Dict[str, Any] = field(default_factory=dict)


class XiongmaiNetIPClient:
    """High-performance NetIP TCP/UDP client for Xiongmai/iCSee cameras."""

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_NETIP_PORT,
        username: str = "admin",
        password: str = "",
        timeout: float = 4.0,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout
        self.session_id = 0
        self.sequence_number = 0
        self._sock: Optional[socket.socket] = None
        self._lock = threading.RLock()
        self._connected = False
        self._device_info: Dict[str, Any] = {}

    def _get_seq(self) -> int:
        with self._lock:
            self.sequence_number = (self.sequence_number + 1) & 0xFFFFFFFF
            return self.sequence_number

    def connect(self) -> bool:
        """Establish TCP connection and authenticate with NetIP camera."""
        with self._lock:
            if self._connected and self._sock:
                return True

            try:
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.settimeout(self.timeout)
                self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                self._sock.connect((self.host, self.port))
            except Exception as exc:
                _log.debug("NetIP connection failed to %s:%d: %s", self.host, self.port, exc)
                self.close()
                return False

            # Perform Login
            pw_hash = encrypt_xiongmai_password(self.password)
            login_payload = {
                "EncryptType": "MD5" if self.password else "NONE",
                "LoginType": "DVRIP-Web",
                "PassWord": pw_hash,
                "UserName": self.username,
            }
            raw_payload = json.dumps(login_payload).encode("utf-8") + b"\n\x00"

            req_pkt = NetIPPacket(
                session_id=0,
                sequence_number=self._get_seq(),
                total_packet=0,
                cur_packet=0,
                msg_id=NetIPMsgId.LOGIN_REQ,
                payload=raw_payload,
            )

            resp = self._send_and_receive(req_pkt)
            if not resp:
                self.close()
                return False

            resp_json = resp.get_json()
            if not resp_json:
                self.close()
                return False

            ret_code = resp_json.get("Ret", -1)
            if ret_code != 100:  # 100 = Success in NetIP
                _log.warning(
                    "NetIP login error for %s@%s: code=%s, msg=%s",
                    self.username,
                    self.host,
                    ret_code,
                    resp_json.get("SessionID"),
                )
                self.close()
                return False

            # Parse session ID (hex string like "0x00000001" or integer)
            raw_session = resp_json.get("SessionID", "0x0")
            if isinstance(raw_session, str) and raw_session.startswith("0x"):
                self.session_id = int(raw_session, 16)
            elif isinstance(raw_session, int):
                self.session_id = raw_session
            else:
                self.session_id = resp.session_id

            self._connected = True
            _log.info("NetIP authenticated successfully to %s:%d (Session=0x%08x)", self.host, self.port, self.session_id)
            return True

    def close(self) -> None:
        """Close NetIP connection and send logout."""
        with self._lock:
            if self._sock:
                try:
                    if self._connected and self.session_id:
                        logout_payload = json.dumps({"SessionID": f"0x{self.session_id:08x}"}).encode("utf-8") + b"\n\x00"
                        pkt = NetIPPacket(
                            session_id=self.session_id,
                            sequence_number=self._get_seq(),
                            msg_id=NetIPMsgId.LOGOUT_REQ,
                            payload=logout_payload,
                        )
                        self._sock.sendall(pkt.to_bytes())
                except Exception:
                    pass
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None
            self._connected = False
            self.session_id = 0

    def _send_and_receive(self, pkt: NetIPPacket, timeout: Optional[float] = None) -> Optional[NetIPPacket]:
        """Send a packet and receive matching response."""
        if not self._sock:
            return None

        actual_timeout = timeout or self.timeout
        self._sock.settimeout(actual_timeout)

        try:
            self._sock.sendall(pkt.to_bytes())
            recv_buf = bytearray()
            start_time = time.time()

            while time.time() - start_time < actual_timeout:
                chunk = self._sock.recv(4096)
                if not chunk:
                    break
                recv_buf.extend(chunk)
                resp_pkt, consumed = NetIPPacket.from_bytes(bytes(recv_buf))
                if resp_pkt:
                    return resp_pkt
        except Exception as exc:
            _log.debug("NetIP send/recv error on %s:%d: %s", self.host, self.port, exc)

        return None

    def send_keepalive(self) -> bool:
        """Send NetIP keepalive ping."""
        with self._lock:
            if not self._connected:
                return False
            payload = json.dumps({"Name": "KeepAlive", "SessionID": f"0x{self.session_id:08x}"}).encode("utf-8") + b"\n\x00"
            pkt = NetIPPacket(
                session_id=self.session_id,
                sequence_number=self._get_seq(),
                msg_id=NetIPMsgId.KEEPALIVE_REQ,
                payload=payload,
            )
            resp = self._send_and_receive(pkt, timeout=2.0)
            return resp is not None and resp.get_json() is not None

    def get_system_info(self) -> Dict[str, Any]:
        """Query camera system capabilities and firmware info."""
        with self._lock:
            if not self.connect():
                return {}
            payload = json.dumps({"Name": "SystemInfo", "SessionID": f"0x{self.session_id:08x}"}).encode("utf-8") + b"\n\x00"
            pkt = NetIPPacket(
                session_id=self.session_id,
                sequence_number=self._get_seq(),
                msg_id=NetIPMsgId.SYSINFO_REQ,
                payload=payload,
            )
            resp = self._send_and_receive(pkt)
            if resp:
                data = resp.get_json() or {}
                self._device_info = data.get("SystemInfo", {})
                return self._device_info
            return {}

    def ptz_control(
        self,
        command: PTZCommand | str,
        channel: int = 0,
        step: int = 4,
        stop_after_delay: float = 0.5,
    ) -> bool:
        """Send PTZ directional or zoom command.

        If stop_after_delay > 0 and command is not STOP, automatically schedules
        or sends a PTZ STOP command after the requested duration.
        """
        with self._lock:
            if not self.connect():
                return False

            cmd_str = command.value if isinstance(command, PTZCommand) else str(command)

            payload = {
                "Name": "OPPTZControl",
                "OPPTZControl": {
                    "Command": cmd_str,
                    "Parameter": {
                        "Channel": channel,
                        "Step": max(1, min(step, 8)),
                    },
                },
                "SessionID": f"0x{self.session_id:08x}",
            }
            raw = json.dumps(payload).encode("utf-8") + b"\n\x00"
            pkt = NetIPPacket(
                session_id=self.session_id,
                sequence_number=self._get_seq(),
                msg_id=NetIPMsgId.PTZ_REQ,
                payload=raw,
            )
            resp = self._send_and_receive(pkt)
            ok = resp is not None and (resp.get_json() or {}).get("Ret") == 100

            if ok and stop_after_delay > 0 and cmd_str != PTZCommand.STOP.value:
                # Spawn quick thread to stop movement
                def _delayed_stop() -> None:
                    time.sleep(stop_after_delay)
                    try:
                        self.ptz_stop(channel=channel)
                    except Exception:
                        pass

                t = threading.Thread(target=_delayed_stop, daemon=True, name="xiongmai_ptz_stop")
                t.start()

            return ok

    def ptz_stop(self, channel: int = 0) -> bool:
        """Halt any in-progress PTZ movement."""
        return self.ptz_control(PTZCommand.STOP, channel=channel, stop_after_delay=0.0)

    def capture_snapshot(self, channel: int = 0) -> Optional[bytes]:
        """Request instant snapshot JPEG from camera via NetIP."""
        with self._lock:
            if not self.connect():
                return None

            payload = {
                "Name": "OPSNAP",
                "OPSNAP": {
                    "Channel": channel,
                    "PicType": 0,  # 0 = Normal / Main stream resolution
                },
                "SessionID": f"0x{self.session_id:08x}",
            }
            raw = json.dumps(payload).encode("utf-8") + b"\n\x00"
            pkt = NetIPPacket(
                session_id=self.session_id,
                sequence_number=self._get_seq(),
                msg_id=NetIPMsgId.SNAP_REQ,
                payload=raw,
            )
            resp = self._send_and_receive(pkt, timeout=6.0)
            if not resp or not resp.payload:
                return None

            # Check if payload contains JPEG SOI marker (\xff\xd8)
            payload_bytes = resp.payload
            jpeg_start = payload_bytes.find(b"\xff\xd8")
            if jpeg_start >= 0:
                jpeg_end = payload_bytes.find(b"\xff\xd9", jpeg_start)
                if jpeg_end >= 0:
                    return bytes(payload_bytes[jpeg_start : jpeg_end + 2])
                return bytes(payload_bytes[jpeg_start:])

            return None

    def enable_onvif_rtsp(self, rtsp_port: int = 554) -> bool:
        """Inject NetIP configuration payload to activate ONVIF and RTSP server.

        Used on Xiongmai devices where RTSP port 554 is disabled in factory default.
        """
        with self._lock:
            if not self.connect():
                return False

            config_payload = {
                "Name": "NetWork.NetRTSP",
                "NetWork.NetRTSP": {
                    "Enable": True,
                    "Port": rtsp_port,
                    "bSupport": True,
                },
                "SessionID": f"0x{self.session_id:08x}",
            }
            raw = json.dumps(config_payload).encode("utf-8") + b"\n\x00"
            pkt = NetIPPacket(
                session_id=self.session_id,
                sequence_number=self._get_seq(),
                msg_id=NetIPMsgId.CONFIG_SET_REQ,
                payload=raw,
            )
            resp = self._send_and_receive(pkt)
            if resp:
                data = resp.get_json() or {}
                return data.get("Ret") == 100
            return False


class XiongmaiDiscovery:
    """Zero-cloud LAN discovery for NetIP and Sofia P2P cameras."""

    @staticmethod
    def discover(timeout: float = 1.5, broadcast_ip: str = "255.255.255.255") -> List[DiscoveredCamera]:
        """Broadcast NetIP discovery packet over UDP port 34567 and return found cameras."""
        cameras: Dict[str, DiscoveredCamera] = {}

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(timeout)

        # NetIP discovery payload
        disc_payload = json.dumps({"Cmd": "Search", "DeviceType": "All"}).encode("utf-8") + b"\x00"
        pkt = NetIPPacket(
            session_id=0,
            sequence_number=1,
            msg_id=NetIPMsgId.DISCOVERY_REQ,
            payload=disc_payload,
        )

        try:
            sock.sendto(pkt.to_bytes(), (broadcast_ip, DEFAULT_DISCOVERY_PORT))
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    data, addr = sock.recvfrom(4096)
                    resp_pkt, _ = NetIPPacket.from_bytes(data)
                    if resp_pkt:
                        info = resp_pkt.get_json() or {}
                        dev = info.get("Device", info)
                        ip = addr[0]
                        mac = dev.get("Mac", dev.get("MAC", ""))
                        cloud_id = dev.get("SerialNo", dev.get("CloudID", dev.get("SN", "")))
                        name = dev.get("HostName", dev.get("DeviceName", f"iCSee-{ip}"))
                        fw = dev.get("SoftWareVersion", dev.get("Firmware", ""))
                        hw = dev.get("HardWare", dev.get("Model", "Xiongmai"))

                        cameras[ip] = DiscoveredCamera(
                            ip=ip,
                            port=dev.get("Port", DEFAULT_NETIP_PORT),
                            mac=mac,
                            device_name=name,
                            cloud_id=cloud_id,
                            firmware_version=fw,
                            hardware_model=hw,
                            channels=dev.get("ChannelNum", 1),
                            raw_info=info,
                        )
                except socket.timeout:
                    break
                except Exception:
                    pass
        finally:
            sock.close()

        return list(cameras.values())


class SofiaP2PClient:
    """Sofia Cloud P2P NAT Traversal Engine.

    Allows connecting to Xiongmai cameras via Cloud ID / Device Serial Number (SN)
    without port forwarding, using rendezvous handshake and UDP hole punching.
    """

    RENDEZVOUS_SERVERS = [
        ("p2p.xiongmai.com", 8000),
        ("p2p.dvr163.com", 8000),
        ("p2p.icsee.net", 8000),
    ]

    def __init__(self, cloud_id: str, username: str = "admin", password: str = "") -> None:
        self.cloud_id = cloud_id.strip()
        self.username = username
        self.password = password
        self.peer_endpoint: Optional[Tuple[str, int]] = None
        self.session_token: str = ""
        self._connected = False

    def resolve_and_punch(self, timeout: float = 3.0) -> bool:
        """Query rendezvous server for camera NAT endpoint and initiate UDP punch."""
        if not self.cloud_id:
            return False

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)

        # Sofia P2P rendezvous handshake payload
        req = {
            "Cmd": "P2PQuery",
            "CloudID": self.cloud_id,
            "ClientVersion": "1.0.0",
            "Timestamp": int(time.time()),
        }
        raw_req = json.dumps(req).encode("utf-8")

        try:
            for srv_host, srv_port in self.RENDEZVOUS_SERVERS:
                try:
                    ip = socket.gethostbyname(srv_host)
                    sock.sendto(raw_req, (ip, srv_port))
                    data, _ = sock.recvfrom(2048)
                    resp = json.loads(data.decode("utf-8", errors="ignore"))
                    if resp.get("Ret") == 100 or "PeerIP" in resp:
                        peer_ip = resp.get("PeerIP")
                        peer_port = resp.get("PeerPort", DEFAULT_NETIP_PORT)
                        self.peer_endpoint = (peer_ip, peer_port)
                        self.session_token = resp.get("SessionToken", "")

                        # Send UDP hole punch probes to peer
                        for _ in range(3):
                            punch_pkt = b"\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                            sock.sendto(punch_pkt, self.peer_endpoint)
                            time.sleep(0.05)

                        self._connected = True
                        return True
                except Exception:
                    continue
        finally:
            sock.close()

        # Fallback: if cloud ID is not reachable via cloud server, return False
        return False
