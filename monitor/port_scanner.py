"""
Módulo de Escaneamento de Portas para Network Stalker

Funções para monitorar portas TCP/UDP, conexões e processos de rede.
"""

from dataclasses import dataclass, field
from pathlib import Path
import socket
from typing import Dict, List, Optional, Tuple

import psutil


def _safe_net_connections(kind: str = "inet") -> list:
    """Return active sockets, returning an empty list when denied (e.g. Android SELinux)."""
    try:
        return psutil.net_connections(kind=kind)
    except (psutil.AccessDenied, PermissionError, OSError):
        return []


@dataclass
class PortInfo:
    """Informações de uma porta em listening."""

    porta: int
    pid: Optional[int]
    processo: str
    protocolo: str  # "TCP" ou "UDP"
    endereco: str


@dataclass
class ProcessConnections:
    """Informações de conexões de um processo."""

    pid: int
    nome: str
    conexoes: int
    memoria_mb: float
    status: str


@dataclass
class PortScannerState:
    """Estado do scanner de portas."""

    listening_tcp: List[PortInfo] = field(default_factory=list)
    listening_udp: List[PortInfo] = field(default_factory=list)
    top_connections: List[ProcessConnections] = field(default_factory=list)
    total_tcp: int = 0
    total_udp: int = 0
    total_established: int = 0
    last_scan_time: Optional[str] = None


def get_listening_ports() -> Tuple[List[PortInfo], List[PortInfo], int]:
    """
    Retorna lista de portas TCP e UDP em listening.

    Returns:
        Tuple com (tcp_ports, udp_ports, total_established)
    """
    connections = _safe_net_connections(kind="inet")
    tcp_ports = []
    udp_ports = []
    established_count = 0
    seen_keys = set()

    for conn in connections:
        if conn.status == psutil.CONN_ESTABLISHED:
            established_count += 1

        if not conn.laddr:
            continue

        # Só pegar LISTENING para TCP, ou qualquer para UDP
        is_tcp = conn.type == socket.SOCK_STREAM
        is_udp = conn.type == socket.SOCK_DGRAM

        if is_tcp and conn.status != psutil.CONN_LISTEN:
            continue

        porta = conn.laddr.port
        key = f"{porta}-{conn.pid}-{'TCP' if is_tcp else 'UDP'}"

        if key in seen_keys:
            continue
        seen_keys.add(key)

        processo = "N/A"
        if conn.pid:
            try:
                proc = psutil.Process(conn.pid)
                processo = proc.name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                processo = "Acesso Negado"  # Internal label, translated at display time

        info = PortInfo(
            porta=porta,
            pid=conn.pid,
            processo=processo,
            protocolo="TCP" if is_tcp else "UDP",
            endereco=conn.laddr.ip if conn.laddr.ip != "0.0.0.0" else "Todas",
        )

        if is_tcp:
            tcp_ports.append(info)
        elif is_udp:
            udp_ports.append(info)

    # Ordenar por porta
    tcp_ports.sort(key=lambda x: x.porta)
    udp_ports.sort(key=lambda x: x.porta)

    return tcp_ports, udp_ports, established_count


def get_process_connections_count(limit: int = 5) -> List[ProcessConnections]:
    """
    Retorna os processos com mais conexões de rede.

    Args:
        limit: Número máximo de processos a retornar

    Returns:
        Lista de ProcessConnections ordenada por número de conexões
    """
    connections = _safe_net_connections(kind="inet")
    process_count: Dict[int, Dict] = {}

    for conn in connections:
        if not conn.pid:
            continue

        if conn.pid not in process_count:
            try:
                proc = psutil.Process(conn.pid)
                mem_info = proc.memory_info()
                process_count[conn.pid] = {
                    "nome": proc.name(),
                    "conexoes": 0,
                    "memoria_mb": mem_info.rss / 1024 / 1024,
                    "status": proc.status(),
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_count[conn.pid] = {
                    "nome": "Desconhecido",
                    "conexoes": 0,
                    "memoria_mb": 0,
                    "status": "N/A",
                }

        process_count[conn.pid]["conexoes"] += 1

    # Converter para lista e ordenar
    result = []
    for pid, info in process_count.items():
        result.append(
            ProcessConnections(
                pid=pid,
                nome=info["nome"],
                conexoes=info["conexoes"],
                memoria_mb=info["memoria_mb"],
                status=info["status"],
            )
        )

    result.sort(key=lambda x: x.conexoes, reverse=True)
    return result[:limit]


def search_port(porta_numero: int) -> List[Dict]:
    """
    Busca processos usando uma porta específica.

    Args:
        porta_numero: Número da porta a buscar

    Returns:
        Lista de dicionários com informações dos processos
    """
    connections = _safe_net_connections(kind="inet")
    encontrados = []

    for conn in connections:
        if conn.laddr and conn.laddr.port == porta_numero:
            if conn.pid:
                try:
                    processo = psutil.Process(conn.pid)
                    info = {
                        "protocolo": "TCP"
                        if conn.type == socket.SOCK_STREAM
                        else "UDP",
                        "status": conn.status,
                        "pid": conn.pid,
                        "nome": processo.name(),
                        "memoria_mb": processo.memory_info().rss / 1024 / 1024,
                    }
                    encontrados.append(info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    encontrados.append(
                        {
                            "protocolo": "TCP"
                            if conn.type == socket.SOCK_STREAM
                            else "UDP",
                            "status": conn.status,
                            "pid": conn.pid,
                            "nome": "Acesso Negado",
                            "memoria_mb": 0,
                        }
                    )

    return encontrados


def _read_proc_net_totals() -> tuple[int, int, int, int]:
    """Fallback counter totals from /proc/net/dev (rx_bytes, rx_pkts, tx_bytes, tx_pkts)."""
    try:
        raw = Path("/proc/net/dev").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0, 0, 0, 0
    rx_bytes = rx_pkts = tx_bytes = tx_pkts = 0
    for line in raw.splitlines():
        if ":" not in line:
            continue
        iface_part, stats_part = line.split(":", 1)
        if iface_part.strip() == "lo":
            continue
        fields = stats_part.split()
        if len(fields) < 10:
            continue
        try:
            rx_bytes += int(fields[0])
            rx_pkts += int(fields[1])
            tx_bytes += int(fields[8])
            tx_pkts += int(fields[9])
        except ValueError:
            continue
    return rx_bytes, rx_pkts, tx_bytes, tx_pkts


def _read_proc_meminfo() -> tuple[float, float, float]:
    """Fallback RAM stats from /proc/meminfo (percent, used_gb, total_gb)."""
    try:
        raw = Path("/proc/meminfo").read_text(encoding="utf-8", errors="replace")
    except OSError:
        return 0.0, 0.0, 0.0
    values_kb: dict[str, int] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, rest = line.split(":", 1)
        parts = rest.split()
        if parts and parts[0].isdigit():
            values_kb[key.strip()] = int(parts[0])
    total_kb = values_kb.get("MemTotal", 0)
    if total_kb <= 0:
        return 0.0, 0.0, 0.0
    avail_kb = values_kb.get(
        "MemAvailable",
        values_kb.get("MemFree", 0)
        + values_kb.get("Buffers", 0)
        + values_kb.get("Cached", 0),
    )
    used_kb = max(0, total_kb - avail_kb)
    percent = round(100.0 * used_kb / total_kb, 1)
    denom = 1024.0 * 1024.0
    return percent, used_kb / denom, total_kb / denom


def get_system_network_stats() -> Dict:
    """
    Retorna estatísticas gerais de rede do sistema.

    Returns:
        Dicionário com bytes enviados/recebidos e contadores
    """
    bytes_sent = bytes_recv = packets_sent = packets_recv = 0
    try:
        net_stats = psutil.net_io_counters()
        if net_stats is not None:
            bytes_sent = net_stats.bytes_sent
            bytes_recv = net_stats.bytes_recv
            packets_sent = net_stats.packets_sent
            packets_recv = net_stats.packets_recv
        else:
            bytes_recv, packets_recv, bytes_sent, packets_sent = _read_proc_net_totals()
    except (psutil.AccessDenied, PermissionError, OSError, RuntimeError):
        bytes_recv, packets_recv, bytes_sent, packets_sent = _read_proc_net_totals()

    try:
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        mem_used_gb = memory.used / 1024 / 1024 / 1024
        mem_total_gb = memory.total / 1024 / 1024 / 1024
    except (psutil.AccessDenied, PermissionError, OSError, RuntimeError):
        mem_percent, mem_used_gb, mem_total_gb = _read_proc_meminfo()

    return {
        "bytes_enviados_mb": bytes_sent / 1024 / 1024,
        "bytes_recebidos_mb": bytes_recv / 1024 / 1024,
        "pacotes_enviados": packets_sent,
        "pacotes_recebidos": packets_recv,
        "memoria_percent": mem_percent,
        "memoria_usada_gb": mem_used_gb,
        "memoria_total_gb": mem_total_gb,
    }


def run_full_scan() -> PortScannerState:
    """
    Executa scan completo e retorna estado atualizado.

    Returns:
        PortScannerState com todos os dados atualizados
    """
    import datetime

    tcp_ports, udp_ports, established = get_listening_ports()
    top_connections = get_process_connections_count(limit=5)

    return PortScannerState(
        listening_tcp=tcp_ports,
        listening_udp=udp_ports,
        top_connections=top_connections,
        total_tcp=len(tcp_ports),
        total_udp=len(udp_ports),
        total_established=established,
        last_scan_time=datetime.datetime.now().strftime("%H:%M:%S"),
    )
