"""
Módulo de Escaneamento de Portas para Network Stalker

Funções para monitorar portas TCP/UDP, conexões e processos de rede.
"""

import psutil
import socket
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple


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
    connections = psutil.net_connections(kind="inet")
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
                processo = "Acesso Negado"

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
    connections = psutil.net_connections(kind="inet")
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
    connections = psutil.net_connections(kind="inet")
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


def get_system_network_stats() -> Dict:
    """
    Retorna estatísticas gerais de rede do sistema.

    Returns:
        Dicionário com bytes enviados/recebidos e contadores
    """
    net_stats = psutil.net_io_counters()
    memory = psutil.virtual_memory()

    return {
        "bytes_enviados_mb": net_stats.bytes_sent / 1024 / 1024,
        "bytes_recebidos_mb": net_stats.bytes_recv / 1024 / 1024,
        "pacotes_enviados": net_stats.packets_sent,
        "pacotes_recebidos": net_stats.packets_recv,
        "memoria_percent": memory.percent,
        "memoria_usada_gb": memory.used / 1024 / 1024 / 1024,
        "memoria_total_gb": memory.total / 1024 / 1024 / 1024,
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
