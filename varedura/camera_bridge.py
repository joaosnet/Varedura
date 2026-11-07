"""Ponte local e sanitizada entre as câmeras do Varedura e o Mural.

O processo é o único componente que conhece URLs RTSP e credenciais. O
diretório de saída contém apenas IDs opacos, estados enumerados e mídia
derivada. Comandos chegam por um inbox atômico e nunca aceitam URLs/caminhos
arbitrários.
"""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import logging
import math
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote, urlsplit, urlunsplit

import psutil

from rtsp import DATA_DIR
from rtsp.log import RedactingFilter, RedactingFormatter, redact_sensitive

SCHEMA_VERSION = 1
DEFAULT_SESSION_TTL = 45.0
DEFAULT_SNAPSHOT_INTERVAL = 30.0
DEFAULT_POLL_INTERVAL = 1.0
HEARTBEAT_INTERVAL = 5.0
MAX_COMMAND_BYTES = 64 * 1024
MAX_COMMAND_AGE = 90.0
MAX_COMMAND_FUTURE_SKEW = 15.0
OUTBOX_RETENTION = 60 * 60
MAX_OUTBOX_FILES = 512
ORPHAN_SNAPSHOT_RETENTION = 24 * 60 * 60
HLS_START_TIMEOUT = 15.0
HLS_STALL_TIMEOUT = 15.0

_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_IP_IN_TEXT_RE = re.compile(
    r"(?<![0-9])(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)"
    r"(?:\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)){3}(?![0-9])"
)
_IDENTITY_SECRET_RE = re.compile(
    r"(?i)\b(user|username|password|passwd|pwd|senha|token)=([^&/?]*)"
)
_ALLOWED_ACTIONS = {
    "refresh",
    "start",
    "heartbeat",
    "stop",
    "shutdown",
    "set_location",
    "clear_location",
}
_COMMAND_KEYS = {
    "schemaVersion",
    "commandId",
    "action",
    "cameraId",
    "sessionId",
    "requestedAt",
    "location",
}
_LOCATION_KEYS = {
    "latitude",
    "longitude",
    "accuracyMeters",
    "source",
    "updatedAt",
}
_LOCATION_SOURCES = {"manual", "device"}
_LOCATION_SCHEMA_VERSION = 1

_log = logging.getLogger("varedura.camera_bridge")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _iso_now() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _parse_iso(value: object) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed


def _valid_uuid(value: object) -> bool:
    if not isinstance(value, str) or not _UUID_RE.fullmatch(value):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def _replace_with_retry(src: Path, dst: Path, max_attempts: int = 5) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            os.replace(src, dst)
            return
        except (PermissionError, OSError):
            if attempt == max_attempts:
                raise
            time.sleep(0.05 * attempt)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    """Grava JSON no mesmo volume e publica com ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_tmp = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    tmp = Path(raw_tmp)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        _replace_with_retry(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _is_link_like(path: Path) -> bool:
    try:
        return path.is_symlink() or path.is_junction()
    except (AttributeError, OSError):
        return path.is_symlink()


def _require_safe_child(root: Path, candidate: Path) -> Path:
    """Rejeita symlink/junction e qualquer resolução fora de ``root``."""
    if _is_link_like(candidate):
        raise OSError("runtime child is a link")
    resolved_root = root.resolve()
    resolved_candidate = candidate.resolve()
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise OSError("runtime child escapes output directory") from exc
    return candidate


def _resolution_parts(value: object) -> tuple[int | None, int | None]:
    if not isinstance(value, str):
        return (None, None)
    match = re.fullmatch(r"\s*([1-9][0-9]*)x([1-9][0-9]*)\s*", value)
    if not match:
        return (None, None)
    return (int(match.group(1)), int(match.group(2)))


def _finite_real(value: object) -> float | None:
    """Normaliza números JSON reais e finitos, rejeitando bool e strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        normalized = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return normalized if math.isfinite(normalized) else None


def _canonical_rtsp_identity(url: str) -> tuple[str, str, int, str] | None:
    """Retorna identidade sem userinfo, ou ``None`` para URL inválida."""
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() != "rtsp" or not parsed.hostname:
            return None
        host = parsed.hostname.rstrip(".").casefold()
        port = parsed.port or 554
    except ValueError:
        return None
    resource = parsed.path or "/"
    if parsed.query:
        resource = f"{resource}?{parsed.query}"
    resource = _IDENTITY_SECRET_RE.sub(r"\1=<credential>", resource)
    return (parsed.scheme.lower(), host, port, resource)


def _rtsp_without_auth(host: str, port: int, resource: str) -> str:
    host_part = host
    try:
        if ipaddress.ip_address(host).version == 6:
            host_part = f"[{host}]"
    except ValueError:
        pass
    path, separator, query = (resource or "/").partition("?")
    return urlunsplit(
        ("rtsp", f"{host_part}:{port}", path or "/", query if separator else "", "")
    )


def _with_credentials(url: str, username: str, password: str) -> str:
    """Adiciona userinfo somente à cópia privada da URL."""
    if not username and not password:
        return url
    try:
        parsed = urlsplit(url)
        if parsed.username is not None or not parsed.hostname:
            return url
        port = parsed.port or 554
    except ValueError:
        return url
    host = parsed.hostname
    try:
        if ipaddress.ip_address(host).version == 6:
            host = f"[{host}]"
    except ValueError:
        pass
    userinfo = quote(username, safe="")
    if password:
        userinfo = f"{userinfo}:{quote(password, safe='')}"
    return urlunsplit(
        (
            parsed.scheme,
            f"{userinfo}@{host}:{port}",
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )


def _safe_display_name(
    proposed: object,
    *,
    forbidden: tuple[str, ...] = (),
) -> str | None:
    """Aceita rótulo humano, rejeitando endereços e material de conexão."""
    if not isinstance(proposed, str):
        return None
    name = " ".join(proposed.strip().split())
    if not name or len(name) > 80:
        return None
    folded = name.casefold()
    if "://" in folded or "@" in folded or _IP_IN_TEXT_RE.search(name):
        return None
    for value in forbidden:
        candidate = value.strip().casefold()
        if len(candidate) >= 3 and candidate in folded:
            return None
    return name


@dataclass(frozen=True)
class CameraLocation:
    """Coordenadas estritamente tipadas, sem endereço ou texto livre."""

    latitude: float
    longitude: float
    source: str
    accuracy_meters: float | None = None
    updated_at: str | None = None

    @classmethod
    def from_dict(cls, data: object) -> CameraLocation | None:
        if not isinstance(data, dict):
            return None
        keys = set(data)
        if keys - _LOCATION_KEYS or not {"latitude", "longitude", "source"} <= keys:
            return None

        latitude = _finite_real(data.get("latitude"))
        longitude = _finite_real(data.get("longitude"))
        if latitude is None or not -90.0 <= latitude <= 90.0:
            return None
        if longitude is None or not -180.0 <= longitude <= 180.0:
            return None

        source = data.get("source")
        if not isinstance(source, str) or source not in _LOCATION_SOURCES:
            return None

        accuracy_meters = None
        if "accuracyMeters" in data:
            accuracy_meters = _finite_real(data.get("accuracyMeters"))
            if accuracy_meters is None or accuracy_meters <= 0:
                return None

        updated_at = None
        if "updatedAt" in data:
            parsed_updated_at = _parse_iso(data.get("updatedAt"))
            if parsed_updated_at is None:
                return None
            updated_at = parsed_updated_at.astimezone(UTC).isoformat()

        return cls(
            latitude=latitude,
            longitude=longitude,
            source=source,
            accuracy_meters=accuracy_meters,
            updated_at=updated_at,
        )

    def public_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "source": self.source,
        }
        if self.accuracy_meters is not None:
            data["accuracyMeters"] = self.accuracy_meters
        if self.updated_at is not None:
            data["updatedAt"] = self.updated_at
        return data


class LocationStore:
    """Estado privado e atômico de localização, indexado pelo ID opaco."""

    def __init__(self, path: Path):
        self.path = path
        self.locations: dict[str, CameraLocation] = {}
        self._load()

    def _require_safe_path(self) -> None:
        _require_safe_child(self.path.parent, self.path)

    def _load(self) -> None:
        self._require_safe_path()
        raw = _read_json(self.path) or {}
        entries = raw.get("locations", {})
        if not isinstance(entries, dict):
            return
        loaded: dict[str, CameraLocation] = {}
        for camera_id, payload in entries.items():
            if not _valid_uuid(camera_id):
                continue
            location = CameraLocation.from_dict(payload)
            if location is not None:
                loaded[camera_id] = location
        self.locations = loaded

    def get(self, camera_id: str) -> CameraLocation | None:
        return self.locations.get(camera_id)

    def _persist(self, locations: dict[str, CameraLocation]) -> None:
        self._require_safe_path()
        _atomic_write_json(
            self.path,
            {
                "schemaVersion": _LOCATION_SCHEMA_VERSION,
                "locations": {
                    camera_id: location.public_dict()
                    for camera_id, location in sorted(locations.items())
                },
            },
        )
        if os.name != "nt":
            try:
                self.path.chmod(0o600)
            except OSError:
                pass

    def set(self, camera_id: str, location: CameraLocation) -> None:
        if not _valid_uuid(camera_id):
            raise ValueError("invalid camera id")
        updated = dict(self.locations)
        updated[camera_id] = location
        self._persist(updated)
        self.locations = updated

    def clear(self, camera_id: str) -> None:
        if not _valid_uuid(camera_id):
            raise ValueError("invalid camera id")
        if camera_id not in self.locations:
            return
        updated = dict(self.locations)
        del updated[camera_id]
        self._persist(updated)
        self.locations = updated


@dataclass
class CameraSource:
    """Fonte privada mais estado público de uma câmera conhecida."""

    id: str
    name: str
    url: str = field(repr=False)
    codec: str | None = None
    width: int | None = None
    height: int | None = None
    status: str = "unknown"
    status_reason: str = "awaiting_first_check"
    last_checked_at: str | None = None
    last_online_at: str | None = None
    snapshot_revision: str | None = None
    snapshot_updated_at: str | None = None
    location: CameraLocation | None = None

    def public_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "statusReason": self.status_reason,
            "lastCheckedAt": self.last_checked_at,
            "lastOnlineAt": self.last_online_at,
            "snapshotFile": f"snapshots/{self.id}.jpg",
        }
        if self.snapshot_revision:
            data.update(
                {
                    "snapshotRevision": self.snapshot_revision,
                    "snapshotUpdatedAt": self.snapshot_updated_at,
                }
            )
        if (
            isinstance(self.codec, str)
            and self.codec.strip()
            and isinstance(self.width, int)
            and self.width > 0
            and isinstance(self.height, int)
            and self.height > 0
        ):
            data["video"] = {
                "codec": self.codec,
                "width": self.width,
                "height": self.height,
            }
        if self.location is not None:
            data["location"] = self.location.public_dict()
        return data


class IdentityStore:
    """Mapa privado fingerprint→UUID, sem persistir host ou URL."""

    def __init__(self, path: Path):
        self.path = path
        raw = _read_json(path) or {}
        entries = raw.get("cameras", {})
        self.entries: dict[str, dict[str, str]] = (
            entries if isinstance(entries, dict) else {}
        )
        self._dirty = False

    def assign(
        self,
        identity: tuple[str, str, int, str],
        *,
        proposed_name: object = None,
        forbidden: tuple[str, ...] = (),
    ) -> tuple[str, str]:
        serialized = json.dumps(identity, ensure_ascii=False, separators=(",", ":"))
        fingerprint = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        entry = self.entries.get(fingerprint)
        if not isinstance(entry, dict) or not _valid_uuid(entry.get("id")):
            entry = {"id": str(uuid.uuid4()), "name": ""}
            self.entries[fingerprint] = entry
            self._dirty = True

        safe_proposed = _safe_display_name(proposed_name, forbidden=forbidden)
        stored_name = _safe_display_name(entry.get("name"), forbidden=forbidden)
        if safe_proposed:
            name = safe_proposed
        elif stored_name:
            name = stored_name
        else:
            used = {
                item.get("name")
                for item in self.entries.values()
                if isinstance(item, dict)
            }
            number = 1
            while f"Câmera {number:02d}" in used:
                number += 1
            name = f"Câmera {number:02d}"

        if entry.get("name") != name:
            entry["name"] = name
            self._dirty = True
        return (entry["id"], name)

    def save(self) -> None:
        if not self._dirty:
            return
        _atomic_write_json(
            self.path,
            {
                "schemaVersion": SCHEMA_VERSION,
                "cameras": self.entries,
            },
        )
        self._dirty = False


def load_private_inventory(
    state_path: Path,
    *,
    conhecidos: dict[str, Any] | None = None,
    regioes: list[Any] | None = None,
) -> list[CameraSource]:
    """Lê o inventário existente e atribui IDs opacos persistentes."""
    if conhecidos is None:
        from rtsp.credenciais import carregar_conhecidos

        conhecidos = carregar_conhecidos()
    if regioes is None:
        from rtsp.regioes import TIPO_CAMERA, carregar_regioes

        regioes = [
            region for region in carregar_regioes() if region.tipo == TIPO_CAMERA
        ]

    store = IdentityStore(state_path)
    region_list = list(regioes)
    sources: dict[tuple[str, str, int, str], CameraSource] = {}

    for map_host, credential in sorted(conhecidos.items()):
        raw_url = getattr(credential, "url", "") or ""
        identity = _canonical_rtsp_identity(raw_url)
        if identity is None:
            path = getattr(credential, "caminho", "") or "/"
            raw_url = _rtsp_without_auth(str(map_host), 554, path)
            raw_url = _with_credentials(
                raw_url,
                str(getattr(credential, "usuario", "") or ""),
                str(getattr(credential, "senha", "") or ""),
            )
            identity = _canonical_rtsp_identity(raw_url)
        elif urlsplit(raw_url).username is None:
            raw_url = _with_credentials(
                raw_url,
                str(getattr(credential, "usuario", "") or ""),
                str(getattr(credential, "senha", "") or ""),
            )
        if identity is None:
            continue

        _, host, port, resource = identity
        matching_region = next(
            (
                region
                for region in region_list
                if str(getattr(region, "endereco", "")).rstrip(".").casefold() == host
                and int(getattr(region, "porta", 554)) == port
                and (
                    not getattr(region, "caminho", "")
                    or (
                        _canonical_rtsp_identity(
                            _rtsp_without_auth(
                                host,
                                port,
                                str(getattr(region, "caminho", "")),
                            )
                        )
                        or ("", "", 0, "")
                    )[3]
                    == resource
                )
            ),
            None,
        )
        proposed = getattr(matching_region, "rotulo", None)
        username = str(getattr(credential, "usuario", "") or "")
        password = str(getattr(credential, "senha", "") or "")
        camera_id, name = store.assign(
            identity,
            proposed_name=proposed,
            forbidden=(host, username, password),
        )
        width, height = _resolution_parts(getattr(credential, "resolucao", None))
        sources[identity] = CameraSource(
            id=camera_id,
            name=name,
            url=raw_url,
            codec=getattr(credential, "codec", None),
            width=width,
            height=height,
        )

    for region in region_list:
        host = str(getattr(region, "endereco", "")).strip()
        if not host:
            continue
        port = int(getattr(region, "porta", 554))
        resource = str(getattr(region, "caminho", "") or "/")
        raw_url = _rtsp_without_auth(host, port, resource)
        identity = _canonical_rtsp_identity(raw_url)
        if identity is None or identity in sources:
            continue
        camera_id, name = store.assign(
            identity,
            proposed_name=getattr(region, "rotulo", None),
            forbidden=(host,),
        )
        sources[identity] = CameraSource(id=camera_id, name=name, url=raw_url)

    store.save()
    return sorted(
        sources.values(), key=lambda camera: (camera.name.casefold(), camera.id)
    )


@dataclass(frozen=True)
class CaptureResult:
    success: bool
    status: str
    reason: str
    revision: str | None = None
    updated_at: str | None = None


class HlsProcess(Protocol):
    pid: int

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float | None = None) -> int: ...


class FFmpegRunner:
    """Único ponto que entrega URLs privadas ao FFmpeg."""

    def __init__(self, executable: str | None = None, timeout: float = 10.0):
        self.executable = (
            executable if executable is not None else shutil.which("ffmpeg")
        )
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.executable)

    def capture_snapshot(
        self, camera: CameraSource, destination: Path
    ) -> CaptureResult:
        if not self.executable:
            return CaptureResult(False, "error", "ffmpeg_unavailable")
        destination.parent.mkdir(parents=True, exist_ok=True)
        tmp = destination.with_name(f".{destination.stem}.{uuid.uuid4().hex}.tmp.jpg")
        command = [
            self.executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-rtsp_transport",
            "tcp",
            "-i",
            camera.url,
            "-frames:v",
            "1",
            "-q:v",
            "3",
            str(tmp),
        ]
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=self.timeout + 5,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
                return self._capture_failure(result.stderr or "")
            with tmp.open("rb") as stream:
                content = stream.read()
            revision = hashlib.sha256(content).hexdigest()[:16]
            _replace_with_retry(tmp, destination)
            return CaptureResult(
                True,
                "online",
                "video_ok",
                revision=revision,
                updated_at=_iso_now(),
            )
        except subprocess.TimeoutExpired:
            return CaptureResult(False, "offline", "connection_timeout")
        except OSError:
            return CaptureResult(False, "error", "ffmpeg_execution_failed")
        finally:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass

    @staticmethod
    def _capture_failure(stderr: str) -> CaptureResult:
        lowered = stderr.casefold()
        if any(token in lowered for token in ("401", "unauthorized", "authentication")):
            return CaptureResult(False, "auth_required", "authentication_required")
        if any(
            token in lowered
            for token in (
                "connection refused",
                "connection timed out",
                "no route to host",
                "could not connect",
            )
        ):
            return CaptureResult(False, "offline", "connection_failed")
        if any(token in lowered for token in ("stream", "video", "codec")):
            return CaptureResult(False, "reachable_no_video", "no_video")
        return CaptureResult(False, "error", "snapshot_failed")

    def start_hls(self, camera: CameraSource, session_dir: Path) -> HlsProcess | None:
        if not self.executable:
            return None
        command = [
            self.executable,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-rtsp_transport",
            "tcp",
            "-i",
            camera.url,
            "-map",
            "0:v:0",
            "-an",
        ]
        if (camera.codec or "").casefold() == "h264":
            command.extend(["-c:v", "copy"])
        else:
            command.extend(
                [
                    "-vf",
                    "scale=1280:-2:force_original_aspect_ratio=decrease,fps=15",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-tune",
                    "zerolatency",
                    "-pix_fmt",
                    "yuv420p",
                    "-g",
                    "15",
                    "-sc_threshold",
                    "0",
                ]
            )
        command.extend(
            [
                "-f",
                "hls",
                "-hls_time",
                "1",
                "-hls_list_size",
                "4",
                "-hls_flags",
                "delete_segments+append_list+omit_endlist+independent_segments",
                "-hls_segment_filename",
                "%06d.ts",
                "index.m3u8",
            ]
        )
        try:
            return subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=session_dir,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except OSError:
            return None


class BridgeAlreadyRunning(RuntimeError):
    """Outro processo válido já possui o diretório de saída."""


@dataclass
class ActiveSession:
    session_id: str
    camera_id: str
    process: HlsProcess
    created_at: str
    last_heartbeat: float
    status: str = "starting"
    last_media_mtime_ns: int = 0
    last_media_progress: float = field(default_factory=time.monotonic)


class CameraBridge:
    """Loop de coordenação do catálogo, comandos, snapshots e HLS."""

    def __init__(
        self,
        output_dir: Path,
        *,
        state_path: Path | None = None,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        snapshot_interval: float = DEFAULT_SNAPSHOT_INTERVAL,
        session_ttl: float = DEFAULT_SESSION_TTL,
        ffmpeg_runner: FFmpegRunner | None = None,
        inventory_loader: Any | None = None,
    ):
        self.output_dir = output_dir.expanduser().resolve()
        self.state_path = (
            state_path.expanduser().resolve()
            if state_path
            else DATA_DIR / "camera_bridge_state.json"
        )
        self.poll_interval = poll_interval
        self.snapshot_interval = snapshot_interval
        self.session_ttl = session_ttl
        self.runner = ffmpeg_runner or FFmpegRunner()
        self.inventory_loader = inventory_loader or (
            lambda: load_private_inventory(self.state_path)
        )
        self.instance_id = str(uuid.uuid4())
        self.started_at = _iso_now()
        try:
            self.process_created_at = psutil.Process(os.getpid()).create_time()
        except (psutil.Error, OSError):
            self.process_created_at = time.time()

        self.snapshots_dir = self.output_dir / "snapshots"
        self.sessions_dir = self.output_dir / "sessions"
        self.commands_dir = self.output_dir / "commands"
        self.inbox_dir = self.commands_dir / "inbox"
        self.processing_dir = self.commands_dir / "processing"
        self.outbox_dir = self.commands_dir / "outbox"
        self.lock_path = self.output_dir / ".bridge.lock"
        self.pid_path = self.output_dir / "bridge.pid"
        self.heartbeat_path = self.output_dir / "heartbeat.json"
        self.catalog_path = self.output_dir / "catalog.json"
        self.locations_path = self.output_dir / ".camera-locations.private.json"
        self.location_store = LocationStore(self.locations_path)

        self.cameras: dict[str, CameraSource] = {}
        self.active_session: ActiveSession | None = None
        self._stop_event = threading.Event()
        self._lock_owned = False
        self._catalog_revision = self._existing_revision()
        self._last_catalog_write = 0.0
        self._last_inventory_load = 0.0
        self._last_snapshot_attempt: dict[str, float] = {}
        self._snapshot_futures: dict[Future[CaptureResult], str] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=2,
            thread_name_prefix="varedura-snapshot",
        )

    def _existing_revision(self) -> int:
        data = _read_json(self.catalog_path)
        revision = data.get("revision", 0) if data else 0
        return revision if isinstance(revision, int) and revision >= 0 else 0

    def _ensure_directories(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        _require_safe_child(self.output_dir, self.locations_path)
        for path in (self.snapshots_dir, self.sessions_dir, self.commands_dir):
            _require_safe_child(self.output_dir, path)
            path.mkdir(exist_ok=True)
            if not path.is_dir():
                raise OSError("runtime child is not a directory")
        for path in (self.inbox_dir, self.processing_dir, self.outbox_dir):
            _require_safe_child(self.output_dir, path)
            path.mkdir(exist_ok=True)
            if not path.is_dir():
                raise OSError("runtime child is not a directory")

    def _process_record(self) -> dict[str, Any]:
        return {
            "schemaVersion": SCHEMA_VERSION,
            "pid": os.getpid(),
            "instanceId": self.instance_id,
            "startedAt": self.started_at,
            "processCreatedAt": self.process_created_at,
            "outputDir": str(self.output_dir),
            "command": "varedura-camera-bridge",
        }

    @staticmethod
    def _record_is_live(record: dict[str, Any], output_dir: Path) -> bool:
        pid = record.get("pid")
        created = record.get("processCreatedAt")
        if not isinstance(pid, int) or not isinstance(created, (int, float)):
            return False
        try:
            process = psutil.Process(pid)
            if not process.is_running() or abs(process.create_time() - created) > 2:
                return False
            command = " ".join(process.cmdline()).casefold()
        except (psutil.Error, OSError):
            return False
        try:
            recorded_output = Path(str(record.get("outputDir", ""))).resolve()
        except (OSError, ValueError):
            return False
        bridge_marker = (
            "varedura-camera-bridge" in command or "camera_bridge" in command
        )
        return bridge_marker and recorded_output == output_dir

    def acquire_lock(self) -> None:
        self._ensure_directories()
        record = self._process_record()
        payload = (json.dumps(record, ensure_ascii=False) + "\n").encode("utf-8")
        for _attempt in range(3):
            try:
                fd = os.open(
                    self.lock_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                existing = _read_json(self.lock_path) or {}
                if self._record_is_live(existing, self.output_dir):
                    raise BridgeAlreadyRunning(
                        "uma ponte já está ativa para este diretório"
                    )
                try:
                    lock_age = time.time() - self.lock_path.stat().st_mtime
                except OSError:
                    continue
                if not existing and lock_age < 5:
                    raise BridgeAlreadyRunning(
                        "outra ponte está inicializando para este diretório"
                    )
                try:
                    self.lock_path.unlink()
                except FileNotFoundError:
                    pass
                continue
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            self._lock_owned = True
            try:
                _atomic_write_json(self.pid_path, record)
                self._recover_processing_commands()
                self._recover_orphan_sessions()
            except Exception:
                self.release_lock()
                raise
            return
        raise BridgeAlreadyRunning("não foi possível adquirir o lock da ponte")

    def release_lock(self) -> None:
        if not self._lock_owned:
            return
        for path in (self.pid_path, self.lock_path):
            current = _read_json(path)
            if not current or current.get("instanceId") != self.instance_id:
                continue
            try:
                path.unlink()
            except FileNotFoundError:
                pass
        self._lock_owned = False

    def _recover_processing_commands(self) -> None:
        for path in self.processing_dir.glob("*.json"):
            command_id = path.stem
            if _valid_uuid(command_id) and (self.outbox_dir / path.name).exists():
                path.unlink(missing_ok=True)
                continue
            try:
                os.replace(path, self.inbox_dir / path.name)
            except OSError:
                path.unlink(missing_ok=True)

    def refresh_inventory(self) -> None:
        try:
            loaded = self.inventory_loader()
        except Exception:
            _log.exception("Falha ao atualizar inventário privado")
            return
        previous = self.cameras
        current: dict[str, CameraSource] = {}
        for camera in loaded:
            if not isinstance(camera, CameraSource) or not _valid_uuid(camera.id):
                continue
            camera.location = self.location_store.get(camera.id)
            old = previous.get(camera.id)
            if old:
                camera.status = old.status
                camera.status_reason = old.status_reason
                camera.last_checked_at = old.last_checked_at
                camera.last_online_at = old.last_online_at
                camera.snapshot_revision = old.snapshot_revision
                camera.snapshot_updated_at = old.snapshot_updated_at
            current[camera.id] = camera
        self.cameras = current
        self._cleanup_orphan_snapshots()
        self._last_inventory_load = time.monotonic()

    def _cleanup_orphan_snapshots(self) -> None:
        now = time.time()
        known_ids = set(self.cameras)
        for path in self.snapshots_dir.glob("*.jpg"):
            if path.stem in known_ids or not _valid_uuid(path.stem):
                continue
            try:
                if path.is_symlink():
                    path.unlink(missing_ok=True)
                elif (
                    path.is_file()
                    and now - path.stat().st_mtime > ORPHAN_SNAPSHOT_RETENTION
                ):
                    path.unlink(missing_ok=True)
            except OSError:
                continue

    def _catalog(self, bridge_status: str | None = None) -> dict[str, Any]:
        status = bridge_status or ("ready" if self.runner.available else "degraded")
        feeds = [
            camera.public_dict()
            for camera in sorted(
                self.cameras.values(),
                key=lambda item: (item.name.casefold(), item.id),
            )
        ]
        return {
            "schemaVersion": SCHEMA_VERSION,
            "revision": self._catalog_revision,
            "generatedAt": _iso_now(),
            "bridge": {
                "status": status,
                "instanceId": self.instance_id,
                "pid": os.getpid(),
                "startedAt": self.started_at,
                "lastHeartbeatAt": _iso_now(),
            },
            "capabilities": {
                "snapshots": True,
                "live": "hls",
                "maxLiveSessions": 1,
                "audio": False,
            },
            "feeds": feeds,
        }

    def write_catalog(self, bridge_status: str | None = None) -> None:
        self._catalog_revision += 1
        catalog = self._catalog(bridge_status)
        _atomic_write_json(self.catalog_path, catalog)
        heartbeat = {
            "schemaVersion": SCHEMA_VERSION,
            "instanceId": self.instance_id,
            "pid": os.getpid(),
            "lastHeartbeatAt": catalog["bridge"]["lastHeartbeatAt"],
            "status": catalog["bridge"]["status"],
        }
        _atomic_write_json(self.heartbeat_path, heartbeat)
        self._last_catalog_write = time.monotonic()

    def _apply_capture(self, camera: CameraSource, result: CaptureResult) -> None:
        previous_state = (camera.status, camera.status_reason)
        camera.status = result.status
        camera.status_reason = result.reason
        camera.last_checked_at = _iso_now()
        if result.success:
            camera.last_online_at = result.updated_at or camera.last_checked_at
            camera.snapshot_revision = result.revision
            camera.snapshot_updated_at = result.updated_at
        current_state = (camera.status, camera.status_reason)
        if current_state != previous_state:
            _log.info(
                "Estado da câmera alterado: name=%s id=%s status=%s reason=%s",
                camera.name,
                camera.id,
                camera.status,
                camera.status_reason,
            )

    def capture_now(self, camera_id: str) -> CaptureResult:
        camera = self.cameras[camera_id]
        result = self.runner.capture_snapshot(
            camera,
            self.snapshots_dir / f"{camera.id}.jpg",
        )
        self._apply_capture(camera, result)
        self._last_snapshot_attempt[camera_id] = time.monotonic()
        return result

    def _schedule_snapshots(self) -> None:
        pending = set(self._snapshot_futures.values())
        now = time.monotonic()
        for camera in self.cameras.values():
            last = self._last_snapshot_attempt.get(camera.id, 0.0)
            if camera.id in pending or now - last < self.snapshot_interval:
                continue
            destination = self.snapshots_dir / f"{camera.id}.jpg"
            future = self._executor.submit(
                self.runner.capture_snapshot,
                camera,
                destination,
            )
            self._snapshot_futures[future] = camera.id
            self._last_snapshot_attempt[camera.id] = now

    def _harvest_snapshots(self) -> None:
        for future, camera_id in list(self._snapshot_futures.items()):
            if not future.done():
                continue
            del self._snapshot_futures[future]
            camera = self.cameras.get(camera_id)
            if camera is None:
                continue
            try:
                result = future.result()
            except Exception:
                result = CaptureResult(False, "error", "snapshot_failed")
            self._apply_capture(camera, result)

    def _session_path(self, session_id: str) -> Path:
        if not _valid_uuid(session_id):
            raise ValueError("sessionId inválido")
        return _require_safe_child(
            self.output_dir,
            self.sessions_dir / session_id,
        )

    def _write_session(
        self,
        session_id: str,
        camera_id: str,
        status: str,
        created_at: str,
        error_code: str | None = None,
    ) -> None:
        data: dict[str, Any] = {
            "schemaVersion": SCHEMA_VERSION,
            "sessionId": session_id,
            "cameraId": camera_id,
            "status": status,
            "createdAt": created_at,
            "updatedAt": _iso_now(),
        }
        if error_code:
            data["errorCode"] = error_code
        _atomic_write_json(self._session_path(session_id) / "session.json", data)

    def _read_session(self, session_id: str) -> dict[str, Any] | None:
        return _read_json(self._session_path(session_id) / "session.json")

    def _process_marker_path(self, session_id: str) -> Path:
        return self._session_path(session_id) / ".ffmpeg-process.json"

    def _write_process_marker(
        self,
        session_id: str,
        process: HlsProcess,
    ) -> None:
        try:
            process_created_at = psutil.Process(process.pid).create_time()
        except (psutil.Error, OSError):
            process_created_at = time.time()
        _atomic_write_json(
            self._process_marker_path(session_id),
            {
                "schemaVersion": SCHEMA_VERSION,
                "pid": process.pid,
                "processCreatedAt": process_created_at,
                "bridgeInstanceId": self.instance_id,
            },
        )

    def _remove_process_marker(self, session_id: str) -> None:
        try:
            self._process_marker_path(session_id).unlink(missing_ok=True)
        except OSError:
            _log.warning(
                "Falha ao remover marker FFmpeg da sessão %s",
                session_id,
            )

    @staticmethod
    def _matching_orphan_process(
        record: dict[str, Any],
        session_dir: Path,
    ) -> psutil.Process | None:
        pid = record.get("pid")
        created_at = record.get("processCreatedAt")
        if not isinstance(pid, int) or not isinstance(created_at, (int, float)):
            return None
        try:
            process = psutil.Process(pid)
            if abs(process.create_time() - created_at) > 2:
                return None
            executable = Path(process.exe()).name.casefold()
            command = [part.casefold() for part in process.cmdline()]
            working_dir = Path(process.cwd()).resolve()
        except (psutil.Error, OSError, ValueError):
            return None
        if "ffmpeg" not in executable or "index.m3u8" not in command:
            return None
        if working_dir != session_dir.resolve():
            return None
        return process

    @staticmethod
    def _terminate_process(process: Any) -> None:
        try:
            if process.poll() is not None:
                return
        except AttributeError:
            try:
                if not process.is_running():
                    return
            except (psutil.Error, OSError):
                return
        try:
            process.terminate()
            process.wait(timeout=3)
        except (subprocess.TimeoutExpired, psutil.TimeoutExpired):
            try:
                process.kill()
                process.wait(timeout=2)
            except (
                OSError,
                psutil.Error,
                subprocess.TimeoutExpired,
                psutil.TimeoutExpired,
            ):
                pass
        except (OSError, psutil.Error):
            pass

    def _recover_orphan_sessions(self) -> None:
        for session_dir in self.sessions_dir.iterdir():
            if (
                not session_dir.is_dir()
                or _is_link_like(session_dir)
                or not _valid_uuid(session_dir.name)
            ):
                continue
            state = _read_json(session_dir / "session.json")
            marker = _read_json(session_dir / ".ffmpeg-process.json") or {}
            process = self._matching_orphan_process(marker, session_dir)
            if process is not None:
                self._terminate_process(process)
            self._remove_process_marker(session_dir.name)
            self._cleanup_session_media(session_dir.name)
            if not state or state.get("status") not in {
                "starting",
                "ready",
                "stopping",
            }:
                continue
            camera_id = state.get("cameraId")
            created_at = state.get("createdAt")
            if not _valid_uuid(camera_id) or _parse_iso(created_at) is None:
                continue
            self._write_session(
                session_dir.name,
                camera_id,
                "stopped",
                created_at,
                error_code="stopped_by_request",
            )

    def _cleanup_session_media(self, session_id: str) -> None:
        session_dir = self._session_path(session_id)
        for pattern in ("*.ts", "*.m3u8", "*.tmp"):
            for path in session_dir.glob(pattern):
                if path.is_file() and not path.is_symlink():
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        _log.warning(
                            "Falha ao remover mídia HLS da sessão %s",
                            session_id,
                        )

    def _stop_active(self, reason: str) -> bool:
        active = self.active_session
        if active is None:
            return False
        self._write_session(
            active.session_id,
            active.camera_id,
            "stopping",
            active.created_at,
        )
        self._terminate_process(active.process)
        self._remove_process_marker(active.session_id)
        self._cleanup_session_media(active.session_id)
        self._write_session(
            active.session_id,
            active.camera_id,
            "stopped",
            active.created_at,
            error_code=reason,
        )
        self.active_session = None
        return True

    def _fail_active(self, error_code: str) -> None:
        active = self.active_session
        if active is None:
            return
        self._terminate_process(active.process)
        self._remove_process_marker(active.session_id)
        self._cleanup_session_media(active.session_id)
        self._write_session(
            active.session_id,
            active.camera_id,
            "error",
            active.created_at,
            error_code=error_code,
        )
        self.active_session = None

    def _session_media_state(self, session_id: str) -> tuple[bool, int]:
        session_dir = self._session_path(session_id)
        playlist = session_dir / "index.m3u8"
        try:
            playlist_ready = (
                playlist.is_file()
                and not playlist.is_symlink()
                and playlist.stat().st_size > 0
            )
        except OSError:
            playlist_ready = False
        latest_segment_mtime = 0
        has_segment = False
        for segment in session_dir.glob("*.ts"):
            try:
                if (
                    segment.is_file()
                    and not segment.is_symlink()
                    and segment.stat().st_size > 0
                ):
                    has_segment = True
                    latest_segment_mtime = max(
                        latest_segment_mtime,
                        segment.stat().st_mtime_ns,
                    )
            except OSError:
                continue
        return (playlist_ready and has_segment, latest_segment_mtime)

    def _update_session(self) -> None:
        active = self.active_session
        if active is None:
            return
        now = time.monotonic()
        if now - active.last_heartbeat > self.session_ttl:
            self._stop_active("expired")
            return
        if active.process.poll() is not None:
            self._fail_active("ffmpeg_start_failed")
            return
        media_ready, media_mtime = self._session_media_state(active.session_id)
        if media_mtime > active.last_media_mtime_ns:
            active.last_media_mtime_ns = media_mtime
            active.last_media_progress = now
        if active.status == "starting" and media_ready:
            active.status = "ready"
            self._write_session(
                active.session_id,
                active.camera_id,
                "ready",
                active.created_at,
            )
            return
        timeout = (
            HLS_START_TIMEOUT if active.status == "starting" else HLS_STALL_TIMEOUT
        )
        if now - active.last_media_progress > timeout:
            self._fail_active("ffmpeg_start_failed")

    def _ack(
        self,
        command: dict[str, Any],
        status: str,
        *,
        error_code: str | None = None,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "schemaVersion": SCHEMA_VERSION,
            "commandId": command["commandId"],
            "action": command.get("action"),
            "status": status,
            "processedAt": _iso_now(),
        }
        for key in ("cameraId", "sessionId"):
            if isinstance(command.get(key), str):
                data[key] = command[key]
        if error_code:
            data["errorCode"] = error_code
        return data

    def _write_start_failure(
        self,
        command: dict[str, Any],
        error_code: str,
    ) -> None:
        session_id = command.get("sessionId")
        camera_id = command.get("cameraId")
        if not _valid_uuid(session_id) or not _valid_uuid(camera_id):
            return
        session_dir = self._session_path(session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        existing = self._read_session(session_id) or {}
        created_at = existing.get("createdAt")
        if _parse_iso(created_at) is None:
            created_at = _iso_now()
        self._write_session(
            session_id,
            camera_id,
            "error",
            created_at,
            error_code=error_code,
        )

    @staticmethod
    def _validate_command(data: dict[str, Any]) -> str | None:
        if set(data) - _COMMAND_KEYS:
            return "unknown_fields"
        if data.get("schemaVersion") != SCHEMA_VERSION:
            return "unsupported_schema"
        if not _valid_uuid(data.get("commandId")):
            return "invalid_command_id"
        action = data.get("action")
        if action not in _ALLOWED_ACTIONS:
            return "invalid_action"
        requested_at = _parse_iso(data.get("requestedAt"))
        if requested_at is None:
            return "invalid_requested_at"
        if action not in {"stop", "shutdown"}:
            age = (_utc_now() - requested_at).total_seconds()
            if age > MAX_COMMAND_AGE or age < -MAX_COMMAND_FUTURE_SKEW:
                return "command_expired"
        camera_id = data.get("cameraId")
        session_id = data.get("sessionId")
        has_location = "location" in data
        if action == "refresh":
            if not _valid_uuid(camera_id) or session_id is not None or has_location:
                return "invalid_command_shape"
        elif action == "start":
            if (
                not _valid_uuid(camera_id)
                or not _valid_uuid(session_id)
                or has_location
            ):
                return "invalid_command_shape"
        elif action in {"heartbeat", "stop"}:
            if not _valid_uuid(session_id) or camera_id is not None or has_location:
                return "invalid_command_shape"
        elif action == "set_location":
            if not _valid_uuid(camera_id) or session_id is not None:
                return "invalid_command_shape"
            if CameraLocation.from_dict(data.get("location")) is None:
                return "invalid_location"
        elif action == "clear_location":
            if not _valid_uuid(camera_id) or session_id is not None or has_location:
                return "invalid_command_shape"
        elif camera_id is not None or session_id is not None or has_location:
            return "invalid_command_shape"
        return None

    def _execute_command(self, command: dict[str, Any]) -> dict[str, Any]:
        action = command["action"]
        if action == "shutdown":
            if self.active_session is not None:
                self._stop_active("stopped_by_request")
            self.request_stop()
            return self._ack(command, "completed")

        if action in {"set_location", "clear_location"}:
            camera_id = command["cameraId"]
            camera = self.cameras.get(camera_id)
            if camera is None:
                return self._ack(
                    command,
                    "rejected",
                    error_code="camera_not_found",
                )
            if action == "set_location":
                location = CameraLocation.from_dict(command.get("location"))
                if location is None:
                    return self._ack(
                        command,
                        "rejected",
                        error_code="invalid_location",
                    )
                self.location_store.set(camera_id, location)
                camera.location = location
            else:
                self.location_store.clear(camera_id)
                camera.location = None
            self.write_catalog()
            return self._ack(command, "completed")

        if action == "refresh":
            camera_id = command["cameraId"]
            if camera_id not in self.cameras:
                return self._ack(command, "rejected", error_code="camera_not_found")
            if not self.runner.available:
                return self._ack(command, "error", error_code="ffmpeg_unavailable")
            self._last_snapshot_attempt[camera_id] = 0.0
            return self._ack(command, "accepted")

        if action == "start":
            camera_id = command["cameraId"]
            session_id = command["sessionId"]
            camera = self.cameras.get(camera_id)
            if camera is None:
                self._write_start_failure(command, "camera_not_found")
                return self._ack(command, "rejected", error_code="camera_not_found")
            if not self.runner.available:
                self._write_start_failure(command, "ffmpeg_unavailable")
                return self._ack(command, "error", error_code="ffmpeg_unavailable")
            if self.active_session is not None:
                if self.active_session.session_id == session_id:
                    return self._ack(command, "accepted")
                self._write_start_failure(command, "session_replaced")
                return self._ack(
                    command,
                    "rejected",
                    error_code="session_limit_reached",
                )
            created_at = _iso_now()
            session_dir = self._session_path(session_id)
            session_dir.mkdir(parents=True, exist_ok=True)
            self._write_session(
                session_id,
                camera_id,
                "starting",
                created_at,
            )
            process = self.runner.start_hls(camera, session_dir)
            if process is None:
                self._write_session(
                    session_id,
                    camera_id,
                    "error",
                    created_at,
                    error_code="ffmpeg_start_failed",
                )
                return self._ack(
                    command,
                    "error",
                    error_code="ffmpeg_start_failed",
                )
            try:
                self._write_process_marker(session_id, process)
            except OSError:
                self._terminate_process(process)
                self._write_session(
                    session_id,
                    camera_id,
                    "error",
                    created_at,
                    error_code="ffmpeg_start_failed",
                )
                return self._ack(
                    command,
                    "error",
                    error_code="ffmpeg_start_failed",
                )
            self.active_session = ActiveSession(
                session_id=session_id,
                camera_id=camera_id,
                process=process,
                created_at=created_at,
                last_heartbeat=time.monotonic(),
            )
            return self._ack(command, "accepted")

        session_id = command["sessionId"]
        if action == "heartbeat":
            active = self.active_session
            if active is None or active.session_id != session_id:
                return self._ack(
                    command,
                    "rejected",
                    error_code="session_not_found",
                )
            active.last_heartbeat = time.monotonic()
            self._write_session(
                active.session_id,
                active.camera_id,
                active.status,
                active.created_at,
            )
            return self._ack(command, "completed")

        active = self.active_session
        if active is not None and active.session_id == session_id:
            self._stop_active("stopped_by_request")
            return self._ack(command, "completed")
        existing = self._read_session(session_id)
        if existing and existing.get("status") in {"stopped", "error"}:
            return self._ack(command, "completed")
        return self._ack(command, "rejected", error_code="session_not_found")

    def _process_command_file(self, source: Path) -> None:
        if source.is_symlink():
            source.unlink(missing_ok=True)
            return
        try:
            if source.stat().st_size > MAX_COMMAND_BYTES:
                source.unlink(missing_ok=True)
                return
        except OSError:
            return
        data = _read_json(source)
        if data is None:
            source.unlink(missing_ok=True)
            return
        command_id = data.get("commandId")
        if not _valid_uuid(command_id) or source.name != f"{command_id}.json":
            source.unlink(missing_ok=True)
            return
        outbox = self.outbox_dir / source.name
        if outbox.exists():
            source.unlink(missing_ok=True)
            return
        processing = self.processing_dir / source.name
        try:
            os.replace(source, processing)
        except OSError:
            return
        try:
            validation_error = self._validate_command(data)
            if validation_error:
                if data.get("action") == "start":
                    session_error = (
                        "session_replaced"
                        if validation_error == "command_expired"
                        else "ffmpeg_start_failed"
                    )
                    self._write_start_failure(data, session_error)
                ack = self._ack(data, "rejected", error_code=validation_error)
            else:
                ack = self._execute_command(data)
            _atomic_write_json(outbox, ack)
        except Exception:
            _log.exception("Falha interna ao processar comando %s", command_id)
            if data.get("action") == "start":
                try:
                    self._write_start_failure(data, "ffmpeg_start_failed")
                except OSError:
                    pass
            _atomic_write_json(
                outbox,
                self._ack(data, "error", error_code="internal_error"),
            )
        finally:
            processing.unlink(missing_ok=True)

    def process_commands(self) -> None:
        candidates = list(self.inbox_dir.glob("*.json"))

        def order(path: Path) -> tuple[float, int, str]:
            data = _read_json(path) or {}
            requested_at = _parse_iso(data.get("requestedAt"))
            try:
                timestamp = requested_at.timestamp() if requested_at else float("-inf")
            except (OSError, OverflowError, ValueError):
                timestamp = float("-inf")
            try:
                written_at = path.stat().st_mtime_ns
            except OSError:
                written_at = 0
            return (timestamp, written_at, str(data.get("commandId", path.name)))

        for path in sorted(candidates, key=order):
            self._process_command_file(path)
        self._prune_outbox()

    def _prune_outbox(self) -> None:
        """Limita a retenção de acks, principalmente heartbeats frequentes."""
        now = time.time()
        survivors: list[tuple[float, Path]] = []
        for path in self.outbox_dir.glob("*.json"):
            try:
                if path.is_symlink():
                    path.unlink(missing_ok=True)
                    continue
                modified = path.stat().st_mtime
                if now - modified > OUTBOX_RETENTION:
                    path.unlink(missing_ok=True)
                    continue
                survivors.append((modified, path))
            except OSError:
                continue
        survivors.sort(key=lambda item: item[0], reverse=True)
        for _modified, path in survivors[MAX_OUTBOX_FILES:]:
            path.unlink(missing_ok=True)

    def request_stop(self, *_args: object) -> None:
        self._stop_event.set()

    def tick(self) -> None:
        now = time.monotonic()
        if now - self._last_inventory_load >= HEARTBEAT_INTERVAL:
            self.refresh_inventory()
        self.process_commands()
        if self._stop_event.is_set():
            return
        self._harvest_snapshots()
        self._schedule_snapshots()
        self._update_session()
        if now - self._last_catalog_write >= HEARTBEAT_INTERVAL:
            self.write_catalog()

    def run(self, *, once: bool = False) -> None:
        self.acquire_lock()
        try:
            self.refresh_inventory()
            self.write_catalog()
            if once:
                self.process_commands()
                if not self._stop_event.is_set():
                    for camera_id in list(self.cameras):
                        self.capture_now(camera_id)
                    self._update_session()
                    self.write_catalog()
                return
            while not self._stop_event.is_set():
                self.tick()
                self._stop_event.wait(self.poll_interval)
        finally:
            if self.active_session is not None:
                self._stop_active("stopped_by_request")
            self._executor.shutdown(wait=True, cancel_futures=True)
            try:
                self.write_catalog(bridge_status="unavailable")
            except OSError:
                pass
            self.release_lock()


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("deve ser maior que zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="varedura-camera-bridge",
        description="Publica câmeras do Varedura para o runtime sanitizado do Mural.",
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--log-file", type=Path)
    parser.add_argument(
        "--poll-interval",
        type=_positive_float,
        default=DEFAULT_POLL_INTERVAL,
    )
    parser.add_argument(
        "--snapshot-interval",
        type=_positive_float,
        default=DEFAULT_SNAPSHOT_INTERVAL,
    )
    parser.add_argument(
        "--session-ttl",
        type=_positive_float,
        default=DEFAULT_SESSION_TTL,
    )
    parser.add_argument("--once", action="store_true")
    return parser


def configure_logging(path: Path | None) -> Path:
    log_path = path or DATA_DIR / "logs" / "camera_bridge.log"
    log_path = log_path.expanduser().resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.addFilter(RedactingFilter())
    handler.setFormatter(
        RedactingFormatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    _log.handlers.clear()
    _log.setLevel(logging.INFO)
    _log.addHandler(handler)
    _log.propagate = False
    return log_path


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    configure_logging(args.log_file)
    bridge = CameraBridge(
        args.output_dir,
        poll_interval=args.poll_interval,
        snapshot_interval=args.snapshot_interval,
        session_ttl=args.session_ttl,
    )
    try:
        signal.signal(signal.SIGINT, bridge.request_stop)
        signal.signal(signal.SIGTERM, bridge.request_stop)
    except ValueError:
        pass
    _log.info("Ponte iniciada (output=%s)", bridge.output_dir)
    try:
        bridge.run(once=args.once)
    except BridgeAlreadyRunning as exc:
        _log.error("%s", redact_sensitive(exc))
        return 3
    except KeyboardInterrupt:
        bridge.request_stop()
    _log.info("Ponte encerrada")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
