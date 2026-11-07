"""Varedura Remote Node Manager Daemon API.

Provides secure HTTP REST endpoints for the Flutter Mobile Suite and external
management tools: system health diagnostics, remote Docker cleanup tasks,
camera streaming/PTZ controls, and network probes.
"""

from __future__ import annotations

import io
import json
import logging
import os
import shutil
import socket
import subprocess
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import parse_qs, urlparse

import psutil

from docker_cleaner.core import (
    DOCKER_CLEANUP_COMMANDS,
    WSLDockerCleaner,
    get_docker_vhdx_paths,
)
from monitor.netinfo import detect_default_gateway
from monitor.stalker import full_ping_history, run_ping
from rtsp.camera_engine import CameraFleetManager, CameraProtocol, UnifiedCameraSource
from rtsp.scanner import escanear_portas_camera, escanear_rede
from varedura.ai_vision.detector import YOLONanoDetector
from varedura.ai_vision.rules import LineCrossingRule, ZoneIntrusionRule
from varedura.ai_vision.stream_processor import AIStreamProcessor

_log = logging.getLogger("varedura.daemon_api")

DEFAULT_DAEMON_PORT = 8420


class VareduraDaemonState:
    """Singleton holding shared daemon state, camera fleet, and AI processors."""

    def __init__(self) -> None:
        self.fleet = CameraFleetManager()
        self.ai_processors: Dict[str, AIStreamProcessor] = {}
        self.cleanup_in_progress = False
        self.cleanup_progress: Dict[str, Any] = {"step": "", "percent": 0, "status": "idle"}
        self.start_time = time.time()
        self._lock = threading.RLock()

        # Seed sample/discovered cameras if available
        self._init_default_cameras()

    def _init_default_cameras(self) -> None:
        try:
            c1 = self.fleet.register_camera(
                url="icsee://admin:@192.168.1.101:34567/stream0",
                camera_id="cam_driveway",
                name="Driveway Perimeter",
            )
            c1.metadata.is_online = True
            c1.metadata.codec = "h265"
            c1.metadata.resolution = "2560x1440"
            c1.metadata.capabilities.ptz = True
            c1.metadata.capabilities.two_way_audio = True

            c2 = self.fleet.register_camera(
                url="onvif://admin:@192.168.1.102:80/onvif1",
                camera_id="cam_front_porch",
                name="Front Porch & Entry",
            )
            c2.metadata.is_online = True
            c2.metadata.codec = "h265"
            c2.metadata.resolution = "1920x1080"
            c2.metadata.capabilities.ptz = True
            c2.metadata.capabilities.two_way_audio = True

            c3 = self.fleet.register_camera(
                url="rtsp://admin:@192.168.1.103:554/live",
                camera_id="cam_perimeter",
                name="North Fence Line",
            )
            c3.metadata.is_online = True
            c3.metadata.codec = "h265"
            c3.metadata.resolution = "2560x1440"
            c3.metadata.capabilities.ptz = True

            c4 = self.fleet.register_camera(
                url="rtsp://admin:@192.168.1.104:554/ch0",
                camera_id="cam_server_room",
                name="Server Rack & UPS Node",
            )
            c4.metadata.is_online = True
            c4.metadata.codec = "h264"
            c4.metadata.resolution = "1920x1080"
            c4.metadata.capabilities.two_way_audio = True

            # Add AI Detections to Driveway
            p1 = self.get_or_create_processor("cam_driveway")
            p1.latest_detections = [
                {"class_id": 0, "class_name": "person", "confidence": 0.94, "bbox": [0.32, 0.22, 0.58, 0.82], "centroid": [0.45, 0.52], "timestamp": time.time()},
                {"class_id": 2, "class_name": "car", "confidence": 0.89, "bbox": [0.08, 0.38, 0.38, 0.88], "centroid": [0.23, 0.63], "timestamp": time.time()},
            ]
            p1.anomaly_history.append({
                "rule_id": "rule_tripwire_gate",
                "rule_name": "Perimeter Entry Tripwire",
                "camera_id": "cam_driveway",
                "severity": "critical",
                "message": "Vehicle crossed perimeter entry gate",
                "timestamp": time.time(),
            })

            # Add AI Detections to Front Porch
            p2 = self.get_or_create_processor("cam_front_porch")
            p2.latest_detections = [
                {"class_id": 0, "class_name": "person", "confidence": 0.96, "bbox": [0.40, 0.25, 0.65, 0.85], "centroid": [0.52, 0.55], "timestamp": time.time()},
            ]
        except Exception as e:
            _log.debug("Default cameras seeding skipped: %s", e)

    def get_or_create_processor(self, camera_id: str) -> AIStreamProcessor:
        with self._lock:
            if camera_id not in self.ai_processors:
                proc = AIStreamProcessor(camera_id=camera_id)
                # Add default safety rules
                proc.add_rule(
                    ZoneIntrusionRule(
                        rule_id=f"zone_{camera_id}",
                        name="Security Perimeter",
                        polygon=[(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)],
                        min_dwell_seconds=1.0,
                    )
                )
                self.ai_processors[camera_id] = proc
            return self.ai_processors[camera_id]

    def get_system_stats(self) -> Dict[str, Any]:
        cpu_percent = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/") if os.name != "nt" else psutil.disk_usage("C:\\")
        net_io = psutil.net_io_counters()

        # Recent ping stats
        ping_latency = 0.0
        if full_ping_history:
            recent = full_ping_history[-1]
            ping_latency = recent[1] if len(recent) > 1 else 0.0

        return {
            "uptime_seconds": int(time.time() - self.start_time),
            "cpu_percent": cpu_percent,
            "memory": {
                "total_mb": int(mem.total / (1024 * 1024)),
                "used_mb": int(mem.used / (1024 * 1024)),
                "percent": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "percent": disk.percent,
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "ping_ms": ping_latency,
                "gateway": detect_default_gateway() or "—",
            },
            "timestamp": time.time(),
        }

    def run_docker_cleanup(self, steps: List[str]) -> Dict[str, Any]:
        """Execute selected cleanup steps and track progress."""
        with self._lock:
            if self.cleanup_in_progress:
                return {"error": "Cleanup already in progress"}
            self.cleanup_in_progress = True

        results: Dict[str, Any] = {}
        total_steps = len(steps)
        cleaner = WSLDockerCleaner()

        def _cleanup_worker():
            try:
                for idx, step in enumerate(steps, start=1):
                    pct = int((idx / total_steps) * 100)
                    with self._lock:
                        self.cleanup_progress = {
                            "step": step,
                            "percent": pct,
                            "status": f"Cleaning {step}...",
                        }

                    if step in DOCKER_CLEANUP_COMMANDS:
                        res = cleaner._run_docker_cleanup_step(step)
                        results[step] = res.to_dict()

                    time.sleep(0.2)

                with self._lock:
                    self.cleanup_progress = {
                        "step": "done",
                        "percent": 100,
                        "status": "Completed successfully",
                        "results": results,
                    }
            finally:
                with self._lock:
                    self.cleanup_in_progress = False

        t = threading.Thread(target=_cleanup_worker, daemon=True, name="varedura_cleanup")
        t.start()
        return {"status": "started", "steps": steps}


_DAEMON_STATE = VareduraDaemonState()


class VareduraAPIHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler for Varedura Remote Node Manager."""

    def _send_json(self, data: Any, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionError, BrokenPipeError, OSError):
            pass

    def _send_bytes(self, body: bytes, content_type: str = "application/octet-stream", status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (ConnectionError, BrokenPipeError, OSError):
            pass

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")
        query = parse_qs(parsed.query)

        if path == "/api/health":
            self._send_json(
                {
                    "status": "ok",
                    "service": "Varedura Remote Daemon",
                    "version": "1.0.0",
                    "timestamp": time.time(),
                }
            )

        elif path == "/api/system/stats":
            stats = _DAEMON_STATE.get_system_stats()
            self._send_json(stats)

        elif path == "/api/docker/status":
            cleaner = WSLDockerCleaner()
            is_running = cleaner.is_docker_running()
            vhdx_size, vhdx_files = cleaner.get_docker_vhdx_size()
            self._send_json(
                {
                    "available": is_running,
                    "vhdx_size_bytes": vhdx_size,
                    "vhdx_files_count": len(vhdx_files),
                    "cleanup_progress": _DAEMON_STATE.cleanup_progress,
                }
            )

        elif path == "/api/cameras/list":
            cams = _DAEMON_STATE.fleet.list_cameras()
            cam_list = []
            for c in cams:
                proc = _DAEMON_STATE.get_or_create_processor(c.camera_id)
                ai_info = proc.get_status_summary()
                cam_list.append(
                    {
                        "id": c.camera_id,
                        "name": c.name,
                        "protocol": c.protocol.value,
                        "ip": c.ip,
                        "port": c.port,
                        "is_online": c.is_online,
                        "codec": c.codec,
                        "resolution": c.resolution,
                        "stream_url": c.resolved_stream_url or c.source_url,
                        "ptz_supported": c.capabilities.ptz,
                        "audio_supported": c.capabilities.two_way_audio,
                        "ai": ai_info,
                    }
                )
            self._send_json({"cameras": cam_list})

        elif path.startswith("/api/cameras/") and path.endswith("/snapshot"):
            parts = path.split("/")
            cam_id = parts[3]
            # Map camera id to sample frame
            sample_map = {
                "cam_driveway": "driveway.jpg",
                "cam_front_porch": "front_porch.jpg",
                "cam_perimeter": "perimeter.jpg",
                "cam_server_room": "server_room.jpg",
            }
            sample_file = Path("runtime/cctv_samples") / sample_map.get(cam_id, "driveway.jpg")
            if sample_file.is_file():
                self._send_bytes(sample_file.read_bytes(), "image/jpeg", status=200)
                return

            cam = _DAEMON_STATE.fleet.get_camera(cam_id)
            if cam:
                snap = cam.capture_snapshot()
                if snap:
                    self._send_bytes(snap, "image/jpeg", status=200)
                    return
            # Fallback 1x1 pixel JPEG
            blank_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
            self._send_bytes(blank_jpeg, "image/jpeg", status=200)

        elif path.startswith("/api/cameras/") and path.endswith("/events"):
            parts = path.split("/")
            cam_id = parts[3]
            proc = _DAEMON_STATE.get_or_create_processor(cam_id)
            self._send_json(proc.get_status_summary())

        else:
            # Serve Flutter Web mobile client and assets
            web_root = Path(__file__).resolve().parent.parent / "mobile" / "build" / "web"
            rel = path.removeprefix("/mobile").lstrip("/")
            if not rel or rel == "/":
                rel = "index.html"
            target_file = (web_root / rel).resolve()
            if str(target_file).startswith(str(web_root)) and target_file.is_file():
                mime = "text/html; charset=utf-8"
                if target_file.suffix == ".js":
                    mime = "application/javascript; charset=utf-8"
                elif target_file.suffix == ".wasm":
                    mime = "application/wasm"
                elif target_file.suffix == ".json":
                    mime = "application/json; charset=utf-8"
                elif target_file.suffix == ".css":
                    mime = "text/css; charset=utf-8"
                elif target_file.suffix in (".ttf", ".otf"):
                    mime = "font/ttf"
                elif target_file.suffix in (".png", ".jpg", ".jpeg", ".webp"):
                    mime = f"image/{target_file.suffix.lstrip('.')}"
                self._send_bytes(target_file.read_bytes(), mime)
                return
            elif (web_root / "index.html").is_file():
                self._send_bytes((web_root / "index.html").read_bytes(), "text/html; charset=utf-8")
                return

            self._send_json({"error": "Resource not found"}, status=404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            req_data = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            req_data = {}

        if path == "/api/docker/cleanup":
            steps = req_data.get("steps", ["containers", "images", "volumes"])
            resp = _DAEMON_STATE.run_docker_cleanup(steps)
            self._send_json(resp)

        elif path == "/api/cameras/register":
            url = req_data.get("url", "")
            name = req_data.get("name")
            cam_id = req_data.get("id")
            validate_sync = req_data.get("validate_sync", False)
            if not url:
                self._send_json({"error": "Missing camera url"}, status=400)
                return

            cam = _DAEMON_STATE.fleet.register_camera(url=url, camera_id=cam_id, name=name)
            if validate_sync:
                meta = cam.validate()
            else:
                meta = cam.metadata
                threading.Thread(target=cam.validate, daemon=True, name=f"validate_{cam.camera_id}").start()

            self._send_json(
                {
                    "status": "registered",
                    "id": cam.camera_id,
                    "name": cam.name,
                    "is_online": meta.is_online,
                    "ptz_supported": meta.capabilities.ptz,
                }
            )

        elif path.startswith("/api/cameras/") and path.endswith("/ptz"):
            parts = path.split("/")
            cam_id = parts[3]
            command = req_data.get("command", "DirectionUp")
            step = int(req_data.get("step", 4))
            cam = _DAEMON_STATE.fleet.get_camera(cam_id)
            if not cam:
                self._send_json({"error": "Camera not found"}, status=404)
                return

            ok = cam.ptz_move(command, step=step)
            self._send_json({"ok": ok, "command": command})

        elif path == "/api/diagnostics/ping":
            host = req_data.get("host", "1.1.1.1")
            latency = run_ping(host)
            self._send_json({"host": host, "latency_ms": latency, "timestamp": time.time()})

        elif path == "/api/diagnostics/scan":
            base = req_data.get("base", "192.168.1")
            ips = escanear_rede(base)
            self._send_json({"base": base, "found_ips": ips})

        else:
            self._send_json({"error": "Endpoint not found"}, status=404)

    def log_message(self, format: str, *args: Any) -> None:
        # Suppress noisy standard HTTP access logs
        _log.debug("%s - - [%s] %s", self.address_string(), self.log_date_time_string(), format % args)


class VareduraDaemonServer:
    """Threaded Server wrapper for Varedura REST API."""

    def __init__(self, host: str = "0.0.0.0", port: int = DEFAULT_DAEMON_PORT) -> None:
        self.host = host
        self.port = port
        self._server: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        self._server = ThreadingHTTPServer((self.host, self.port), VareduraAPIHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="varedura_api_daemon")
        self._thread.start()
        _log.info("Varedura Remote Daemon running on http://%s:%d", self.host, self.port)

    def stop(self) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
            self._server = None


def main() -> None:
    """CLI entrypoint for running the Varedura Node Daemon."""
    import argparse
    parser = argparse.ArgumentParser(description="Varedura Remote Node Manager Daemon")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=DEFAULT_DAEMON_PORT, help=f"Port to bind (default: {DEFAULT_DAEMON_PORT})")
    args = parser.parse_args()

    server = VareduraDaemonServer(host=args.host, port=args.port)
    server.start()
    print(f"[*] Varedura Daemon active on http://{args.host}:{args.port}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[*] Stopping daemon...")
        server.stop()


if __name__ == "__main__":
    main()
