"""Privacy-aware detection of the current League of Legends game endpoint.

Detection is intentionally passive: the Riot Live Client Data API confirms a
running match, then only the real game process' existing UDP sockets are read.
No packet is sent to a game port and no elevation is attempted.
"""

from __future__ import annotations

import ipaddress
import json
import platform
import queue
import socket
import ssl
import threading
import time
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from urllib.parse import urlsplit
from urllib.request import (
    HTTPRedirectHandler,
    HTTPSHandler,
    ProxyHandler,
    Request,
    build_opener,
)

from monitor.ping_targets import PingTarget, TargetCategory


LIVE_CLIENT_URL = "https://127.0.0.1:2999/liveclientdata/gamestats"
_MAX_LIVE_RESPONSE = 64 * 1024
_GAME_PORT_RANGES = (range(5000, 5501), range(7000, 8001))
_GAME_PROCESS_NAMES = {
    "league of legends.exe",
    "league of legends",
    "leagueoflegends",
}


class LeagueDetectorState(StrEnum):
    IDLE = "idle"
    API_UNAVAILABLE = "api_unavailable"
    ACTIVE_PENDING = "active_pending"
    ACTIVE = "active"
    AMBIGUOUS = "ambiguous"
    PERMISSION_DENIED = "permission_denied"
    UNSUPPORTED = "unsupported"
    ENDED = "ended"


@dataclass(frozen=True, slots=True)
class LeagueCandidate:
    host: str
    port: int
    pid: int
    process_name: str
    process_create_time: float

    @property
    def stability_key(self) -> tuple[str, int, int, float]:
        return (self.host, self.port, self.pid, self.process_create_time)


@dataclass(frozen=True, slots=True)
class LeagueEndpoint:
    host: str
    port: int
    pid: int
    process_name: str
    process_create_time: float
    session_id: str
    generation: int
    experimental: bool = False
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def target_id(self) -> str:
        return f"league_match_{self.session_id}"

    def to_ping_target(self) -> PingTarget:
        return PingTarget(
            id=self.target_id,
            label="League of Legends - partida atual",
            host=self.host,
            category=TargetCategory.LEAGUE_MATCH,
            description=(
                f"Endpoint UDP observado passivamente na porta {self.port}; "
                "o ping ICMP pode ser filtrado."
            ),
            ephemeral=True,
        )

    def export_host(self, *, include_full_ip: bool = False) -> str:
        return self.host if include_full_ip else mask_endpoint_ip(self.host)

    def to_export_dict(self, *, include_full_ip: bool = False) -> dict[str, Any]:
        return {
            "host": self.export_host(include_full_ip=include_full_ip),
            "port": self.port,
            "session_id": self.session_id,
            "generation": self.generation,
            "experimental": self.experimental,
        }


@dataclass(frozen=True, slots=True)
class LeagueDetectionResult:
    state: LeagueDetectorState
    endpoint: LeagueEndpoint | None = None
    detail: str = ""
    candidate_count: int = 0
    api_failures: int = 0
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def mask_endpoint_ip(host: str) -> str:
    """Return the privacy default used in reports (/24 IPv4 or /64 IPv6)."""

    address = ipaddress.ip_address(host)
    prefix = 24 if address.version == 4 else 64
    return str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))


def _validate_live_client_url(url: str) -> None:
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 2999
        or parsed.path != "/liveclientdata/gamestats"
        or parsed.query
        or parsed.fragment
        or parsed.username is not None
    ):
        raise ValueError("Live Client TLS exception is restricted to Riot loopback")


class _RejectLiveClientRedirects(HTTPRedirectHandler):
    """Keep the loopback-only TLS exception from following a redirect."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise OSError("Live Client redirects are not allowed")


def fetch_live_client_data(
    *,
    url: str = LIVE_CLIENT_URL,
    timeout: float = 0.75,
) -> Mapping[str, Any]:
    """Read Riot's loopback-only self-signed Live Client endpoint.

    The custom TLS context and proxy bypass are constructed only after a strict
    URL check.  They can never be reused for an external host.
    """

    _validate_live_client_url(url)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    timeout = max(0.05, timeout)
    deadline = time.monotonic() + timeout
    opener = build_opener(
        ProxyHandler({}),
        HTTPSHandler(context=context),
        _RejectLiveClientRedirects(),
    )
    request = Request(
        url,
        headers={"Accept": "application/json", "User-Agent": "Varedura/1.0"},
        method="GET",
    )
    with opener.open(request, timeout=timeout) as response:
        status = getattr(response, "status", 200)
        if status != 200:
            raise OSError(f"Live Client returned HTTP {status}")
        chunks: list[bytes] = []
        size = 0
        while size <= _MAX_LIVE_RESPONSE:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Live Client response exceeded its total deadline")
            try:
                response.fp.raw._sock.settimeout(remaining)
            except (AttributeError, OSError):
                pass
            chunk = response.read(min(4096, _MAX_LIVE_RESPONSE + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
        payload = b"".join(chunks)
    if len(payload) > _MAX_LIVE_RESPONSE:
        raise ValueError("Live Client response is unexpectedly large")
    decoded = json.loads(payload.decode("utf-8"))
    if not isinstance(decoded, Mapping):
        raise ValueError("Live Client response must be an object")
    return decoded


def _default_process_iter() -> Iterable[Any]:
    import psutil

    return psutil.process_iter(
        ["pid", "name", "exe", "cmdline", "create_time"],
        ad_value=None,
    )


def _is_game_process(
    name: str, executable: str = "", cmdline: Iterable[str] = ()
) -> bool:
    candidates = {name.replace("\\", "/").rsplit("/", 1)[-1].casefold()}
    if executable:
        candidates.add(executable.replace("\\", "/").rsplit("/", 1)[-1].casefold())
    for argument in cmdline:
        candidate = str(argument).replace("\\", "/").rsplit("/", 1)[-1].casefold()
        if candidate:
            candidates.add(candidate)
    if any(
        marker in candidate
        for candidate in candidates
        for marker in ("riotclient", "leagueclient", "crashhandler", "renderer")
    ):
        return False
    return bool(candidates & _GAME_PROCESS_NAMES)


def _remote_address(connection: Any) -> tuple[str, int] | None:
    remote = getattr(connection, "raddr", None)
    if not remote:
        return None
    try:
        if hasattr(remote, "ip"):
            host, port = remote.ip, remote.port
        else:
            host, port = remote[0], remote[1]
        host = str(host).split("%", 1)[0]
        address = ipaddress.ip_address(host)
        if address.version == 6 and address.ipv4_mapped is not None:
            address = address.ipv4_mapped
        if not address.is_global:
            return None
        return address.compressed, int(port)
    except (ValueError, TypeError, IndexError, AttributeError):
        return None


def _is_game_port(port: int) -> bool:
    return any(port in ports for ports in _GAME_PORT_RANGES)


class LeagueMatchDetector:
    """Stateful two-sample detector for League game UDP endpoints."""

    def __init__(
        self,
        *,
        live_client_probe: Callable[[], Mapping[str, Any]] = fetch_live_client_data,
        process_iter: Callable[[], Iterable[Any]] = _default_process_iter,
        system: str | None = None,
        session_id_factory: Callable[[], str] = lambda: uuid.uuid4().hex,
        required_stable_samples: int = 2,
        api_failures_to_end: int = 3,
        scan_timeout: float = 1.0,
    ) -> None:
        if required_stable_samples < 2:
            raise ValueError("at least two stable endpoint samples are required")
        self._live_client_probe = live_client_probe
        self._process_iter = process_iter
        self._system = (system or platform.system()).lower()
        self._session_id_factory = session_id_factory
        self._required_stable_samples = required_stable_samples
        self._api_failures_to_end = max(1, api_failures_to_end)
        self._scan_timeout = max(0.1, scan_timeout)
        self._session_id: str | None = None
        self._endpoint: LeagueEndpoint | None = None
        self._candidate_key: tuple[str, int, int, float] | None = None
        self._stable_samples = 0
        self._api_failures = 0
        self._generation = 0
        self._lock = threading.RLock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def current_endpoint(self) -> LeagueEndpoint | None:
        with self._lock:
            return self._endpoint

    def poll(self) -> LeagueDetectionResult:
        """Perform one bounded Live API check followed by passive socket reading."""

        if self._system not in {"windows", "darwin", "linux"}:
            return LeagueDetectionResult(
                LeagueDetectorState.UNSUPPORTED,
                detail=f"Plataforma nao suportada: {self._system}",
            )
        try:
            live_data = self._live_client_probe()
            if not isinstance(live_data, Mapping):
                raise ValueError("invalid Live Client response")
            game_time = live_data.get("gameTime")
            if not isinstance(game_time, (int, float)) or isinstance(game_time, bool):
                raise ValueError(
                    "Live Client response does not confirm an active match"
                )
        except Exception as exc:
            return self._on_api_failure(exc)

        with self._lock:
            self._api_failures = 0
            if self._session_id is None:
                self._session_id = self._session_id_factory()
                self._candidate_key = None
                self._stable_samples = 0
        candidates, permission_denied, unavailable, incomplete = self._scan_candidates()
        if unavailable:
            return LeagueDetectionResult(
                LeagueDetectorState.UNSUPPORTED,
                endpoint=self.current_endpoint,
                detail="psutil nao esta disponivel",
            )
        if incomplete:
            with self._lock:
                self._endpoint = None
                self._candidate_key = None
                self._stable_samples = 0
            return LeagueDetectionResult(
                LeagueDetectorState.ACTIVE_PENDING,
                detail="Varredura de sockets excedeu o prazo; nenhum endpoint foi escolhido.",
            )
        if len(candidates) > 1:
            with self._lock:
                self._candidate_key = None
                self._stable_samples = 0
                self._endpoint = None
            return LeagueDetectionResult(
                LeagueDetectorState.AMBIGUOUS,
                detail="Mais de um endpoint UDP elegivel; nenhum foi escolhido.",
                candidate_count=len(candidates),
            )
        if not candidates:
            with self._lock:
                self._endpoint = None
                self._candidate_key = None
                self._stable_samples = 0
            if permission_denied:
                return LeagueDetectionResult(
                    LeagueDetectorState.PERMISSION_DENIED,
                    detail="Sem permissao para ler os sockets do processo do jogo.",
                )
            return LeagueDetectionResult(
                LeagueDetectorState.ACTIVE_PENDING,
                detail="Partida confirmada; aguardando um endpoint UDP publico elegivel.",
            )

        candidate = candidates[0]
        with self._lock:
            if candidate.stability_key == self._candidate_key:
                self._stable_samples += 1
            else:
                self._candidate_key = candidate.stability_key
                self._stable_samples = 1
            if self._stable_samples >= self._required_stable_samples:
                current_key = (
                    (
                        self._endpoint.host,
                        self._endpoint.port,
                        self._endpoint.pid,
                        self._endpoint.process_create_time,
                    )
                    if self._endpoint is not None
                    else None
                )
                if current_key != candidate.stability_key:
                    self._generation += 1
                    self._endpoint = LeagueEndpoint(
                        host=candidate.host,
                        port=candidate.port,
                        pid=candidate.pid,
                        process_name=candidate.process_name,
                        process_create_time=candidate.process_create_time,
                        session_id=self._session_id or self._session_id_factory(),
                        generation=self._generation,
                        experimental=self._system == "linux",
                    )
                endpoint = self._endpoint
                state = LeagueDetectorState.ACTIVE
                detail = "Endpoint UDP confirmado em duas leituras estaveis."
            else:
                endpoint = self._endpoint
                state = LeagueDetectorState.ACTIVE_PENDING
                detail = "Candidato encontrado; aguardando a segunda leitura estavel."
        return LeagueDetectionResult(
            state,
            endpoint=endpoint,
            detail=detail,
            candidate_count=1,
        )

    def _on_api_failure(self, error: Exception) -> LeagueDetectionResult:
        with self._lock:
            self._api_failures += 1
            failures = self._api_failures
            endpoint = self._endpoint
            session_active = self._session_id is not None
            if session_active and failures >= self._api_failures_to_end:
                self._reset_session_locked()
                return LeagueDetectionResult(
                    LeagueDetectorState.ENDED,
                    detail="Live Client ficou indisponivel por tres leituras; sessao encerrada.",
                    api_failures=failures,
                )
            if session_active:
                return LeagueDetectionResult(
                    LeagueDetectorState.ACTIVE
                    if endpoint
                    else LeagueDetectorState.ACTIVE_PENDING,
                    endpoint=endpoint,
                    detail=f"Live Client temporariamente indisponivel: {error}",
                    api_failures=failures,
                )
        return LeagueDetectionResult(
            LeagueDetectorState.API_UNAVAILABLE,
            detail=f"Nenhuma partida confirmada pelo Live Client: {error}",
            api_failures=failures,
        )

    def _reset_session_locked(self) -> None:
        self._session_id = None
        self._endpoint = None
        self._candidate_key = None
        self._stable_samples = 0
        self._api_failures = 0

    @staticmethod
    def _bounded_connections(
        process: Any, timeout: float
    ) -> tuple[Any, Exception | None, bool]:
        results: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

        def read_connections() -> None:
            try:
                results.put((True, process.net_connections(kind="inet")))
            except Exception as exc:
                results.put((False, exc))

        threading.Thread(target=read_connections, daemon=True).start()
        try:
            ok, value = results.get(timeout=max(0.01, timeout))
        except queue.Empty:
            return None, None, True
        return (value, None, False) if ok else (None, value, False)

    def _scan_candidates(
        self,
    ) -> tuple[list[LeagueCandidate], bool, bool, bool]:
        try:
            import psutil
        except ImportError:
            return [], False, True, False
        permission_denied = False
        incomplete = False
        candidates: dict[tuple[str, int, int, float], LeagueCandidate] = {}
        deadline = time.monotonic() + self._scan_timeout
        try:
            processes = self._process_iter()
            for process in processes:
                if self._stop_event.is_set() or time.monotonic() >= deadline:
                    incomplete = True
                    break
                info = getattr(process, "info", {}) or {}
                name = str(info.get("name") or "")
                executable = str(info.get("exe") or "")
                cmdline = info.get("cmdline") or ()
                if isinstance(cmdline, str):
                    cmdline = (cmdline,)
                if not _is_game_process(name, executable, cmdline):
                    continue
                try:
                    pid = int(info.get("pid") or getattr(process, "pid"))
                    create_time_raw = info.get("create_time")
                    create_time = float(
                        create_time_raw
                        if create_time_raw is not None
                        else process.create_time()
                    )
                    connections, connection_error, timed_out = (
                        self._bounded_connections(process, deadline - time.monotonic())
                    )
                    if timed_out:
                        incomplete = True
                        break
                    if connection_error is not None:
                        raise connection_error
                except (psutil.AccessDenied, PermissionError):
                    permission_denied = True
                    continue
                except (psutil.NoSuchProcess, psutil.ZombieProcess, OSError):
                    continue
                for connection in connections:
                    if time.monotonic() >= deadline:
                        incomplete = True
                        break
                    if getattr(connection, "type", None) != socket.SOCK_DGRAM:
                        continue
                    remote = _remote_address(connection)
                    if remote is None or not _is_game_port(remote[1]):
                        continue
                    candidate = LeagueCandidate(
                        host=remote[0],
                        port=remote[1],
                        pid=pid,
                        process_name=name or executable.rsplit("/", 1)[-1],
                        process_create_time=create_time,
                    )
                    candidates[candidate.stability_key] = candidate
                if incomplete:
                    break
        except (psutil.AccessDenied, PermissionError):
            # A generator-wide failure means the process list was not fully
            # inspected.  Even if an eligible socket was already observed, it
            # is unsafe to treat that partial set as unambiguous.
            permission_denied = True
            incomplete = True
        except (psutil.Error, OSError):
            incomplete = True
        return (
            []
            if incomplete
            else sorted(candidates.values(), key=lambda item: item.stability_key),
            permission_denied,
            False,
            incomplete,
        )

    def start(
        self,
        callback: Callable[[LeagueDetectionResult], None],
        *,
        interval: float = 1.5,
    ) -> None:
        """Start polling; three misses at the default interval remove within 6s."""

        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()

            def loop() -> None:
                next_poll = time.monotonic()
                period = max(0.25, interval)
                while not self._stop_event.is_set():
                    delay = next_poll - time.monotonic()
                    if delay > 0 and self._stop_event.wait(delay):
                        break
                    result = self.poll()
                    if self._stop_event.is_set():
                        break
                    try:
                        callback(result)
                    except Exception:
                        pass
                    next_poll = max(next_poll + period, time.monotonic())

            self._thread = threading.Thread(
                target=loop,
                name="varedura-league-detector",
                daemon=True,
            )
            self._thread.start()

    def stop(self, *, wait: bool = True) -> None:
        self._stop_event.set()
        thread = self._thread
        if wait and thread is not None and thread is not threading.current_thread():
            thread.join(timeout=2.0)


__all__ = [
    "LIVE_CLIENT_URL",
    "LeagueCandidate",
    "LeagueDetectionResult",
    "LeagueDetectorState",
    "LeagueEndpoint",
    "LeagueMatchDetector",
    "fetch_live_client_data",
    "mask_endpoint_ip",
]
