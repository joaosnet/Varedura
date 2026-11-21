"""Provedores de velocidade sem navegador: Cloudflare e M-Lab NDT7.

Funcionam em qualquer plataforma (inclusive Termux), com servidores no Brasil:

- **Cloudflare** (``speed.cloudflare.com``): HTTP simples, fluxos paralelos.
- **M-Lab NDT7**: protocolo aberto do Measurement Lab sobre WebSocket, com
  servidores da RNP.  Um único fluxo TCP por sentido, por definição do teste.

O cliente WebSocket é mínimo e só usa a stdlib, para não exigir dependência
nova.  Importado apenas pelo processo filho ``monitor.speed_worker``.
"""

from __future__ import annotations

import base64
import datetime
import importlib.util
import json
import os
import select
import socket
import ssl
import struct
import threading
import time
import urllib.parse
import urllib.request
from typing import Callable, Optional

from monitor.speed_providers import SpeedTestProvider, SpeedTestResult

MBIT = 1_000_000


def measure_parallel(
    worker: Callable[[threading.Event, Callable[[int], None]], None],
    *,
    streams: int,
    duration: float,
    warmup: float = 1.0,
) -> float:
    """Roda ``streams`` fluxos por ``duration`` s e devolve Mbps após o aquecimento.

    ``worker(stop, add_bytes)`` transfere dados chamando ``add_bytes(n)`` até
    ``stop`` ser sinalizado.  Os primeiros ``warmup`` segundos (slow start do
    TCP) não entram na conta.
    """
    stop = threading.Event()
    lock = threading.Lock()
    total = [0]

    def add(count: int) -> None:
        with lock:
            total[0] += count

    threads = [
        threading.Thread(target=worker, args=(stop, add), daemon=True)
        for _ in range(max(1, streams))
    ]
    started = time.monotonic()
    for thread in threads:
        thread.start()
    time.sleep(min(warmup, duration / 2))
    with lock:
        base_bytes, base_time = total[0], time.monotonic()
    time.sleep(max(0.0, duration - (base_time - started)))
    with lock:
        end_bytes, end_time = total[0], time.monotonic()
    stop.set()
    for thread in threads:
        thread.join(timeout=3.0)
    elapsed = end_time - base_time
    if elapsed <= 0:
        return 0.0
    return (end_bytes - base_bytes) * 8 / MBIT / elapsed


class _ChunkStream:
    """Corpo de upload que conta os bytes realmente entregues ao socket."""

    def __init__(self, stop: threading.Event, add: Callable[[int], None], limit: int):
        self._stop = stop
        self._add = add
        self._left = limit
        self._chunk = b"\0" * 65536

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        if self._stop.is_set() or self._left <= 0:
            raise StopIteration
        piece = self._chunk[: min(len(self._chunk), self._left)]
        self._left -= len(piece)
        self._add(len(piece))
        return piece


def http_upload_worker(requests_module, url: str, *, body_bytes: int = 25_000_000):
    """Fábrica de worker que envia POSTs em sequência para ``url``."""

    def worker(stop: threading.Event, add: Callable[[int], None]) -> None:
        session = requests_module.Session()
        try:
            while not stop.is_set():
                try:
                    session.post(
                        url,
                        data=_ChunkStream(stop, add, body_bytes),
                        headers={"Content-Type": "application/octet-stream"},
                        timeout=20,
                    )
                except Exception:
                    if stop.is_set():
                        return
                    time.sleep(0.2)
        finally:
            session.close()

    return worker


def http_download_worker(requests_module, url: str):
    def worker(stop: threading.Event, add: Callable[[int], None]) -> None:
        session = requests_module.Session()
        try:
            while not stop.is_set():
                try:
                    with session.get(url, stream=True, timeout=20) as response:
                        if response.status_code != 200:
                            time.sleep(0.5)  # recusado (ex.: tamanho acima do limite)
                            continue
                        for chunk in response.iter_content(chunk_size=131072):
                            add(len(chunk))
                            if stop.is_set():
                                return
                except Exception:
                    if stop.is_set():
                        return
                    time.sleep(0.2)
        finally:
            session.close()

    return worker


class CloudflareProvider(SpeedTestProvider):
    """speed.cloudflare.com — download e upload reais, por HTTP."""

    BASE = "https://speed.cloudflare.com"

    def __init__(self) -> None:
        self._available = importlib.util.find_spec("requests") is not None
        self._error: Optional[str] = None

    @property
    def name(self) -> str:
        return "Cloudflare"

    def is_available(self) -> bool:
        return self._available

    def run_test(self) -> Optional[SpeedTestResult]:
        try:
            import requests

            pings = []
            session = requests.Session()
            for _ in range(5):
                started = time.monotonic()
                session.get(f"{self.BASE}/__down?bytes=0", timeout=8)
                pings.append((time.monotonic() - started) * 1000)
            ping_ms = min(pings[1:]) if len(pings) > 1 else 0.0  # 1ª inclui o TLS

            colo = ""
            try:
                trace = session.get(f"{self.BASE}/cdn-cgi/trace", timeout=8).text
                colo = next(
                    (
                        line.split("=", 1)[1]
                        for line in trace.splitlines()
                        if line.startswith("colo=")
                    ),
                    "",
                )
            except Exception:
                pass
            session.close()

            download = measure_parallel(
                # Acima de ~50 MB por requisição o endpoint responde 403.
                http_download_worker(requests, f"{self.BASE}/__down?bytes=25000000"),
                streams=4,
                duration=8.0,
            )
            upload = measure_parallel(
                http_upload_worker(requests, f"{self.BASE}/__up"),
                streams=3,
                duration=7.0,
            )
            if download <= 0:
                self._error = "sem dados de download"
                return None
            return SpeedTestResult(
                download_mbps=download,
                upload_mbps=upload,
                ping_ms=ping_ms,
                servidor=f"Cloudflare {colo}".strip(),
                timestamp=datetime.datetime.now(),
                provider_name=self.name,
            )
        except Exception as exc:
            self._error = str(exc)[:80]
            return None


# ---------------------------------------------------------------------------
# WebSocket mínimo (RFC 6455) para o NDT7
# ---------------------------------------------------------------------------
class _WebSocket:
    def __init__(self, url: str, subprotocol: str, timeout: float = 15.0) -> None:
        parsed = urllib.parse.urlsplit(url)
        secure = parsed.scheme == "wss"
        port = parsed.port or (443 if secure else 80)
        raw = socket.create_connection((parsed.hostname, port), timeout=timeout)
        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if secure:
            context = ssl.create_default_context()
            raw = context.wrap_socket(raw, server_hostname=parsed.hostname)
        self.sock = raw
        self._buffer = bytearray()
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.netloc}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Sec-WebSocket-Protocol: {subprotocol}\r\n"
            "User-Agent: varedura-ndt7\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        while b"\r\n\r\n" not in self._buffer:
            data = self.sock.recv(4096)
            if not data:
                raise ConnectionError("handshake encerrado")
            self._buffer += data
        head, _, rest = bytes(self._buffer).partition(b"\r\n\r\n")
        if b" 101 " not in head.split(b"\r\n", 1)[0]:
            raise ConnectionError(head.split(b"\r\n", 1)[0].decode("latin-1")[:80])
        self._buffer = bytearray(rest)

    def _fill(self, size: int) -> bool:
        while len(self._buffer) < size:
            data = self.sock.recv(262144)
            if not data:
                return False
            self._buffer += data
        return True

    def readable(self) -> bool:
        if self._buffer:
            return True
        pending = getattr(self.sock, "pending", None)
        if pending is not None and pending():
            return True
        ready, _, _ = select.select([self.sock], [], [], 0)
        return bool(ready)

    def recv_frame(self) -> tuple[int, bytes] | None:
        """Devolve ``(opcode, payload)`` ou None quando a conexão fecha."""
        if not self._fill(2):
            return None
        opcode = self._buffer[0] & 0x0F
        length = self._buffer[1] & 0x7F
        offset = 2
        if length == 126:
            if not self._fill(4):
                return None
            length = struct.unpack("!H", self._buffer[2:4])[0]
            offset = 4
        elif length == 127:
            if not self._fill(10):
                return None
            length = struct.unpack("!Q", self._buffer[2:10])[0]
            offset = 10
        if not self._fill(offset + length):
            return None
        payload = bytes(self._buffer[offset : offset + length])
        del self._buffer[: offset + length]
        if opcode == 0x8:
            return None
        return opcode, payload

    @staticmethod
    def binary_header(length: int) -> bytes:
        """Cabeçalho de frame binário de cliente (máscara zero = payload intacto)."""
        if length < 126:
            head = struct.pack("!BB", 0x82, 0x80 | length)
        elif length < 65536:
            head = struct.pack("!BBH", 0x82, 0x80 | 126, length)
        else:
            head = struct.pack("!BBQ", 0x82, 0x80 | 127, length)
        return head + b"\0\0\0\0"

    def close(self) -> None:
        try:
            self.sock.sendall(b"\x88\x80\0\0\0\0")
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


class MLabNdt7Provider(SpeedTestProvider):
    """Measurement Lab NDT7 — teste aberto, servidores da RNP no Brasil."""

    LOCATE = "https://locate.measurementlab.net/v2/nearest/ndt/ndt7"
    SUBPROTOCOL = "net.measurementlab.ndt.v7"
    DURATION = 10.0

    def __init__(self) -> None:
        self._error: Optional[str] = None

    @property
    def name(self) -> str:
        return "M-Lab NDT7"

    def is_available(self) -> bool:
        return True  # só stdlib

    def _locate(self) -> tuple[str, str, str] | None:
        request = urllib.request.Request(
            self.LOCATE, headers={"User-Agent": "varedura-ndt7"}
        )
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        for result in payload.get("results") or []:
            urls = result.get("urls") or {}
            down = urls.get("wss:///ndt/v7/download")
            up = urls.get("wss:///ndt/v7/upload")
            if down and up:
                location = result.get("location") or {}
                place = ", ".join(
                    part
                    for part in (location.get("city"), location.get("country"))
                    if part
                )
                return down, up, place or str(result.get("machine", ""))
        return None

    def _download(self, url: str) -> tuple[float, float]:
        ws = _WebSocket(url, self.SUBPROTOCOL)
        total = 0
        min_rtt_ms = 0.0
        started = time.monotonic()
        try:
            ws.sock.settimeout(8.0)
            while time.monotonic() - started < self.DURATION + 3.0:
                frame = ws.recv_frame()
                if frame is None:
                    break
                opcode, payload = frame
                total += len(payload)
                if opcode == 0x1:
                    try:
                        info = json.loads(payload).get("TCPInfo") or {}
                        if info.get("MinRTT"):
                            min_rtt_ms = float(info["MinRTT"]) / 1000.0
                    except (ValueError, AttributeError):
                        pass
        finally:
            elapsed = time.monotonic() - started
            ws.close()
        return (total * 8 / MBIT / elapsed if elapsed > 0 else 0.0), min_rtt_ms

    def _upload(self, url: str) -> float:
        ws = _WebSocket(url, self.SUBPROTOCOL)
        size = 1 << 13
        payload = b"\0" * size
        frame = _WebSocket.binary_header(size) + payload
        sent = 0
        server_bytes = 0
        server_elapsed_us = 0
        started = time.monotonic()
        try:
            ws.sock.settimeout(8.0)
            while time.monotonic() - started < self.DURATION:
                ws.sock.sendall(frame)
                sent += size
                if size < (1 << 20) and size < sent // 16:
                    size *= 2
                    frame = _WebSocket.binary_header(size) + b"\0" * size
                while ws.readable():
                    incoming = ws.recv_frame()
                    if incoming is None:
                        break
                    if incoming[0] == 0x1:
                        try:
                            info = json.loads(incoming[1]).get("TCPInfo") or {}
                            server_bytes = int(info.get("BytesReceived") or server_bytes)
                            server_elapsed_us = int(
                                info.get("ElapsedTime") or server_elapsed_us
                            )
                        except (ValueError, AttributeError, TypeError):
                            pass
        except OSError:
            pass
        finally:
            elapsed = time.monotonic() - started
            ws.close()
        # O que o servidor confirmou ter recebido é mais fiel que o que saiu
        # daqui (parte ainda estaria no buffer de envio).
        if server_bytes and server_elapsed_us:
            return server_bytes * 8 / MBIT / (server_elapsed_us / 1_000_000)
        return sent * 8 / MBIT / elapsed if elapsed > 0 else 0.0

    def run_test(self) -> Optional[SpeedTestResult]:
        try:
            located = self._locate()
            if located is None:
                self._error = "nenhum servidor M-Lab disponível"
                return None
            down_url, up_url, place = located
            download, ping_ms = self._download(down_url)
            upload = self._upload(up_url)
            if download <= 0:
                self._error = "sem dados de download"
                return None
            return SpeedTestResult(
                download_mbps=download,
                upload_mbps=upload,
                ping_ms=ping_ms,
                servidor=f"M-Lab {place}".strip(),
                timestamp=datetime.datetime.now(),
                provider_name=self.name,
            )
        except Exception as exc:
            self._error = str(exc)[:80]
            return None


__all__ = [
    "CloudflareProvider",
    "MLabNdt7Provider",
    "http_download_worker",
    "http_upload_worker",
    "measure_parallel",
]
