"""Detecção de interfaces IPv4 locais e derivação de redes /24 (stdlib só)."""

from __future__ import annotations

import socket
from dataclasses import dataclass

from rtsp.log import obter_logger

_log = obter_logger("rede")


@dataclass(frozen=True)
class RedeLocal:
    """Uma rede /24 local detectada automaticamente."""

    base: str          # "192.168.18"
    ip_local: str      # "192.168.18.82"
    primaria: bool = False

    @property
    def ultimo_octeto(self) -> str:
        return "." + self.ip_local.rsplit(".", 1)[1]

    @property
    def rotulo(self) -> str:
        marca = " ★" if self.primaria else ""
        return f"Rede local · {self.base}.x · este PC: {self.ultimo_octeto}{marca}"


def _ip_primario() -> str | None:
    """IP de saída padrão via truque UDP-connect (não envia pacote)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def _ips_hostname() -> list[str]:
    """IPs adicionais via hostname (aditivo; pode falhar/retornar parcial)."""
    try:
        return socket.gethostbyname_ex(socket.gethostname())[2]
    except OSError:
        return []


def _eh_privado_utilizavel(ip: str) -> bool:
    if not ip or ip.startswith(("127.", "169.254.")):
        return False
    partes = ip.split(".")
    if len(partes) != 4:
        return False
    try:
        a, b = int(partes[0]), int(partes[1])
    except ValueError:
        return False
    if a == 10:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 192 and b == 168:
        return True
    return False


def _base24(ip: str) -> str:
    return ip.rsplit(".", 1)[0]


def detectar_redes() -> list[RedeLocal]:
    """Detecta redes /24 locais. Retorna [] se nada for encontrado."""
    primario = _ip_primario()
    base_primaria = _base24(primario) if primario else None

    candidatos: list[str] = []
    if primario:
        candidatos.append(primario)
    candidatos.extend(_ips_hostname())

    redes: dict[str, RedeLocal] = {}  # base -> RedeLocal (dedup por /24)
    for ip in candidatos:
        if not _eh_privado_utilizavel(ip):
            continue
        base = _base24(ip)
        primaria = base == base_primaria
        # Mantém o IP que corresponde ao primário quando há colisão de /24.
        if base not in redes or primaria:
            redes[base] = RedeLocal(base=base, ip_local=ip, primaria=primaria)

    ordenadas = sorted(redes.values(), key=lambda r: (not r.primaria, r.base))
    _log.info("Redes detectadas: %d (%s)", len(ordenadas), [r.base for r in ordenadas])
    return ordenadas
