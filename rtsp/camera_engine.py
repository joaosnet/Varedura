"""Unified Camera Engine supporting RTSP, iCSee/NetIP, Sofia P2P, and ONVIF streams.

Provides a unified interface for camera discovery, validation, frame extraction,
PTZ manipulation, audio talk, and stream URL resolution.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import socket
import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, unquote, urlsplit, urlunsplit

from rtsp.video import InfoStream, validar_stream
from rtsp.xiongmai import (
    DEFAULT_NETIP_PORT,
    DiscoveredCamera,
    NetIPPacket,
    PTZCommand,
    SofiaP2PClient,
    XiongmaiDiscovery,
    XiongmaiNetIPClient,
)

_log = logging.getLogger("varedura.camera_engine")


class CameraProtocol(str, Enum):
    """Supported camera transport and control protocols."""
    RTSP = "rtsp"
    ICSEE_NETIP = "icsee"
    SOFIA_P2P = "p2p"
    ONVIF = "onvif"
    HTTP_MJPEG = "http"
    UNKNOWN = "unknown"


@dataclass
class CameraCapabilities:
    """Hardware and protocol capabilities detected for a camera."""
    ptz: bool = False
    ptz_presets: bool = False
    two_way_audio: bool = False
    snapshot_endpoint: bool = False
    onvif: bool = False
    h264: bool = True
    h265: bool = False
    multi_stream: bool = True


@dataclass
class CameraMetadata:
    """Comprehensive camera status and metadata."""
    camera_id: str
    name: str
    protocol: CameraProtocol
    source_url: str
    resolved_stream_url: str = ""
    snapshot_url: str = ""
    ip: str = ""
    port: int = 554
    username: Optional[str] = None
    password: Optional[str] = None
    cloud_id: Optional[str] = None
    is_online: bool = False
    codec: str = "h264"
    resolution: str = "1920x1080"
    fps: float = 25.0
    capabilities: CameraCapabilities = field(default_factory=CameraCapabilities)
    last_seen: float = field(default_factory=time.time)
    last_error: Optional[str] = None
    extra_attributes: Dict[str, Any] = field(default_factory=dict)


def parse_camera_url(url: str) -> Dict[str, Any]:
    """Parse custom camera URIs into protocol, host, port, credentials, and parameters.

    Supported schemes:
    - rtsp://[user:pass@]host[:port]/path
    - icsee://[user:pass@]host[:port][/stream]
    - p2p://[user:pass@]cloud_id[/stream]
    - onvif://[user:pass@]host[:port]
    - http://[user:pass@]host[:port]/snapshot.jpg
    """
    cleaned = url.strip()
    parsed = urlsplit(cleaned)
    scheme = parsed.scheme.lower()

    protocol = CameraProtocol.UNKNOWN
    if scheme in ("rtsp", "rtsps"):
        protocol = CameraProtocol.RTSP
    elif scheme in ("icsee", "netip", "xm"):
        protocol = CameraProtocol.ICSEE_NETIP
    elif scheme in ("p2p", "sofia"):
        protocol = CameraProtocol.SOFIA_P2P
    elif scheme in ("onvif", "onvifs"):
        protocol = CameraProtocol.ONVIF
    elif scheme in ("http", "https"):
        protocol = CameraProtocol.HTTP_MJPEG

    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    host = parsed.hostname or ""
    port = parsed.port

    if protocol == CameraProtocol.ICSEE_NETIP and not port:
        port = DEFAULT_NETIP_PORT
    elif protocol == CameraProtocol.RTSP and not port:
        port = 554
    elif protocol == CameraProtocol.ONVIF and not port:
        port = 8899

    return {
        "protocol": protocol,
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "path": parsed.path,
        "query": parse_qs(parsed.query),
        "raw_url": url,
    }


class UnifiedCameraSource:
    """High-level abstraction for interacting with any IP or P2P camera."""

    def __init__(
        self,
        url: str,
        camera_id: Optional[str] = None,
        name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.raw_url = url
        parsed = parse_camera_url(url)
        self.protocol = parsed["protocol"]
        self.host = parsed["host"]
        self.port = parsed["port"] or 554
        self.username = username or parsed["username"] or "admin"
        self.password = password or parsed["password"] or ""
        self.path = parsed["path"] or ""
        self.camera_id = camera_id or f"cam_{hashlib.sha256(url.encode()).hexdigest()[:12]}"
        self.name = name or f"Camera-{self.host or self.camera_id[:8]}"

        self._netip_client: Optional[XiongmaiNetIPClient] = None
        self._p2p_client: Optional[SofiaP2PClient] = None
        self._metadata: CameraMetadata = CameraMetadata(
            camera_id=self.camera_id,
            name=self.name,
            protocol=self.protocol,
            source_url=self.raw_url,
            ip=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
        )
        self._lock = threading.RLock()

        if self.protocol == CameraProtocol.ICSEE_NETIP:
            self._netip_client = XiongmaiNetIPClient(
                host=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
            )
            self._metadata.capabilities.ptz = True
            self._metadata.capabilities.two_way_audio = True
            self._metadata.capabilities.snapshot_endpoint = True
        elif self.protocol == CameraProtocol.SOFIA_P2P:
            self._p2p_client = SofiaP2PClient(
                cloud_id=self.host,
                username=self.username,
                password=self.password,
            )
            self._metadata.capabilities.ptz = True
            self._metadata.capabilities.two_way_audio = True

    @property
    def metadata(self) -> CameraMetadata:
        with self._lock:
            return self._metadata

    def validate(self) -> CameraMetadata:
        """Probe camera connectivity, capabilities, codec, and resolution."""
        if self.protocol == CameraProtocol.ICSEE_NETIP and self._netip_client:
            ok = self._netip_client.connect()
            with self._lock:
                if ok:
                    info = self._netip_client.get_system_info()
                    self._metadata.is_online = True
                    self._metadata.last_seen = time.time()
                    self._metadata.extra_attributes["system_info"] = info
                    self._netip_client.enable_onvif_rtsp(rtsp_port=554)
                    rtsp_auth = f"{self.username}:{self.password}@" if self.password or self.username else ""
                    self._metadata.resolved_stream_url = f"rtsp://{rtsp_auth}{self.host}:554/stream0"
                else:
                    self._metadata.is_online = False
                    self._metadata.last_error = "NetIP authentication or connection failed"

        elif self.protocol == CameraProtocol.SOFIA_P2P and self._p2p_client:
            ok = self._p2p_client.resolve_and_punch()
            with self._lock:
                self._metadata.is_online = ok
                if ok and self._p2p_client.peer_endpoint:
                    peer_ip, peer_port = self._p2p_client.peer_endpoint
                    self._metadata.ip = peer_ip
                    self._metadata.port = peer_port
                    self._metadata.resolved_stream_url = f"rtsp://{self.username}:{self.password}@{peer_ip}:{peer_port}/stream0"
                else:
                    self._metadata.last_error = "P2P rendezvous punch failed"

        else:  # RTSP / ONVIF / HTTP
            rtsp_url = self.get_rtsp_url()
            stream_res = validar_stream(rtsp_url, timeout=2)
            with self._lock:
                if stream_res and stream_res.funciona:
                    self._metadata.is_online = True
                    self._metadata.codec = stream_res.codec or "h264"
                    self._metadata.resolution = stream_res.resolucao or "1920x1080"
                    self._metadata.resolved_stream_url = rtsp_url
                    self._metadata.last_seen = time.time()
                else:
                    self._metadata.is_online = False
                    self._metadata.last_error = "RTSP stream probe timeout"

        with self._lock:
            return self._metadata

    def get_rtsp_url(self) -> str:
        """Build canonical RTSP URL with credentials."""
        if self._metadata.resolved_stream_url:
            return self._metadata.resolved_stream_url

        auth = ""
        if self.username or self.password:
            auth = f"{self.username}:{self.password}@"
        port_part = f":{self.port}" if self.port and self.port != 554 else ""
        path_part = self.path if self.path.startswith("/") else f"/{self.path}"
        if not path_part or path_part == "/":
            path_part = "/stream0"
        return f"rtsp://{auth}{self.host}{port_part}{path_part}"

    def capture_snapshot(self, timeout: float = 1.5) -> Optional[bytes]:
        """Obtain a real-time JPEG snapshot from camera."""
        # 1. If NetIP is supported, query directly over NetIP socket (fastest, <100ms)
        if self._netip_client and self.protocol == CameraProtocol.ICSEE_NETIP:
            snap = self._netip_client.capture_snapshot(channel=0)
            if snap:
                return snap

        # 2. Fallback: extract single frame using ffmpeg from RTSP stream
        rtsp_url = self.get_rtsp_url()
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            "tcp",
            "-stimeout",
            str(int(timeout * 1_000_000)),
            "-i",
            rtsp_url,
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "mjpeg",
            "pipe:1",
        ]
        try:
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout + 0.5)
            if proc.returncode == 0 and len(proc.stdout) > 500:
                return proc.stdout
        except Exception as exc:
            _log.debug("FFmpeg snapshot failed for %s: %s", self.camera_id, exc)

        return None

    def ptz_move(self, command: PTZCommand | str, step: int = 4, stop_after_delay: float = 0.5) -> bool:
        """Send PTZ command to camera."""
        with self._lock:
            if self._netip_client and self.protocol == CameraProtocol.ICSEE_NETIP:
                return self._netip_client.ptz_control(command, step=step, stop_after_delay=stop_after_delay)
            # Future ONVIF PTZ SOAP dispatch can be routed here
            return False

    def ptz_stop(self) -> bool:
        """Stop active PTZ motion."""
        with self._lock:
            if self._netip_client and self.protocol == CameraProtocol.ICSEE_NETIP:
                return self._netip_client.ptz_stop()
            return False

    def close(self) -> None:
        """Close underlying connections and sockets."""
        with self._lock:
            if self._netip_client:
                self._netip_client.close()
                self._netip_client = None


class CameraFleetManager:
    """Manages active camera sources, automatic discovery, and health polling."""

    def __init__(self) -> None:
        self._cameras: Dict[str, UnifiedCameraSource] = {}
        self._lock = threading.RLock()

    def register_camera(
        self,
        url: str,
        camera_id: Optional[str] = None,
        name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> UnifiedCameraSource:
        """Add or update a camera source."""
        with self._lock:
            source = UnifiedCameraSource(
                url=url,
                camera_id=camera_id,
                name=name,
                username=username,
                password=password,
            )
            self._cameras[source.camera_id] = source
            return source

    def get_camera(self, camera_id: str) -> Optional[UnifiedCameraSource]:
        with self._lock:
            return self._cameras.get(camera_id)

    def list_cameras(self) -> List[CameraMetadata]:
        with self._lock:
            return [cam.metadata for cam in self._cameras.values()]

    def discover_local_cameras(self, timeout: float = 2.0) -> List[DiscoveredCamera]:
        """Perform NetIP & ONVIF local subnet discovery."""
        return XiongmaiDiscovery.discover(timeout=timeout)

    def close_all(self) -> None:
        with self._lock:
            for cam in self._cameras.values():
                cam.close()
            self._cameras.clear()
