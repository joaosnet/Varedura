"""
V's Network Stalker v3.2 - Monitor de Rede em Tempo Real com Escaner de Portas e Velocidade

Funcionalidades:
    - Monitoramento de ping em tempo real (gateway local + externo)
    - Teste de velocidade contínuo (download/upload) em background
    - Verificação de conformidade com velocidade contratada (ANATEL 80%)
    - Gráfico ASCII ao vivo com picos e mínimos
    - Tabela de uso de rede por processo
    - Escaner de portas TCP/UDP integrado
    - Controles interativos por teclado
    - Exportação para PNG/CSV
"""

import subprocess
import platform
import time
import datetime
import psutil
import re
import os
import threading

from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Deque

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from monitor.port_scanner import run_full_scan, PortScannerState
from monitor.speed_tester import (
    get_speed_tester,
    start_continuous_testing,
    stop_continuous_testing,
    speed_config,
)

# Windows keyboard input
if platform.system().lower() == "windows":
    import msvcrt
else:
    import sys
    import select


# ==============================================================================
# CONFIGURAÇÕES DO STALKER (Modificáveis em tempo de execução)
# ==============================================================================
@dataclass
class StalkerConfig:
    gateway_ip: str = "192.168.18.1"  # IP do Roteador
    external_ip: str = "ec2.sa-east-1.amazonaws.com"  # AWS EC2 por que o LOL teoricamente usa essa região
    lag_threshold_ms: int = 100  # Limite para considerar LAG (ms)
    interval: float = 1.0  # Intervalo de atualização (segundos)
    history_size: int = 8  # Quantas linhas de log manter
    graph_width: int = 40  # Largura do gráfico ASCII
    graph_history: int = 100  # Quantos pontos manter no histórico
    show_ports: bool = True  # Mostrar painel de portas
    port_scan_interval: int = 5  # Intervalo entre scans de porta (em ciclos)
    show_speed: bool = True  # Mostrar painel de velocidade


@dataclass
class PingStats:
    """Estatísticas de histórico de ping com timestamps."""

    history: Deque[Optional[float]] = field(default_factory=lambda: deque(maxlen=100))
    timestamps: Deque[datetime.datetime] = field(
        default_factory=lambda: deque(maxlen=100)
    )
    min_ms: Optional[float] = None
    max_ms: Optional[float] = None
    avg_ms: Optional[float] = None
    start_time: Optional[datetime.datetime] = None

    def add(self, ms: Optional[float]):
        now = datetime.datetime.now()
        if self.start_time is None:
            self.start_time = now
        self.history.append(ms)
        self.timestamps.append(now)
        valid = [x for x in self.history if x is not None]
        if valid:
            self.min_ms = min(valid)
            self.max_ms = max(valid)
            self.avg_ms = sum(valid) / len(valid)


console = Console()
config = StalkerConfig()
local_stats = PingStats()
external_stats = PingStats()
port_scanner_state = PortScannerState()
show_help = False
running = True
scan_counter = 0


def is_android():
    """Detecta se está rodando no Android (Termux)."""
    return "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ


def get_ping_command(host):
    """Retorna o comando de ping adequado para o SO."""
    system = platform.system().lower()
    if system == "windows":
        return ["ping", "-n", "1", "-w", "1000", host]
    else:
        return ["ping", "-c", "1", "-W", "1", host]


def parse_ping(output):
    """Extrai o tempo em ms da resposta do ping."""
    try:
        output_str = output.decode("utf-8", errors="ignore")
        match = re.search(r"(?:tempo|time)[=<]([\d\.]+)", output_str, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return None
    except Exception:
        return None


def run_ping(host):
    """Executa o ping e retorna o tempo ou None se falhar."""
    try:
        cmd = get_ping_command(host)
        startupinfo = None
        if platform.system().lower() == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo
        )
        return parse_ping(result.stdout)
    except Exception:
        return None


def get_top_network_hogs():
    """Identifica os processos (Top 5) com mais conexões de rede ativas.

    NOTA: Usa conexões de rede reais em vez de I/O geral pra evitar
    falsos positivos como o Windows Defender (que faz muito I/O de disco).
    """
    procs = {}
    try:
        # Coletar conexões de rede ativas
        connections = psutil.net_connections(kind="inet")

        for conn in connections:
            # Só conta conexões estabelecidas ou em transferência
            if conn.status in ("ESTABLISHED", "SYN_SENT", "SYN_RECV"):
                pid = conn.pid
                if pid and pid > 0:
                    if pid not in procs:
                        try:
                            proc = psutil.Process(pid)
                            procs[pid] = {
                                "name": proc.name(),
                                "connections": 0,
                                "bytes": 0,
                            }
                            # Tentar pegar I/O do processo (complementar)
                            try:
                                io = proc.io_counters()
                                if io:
                                    procs[pid]["bytes"] = io.read_bytes + io.write_bytes
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    procs[pid]["connections"] += 1
    except (psutil.AccessDenied, PermissionError):
        # Fallback: usar método antigo se não tiver permissão
        return _get_top_network_hogs_fallback()
    except Exception:
        return _get_top_network_hogs_fallback()

    # Ordenar por conexões ativas, não por bytes totais
    result = [
        (
            pid,
            info["name"],
            info["connections"] * 1024 * 1024,
        )  # Multiplicar pra manter compatibilidade de display
        for pid, info in procs.items()
    ]
    result.sort(key=lambda x: x[2], reverse=True)
    return result[:5]


def _get_top_network_hogs_fallback():
    """Fallback usando I/O counters (menos preciso, usado quando sem permissão)."""
    procs = []
    try:
        for p in psutil.process_iter(["pid", "name", "io_counters"]):
            try:
                io = p.info["io_counters"]
                if io:
                    if hasattr(io, "read_bytes") and hasattr(io, "write_bytes"):
                        total_bytes = io.read_bytes + io.write_bytes
                    else:
                        total_bytes = 0
                    if hasattr(io, "other_bytes"):
                        total_bytes += io.other_bytes
                    if total_bytes > 0:
                        procs.append((p.info["pid"], p.info["name"], total_bytes))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception:
        pass

    procs.sort(key=lambda x: x[2], reverse=True)
    return procs[:5]


def analyze_lag_source(
    local_ms: Optional[float], ext_ms: Optional[float], threshold: int, procs: list
) -> tuple[str, str]:
    """Analisa a origem provável do lag com mais inteligência.

    Retorna: (suspeito, explicação)

    Lógica:
    - Se local_ms alto E ext_ms alto → Problema no roteador/rede interna
    - Se local_ms OK mas ext_ms alto → Problema no provedor/internet externa
    - Se local_ms alto mas ext_ms OK → Improvável (ext passa pelo local)
    - Se ambos timeout → Problema crítico no roteador ou cabo
    - Se tem processo com muitas conexões → Pode ser ele saturando
    """
    # Caso 1: Timeout total
    if local_ms is None and ext_ms is None:
        return (
            "🔌 ROTEADOR/CABO",
            "Sem resposta do gateway - verificar cabo/roteador/energia",
        )

    # Caso 2: Só gateway com timeout (crítico)
    if local_ms is None:
        return (
            "🔌 ROTEADOR",
            "Gateway não responde mas internet pode estar ok - problema no roteador",
        )

    # Caso 3: Só externo com timeout
    if ext_ms is None:
        return (
            "🌐 PROVEDOR/DNS",
            "Gateway OK mas sem internet - problema no provedor ou DNS",
        )

    # Caso 4: Ambos acima do threshold
    local_lag = local_ms > threshold
    ext_lag = ext_ms > threshold

    if local_lag and ext_lag:
        # Se a diferença entre local e externo é pequena, provável roteador
        diff = abs(ext_ms - local_ms)
        if diff < 20:  # Menos de 20ms de diferença
            return (
                "🔌 ROTEADOR",
                f"Lag similar em ambos ({local_ms:.0f}ms vs {ext_ms:.0f}ms) - roteador sobrecarregado",
            )
        else:
            # Grande diferença: pode ser tanto roteador quanto provedor
            return (
                "🔌 ROTEADOR + 🌐 PROVEDOR",
                f"Lag composto - roteador ({local_ms:.0f}ms) + internet adicional",
            )

    # Caso 5: Só externo com lag (local ok)
    if ext_lag and not local_lag:
        return (
            "🌐 PROVEDOR/ROTA",
            f"Gateway rápido ({local_ms:.0f}ms) mas internet lenta - problema externo",
        )

    # Caso 6: Só local com lag (raro, já que ext passa por local)
    if local_lag and not ext_lag:
        # Isso é teoricamente estranho... ext_ms deveria incluir local_ms
        # Pode ser flutuação ou cache
        return (
            "🔌 ROTEADOR (flutuação)",
            "Padrão incomum - verificar estabilidade do roteador",
        )

    # Caso 7: Tudo OK, mas ainda assim quer info
    if procs:
        top_proc = procs[0][1] if procs[0][1] else "Desconhecido"
        return f"✅ OK ({top_proc})", "Rede estável - maior uso de rede no momento"

    return "✅ OK", "Rede estável"


# --- Entrada de Teclado ---
# Debounce: evita múltiplas leituras acidentais
_last_key_time = 0.0
_KEY_COOLDOWN = 0.3  # 300ms cooldown entre teclas


def _flush_stdin():
    """Limpa completamente o buffer de entrada do teclado."""
    if platform.system().lower() == "windows":
        # Consumir todos os bytes pendentes
        while msvcrt.kbhit():
            msvcrt.getch()


def check_keyboard():
    """
    Verificação não-bloqueante de teclado com:
    - Filtragem de escape sequences
    - Debounce para evitar glitches
    - Flush do buffer
    """
    global _last_key_time

    # Debounce: ignorar teclas muito próximas
    current_time = time.time()
    if current_time - _last_key_time < _KEY_COOLDOWN:
        _flush_stdin()  # Limpar buffer mas não processar
        return None

    if platform.system().lower() == "windows":
        if msvcrt.kbhit():
            # Ler apenas o primeiro byte
            first_byte = msvcrt.getch()

            # Se é uma tecla especial (setas, F-keys), o primeiro byte é 0 ou 224
            # Precisamos consumir o segundo byte e ignorar
            if first_byte in (b"\x00", b"\xe0"):
                if msvcrt.kbhit():
                    msvcrt.getch()  # Consumir segundo byte da tecla especial
                return None

            # Limpar qualquer coisa extra no buffer
            _flush_stdin()

            try:
                key = first_byte.decode("utf-8", errors="ignore").lower()
                # Apenas aceitar caracteres ASCII simples (a-z, 0-9)
                if len(key) == 1 and key.isalnum():
                    _last_key_time = current_time  # Atualizar timestamp
                    return key
            except Exception:
                pass
            return None
    else:
        # Sistemas Unix-like
        if select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.read(1).lower()
            # Mesmo filtro para Unix
            if key.isalnum():
                _last_key_time = current_time
                return key
            return None
    return None


def handle_key(key: str) -> Optional[str]:
    """Processa entrada de teclado. Retorna mensagem para log ou None."""
    global show_help, running, config, port_scanner_state

    if key == "q":
        running = False
        return None
    elif key == "h":
        show_help = not show_help
        return "[dim]Painel de ajuda alternado[/]"
    elif key == "g":
        return prompt_change_gateway()
    elif key == "e":
        return prompt_change_external()
    elif key == "t":
        return prompt_change_threshold()
    elif key == "i":
        return prompt_change_interval()
    elif key == "x":
        return export_combined_report()
    elif key == "p":
        config.show_ports = not config.show_ports
        status = "ativado" if config.show_ports else "desativado"
        return f"[yellow]Painel de portas {status}[/]"
    elif key == "s":
        port_scanner_state = run_full_scan()
        return f"[green]Scan de portas atualizado: {port_scanner_state.total_tcp} TCP, {port_scanner_state.total_udp} UDP[/]"
    elif key == "v":
        config.show_speed = not config.show_speed
        if config.show_speed:
            return "[yellow]Painel de velocidade ativado[/]"
        else:
            # Exportar relatório ao pausar velocidade
            export_msg = export_combined_report()
            return f"[yellow]Painel de velocidade desativado[/] | {export_msg}"
    elif key == "c":
        return prompt_change_contracted_speed()
    return None


def prompt_change_gateway() -> str:
    """Altera IP do gateway (cicla entre valores comuns)."""
    common_gateways = ["192.168.1.1", "192.168.0.1", "192.168.18.1", "10.0.0.1"]
    try:
        current_idx = common_gateways.index(config.gateway_ip)
        config.gateway_ip = common_gateways[(current_idx + 1) % len(common_gateways)]
    except ValueError:
        config.gateway_ip = common_gateways[0]
    return f"[yellow]Gateway alterado para: {config.gateway_ip}[/]"


def prompt_change_external() -> str:
    """Altera IP externo (cicla entre servidores DNS)."""
    dns_servers = ["8.8.8.8", "1.1.1.1", "208.67.222.222", "9.9.9.9"]
    try:
        current_idx = dns_servers.index(config.external_ip)
        config.external_ip = dns_servers[(current_idx + 1) % len(dns_servers)]
    except ValueError:
        config.external_ip = dns_servers[0]
    return f"[yellow]DNS externo alterado para: {config.external_ip}[/]"


def prompt_change_threshold() -> str:
    """Cicla entre valores de threshold."""
    thresholds = [50, 100, 150, 200, 300]
    try:
        current_idx = thresholds.index(config.lag_threshold_ms)
        config.lag_threshold_ms = thresholds[(current_idx + 1) % len(thresholds)]
    except ValueError:
        config.lag_threshold_ms = thresholds[0]
    return f"[yellow]Threshold alterado para: {config.lag_threshold_ms}ms[/]"


def prompt_change_interval() -> str:
    """Cicla entre valores de intervalo."""
    intervals = [0.5, 1.0, 2.0, 5.0]
    try:
        current_idx = intervals.index(config.interval)
        config.interval = intervals[(current_idx + 1) % len(intervals)]
    except ValueError:
        config.interval = intervals[0]
    return f"[yellow]Intervalo alterado para: {config.interval}s[/]"


def prompt_change_contracted_speed() -> str:
    """Cicla entre valores comuns de velocidade contratada no Brasil."""
    # Valores comuns de planos de internet no Brasil (Mbps)
    speeds = [
        (100, 50),  # 100 Mbps down / 50 Mbps up
        (200, 100),  # 200 Mbps down / 100 Mbps up
        (300, 150),  # 300 Mbps down / 150 Mbps up
        (500, 250),  # 500 Mbps down / 250 Mbps up
        (600, 300),  # 600 Mbps down / 300 Mbps up
        (1000, 500),  # 1 Gbps down / 500 Mbps up
    ]
    current = (
        speed_config.velocidade_contratada_down,
        speed_config.velocidade_contratada_up,
    )
    try:
        current_idx = speeds.index(current)
        new_speed = speeds[(current_idx + 1) % len(speeds)]
    except ValueError:
        new_speed = speeds[0]

    speed_config.velocidade_contratada_down = new_speed[0]
    speed_config.velocidade_contratada_up = new_speed[1]
    return f"[yellow]Velocidade contratada: {new_speed[0]}/{new_speed[1]} Mbps (↓/↑)[/]"


# --- Estado de Exportação em Background ---
_export_status = {"running": False, "message": None, "completed": False}
_export_lock = threading.Lock()


def _generate_combined_pdf_worker():
    """Worker que gera o PDF combinado em background."""
    global _export_status

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("exports", exist_ok=True)

        # Importar matplotlib e configurar backend não-interativo
        import matplotlib

        matplotlib.use("Agg")  # Backend não-interativo para threads
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from matplotlib.backends.backend_pdf import PdfPages

        pdf_filename = f"exports/network_report_{timestamp}.pdf"
        csv_ping_filename = f"exports/ping_history_{timestamp}.csv"
        csv_speed_filename = f"exports/speed_history_{timestamp}.csv"

        # Exportar CSVs primeiro (rápido)
        # CSV de Ping
        try:
            with open(csv_ping_filename, "w", encoding="utf-8") as f:
                f.write("timestamp,local_ms,external_ms\n")
                for ts, local, ext in zip(
                    local_stats.timestamps, local_stats.history, external_stats.history
                ):
                    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                    local_val = f"{local:.1f}" if local is not None else ""
                    ext_val = f"{ext:.1f}" if ext is not None else ""
                    f.write(f"{ts_str},{local_val},{ext_val}\n")
        except Exception:
            pass  # Continua mesmo se CSV falhar

        # CSV de Velocidade
        tester = get_speed_tester()
        stats = tester.stats

        if stats.test_count > 0:
            try:
                with open(csv_speed_filename, "w", encoding="utf-8") as f:
                    f.write(
                        "timestamp,download_mbps,upload_mbps,contrato_down,contrato_up,pct_down,pct_up,status\n"
                    )
                    for ts, down, up in zip(
                        stats.timestamps, stats.history_down, stats.history_up
                    ):
                        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                        pct_down = (
                            down / speed_config.velocidade_contratada_down
                        ) * 100
                        pct_up = (up / speed_config.velocidade_contratada_up) * 100
                        min_pct = speed_config.percentual_minimo
                        status = (
                            "OK"
                            if pct_down >= min_pct and pct_up >= min_pct
                            else "ABAIXO"
                        )
                        f.write(
                            f"{ts_str},{down:.2f},{up:.2f},"
                            f"{speed_config.velocidade_contratada_down},{speed_config.velocidade_contratada_up},"
                            f"{pct_down:.1f},{pct_up:.1f},{status}\n"
                        )
            except Exception:
                pass

        # Gerar PDF combinado
        with PdfPages(pdf_filename) as pdf:
            # === Página 1: Relatório de Ping ===
            fig1, ax1 = plt.subplots(figsize=(14, 8))

            times_ping = list(local_stats.timestamps)
            local_valid = list(local_stats.history)
            ext_valid = list(external_stats.history)

            if times_ping:
                ax1.plot(
                    times_ping,
                    local_valid,
                    label=f"Gateway ({config.gateway_ip})",
                    color="cyan",
                    linewidth=2,
                )
                ax1.plot(
                    times_ping,
                    ext_valid,
                    label=f"Externo ({config.external_ip})",
                    color="orange",
                    linewidth=2,
                )
                ax1.axhline(
                    y=config.lag_threshold_ms,
                    color="red",
                    linestyle="--",
                    label=f"Limite ({config.lag_threshold_ms}ms)",
                )
                ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
                plt.xticks(rotation=45)

                start_str = times_ping[0].strftime("%Y-%m-%d %H:%M:%S")
                end_str = times_ping[-1].strftime("%H:%M:%S")
                ax1.set_title(
                    f"V's Network Stalker - Histórico de Ping\n{start_str} → {end_str}",
                    fontsize=14,
                    fontweight="bold",
                )

                # Adicionar estatísticas
                if local_stats.min_ms is not None:
                    stats_text = (
                        f"Gateway - Min: {local_stats.min_ms:.1f}ms | "
                        f"Máx: {local_stats.max_ms:.1f}ms | Méd: {local_stats.avg_ms:.1f}ms\n"
                        f"Externo - Min: {external_stats.min_ms:.1f}ms | "
                        f"Máx: {external_stats.max_ms:.1f}ms | Méd: {external_stats.avg_ms:.1f}ms"
                    )
                    ax1.text(
                        0.02,
                        0.98,
                        stats_text,
                        transform=ax1.transAxes,
                        fontsize=9,
                        verticalalignment="top",
                        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                    )
            else:
                ax1.text(
                    0.5, 0.5, "Sem dados de ping disponíveis", ha="center", va="center"
                )

            ax1.set_xlabel("Tempo")
            ax1.set_ylabel("Ping (ms)")
            ax1.legend(loc="upper right")
            ax1.grid(True, alpha=0.3)

            plt.tight_layout()
            pdf.savefig(fig1, dpi=150)
            plt.close(fig1)

            # === Página 2: Relatório de Velocidade ===
            if stats.test_count > 0:
                fig2, (ax2, ax3) = plt.subplots(2, 1, figsize=(14, 10))

                times_speed = list(stats.timestamps)
                down_vals = list(stats.history_down)
                up_vals = list(stats.history_up)

                # Calcular estatísticas
                avg_down = (
                    sum(stats.history_down) / len(stats.history_down)
                    if stats.history_down
                    else 0
                )
                avg_up = (
                    sum(stats.history_up) / len(stats.history_up)
                    if stats.history_up
                    else 0
                )
                min_down = min(stats.history_down) if stats.history_down else 0
                max_down = max(stats.history_down) if stats.history_down else 0
                min_up = min(stats.history_up) if stats.history_up else 0
                max_up = max(stats.history_up) if stats.history_up else 0

                violations_down = sum(
                    1
                    for d in stats.history_down
                    if (d / speed_config.velocidade_contratada_down * 100)
                    < speed_config.percentual_minimo
                )
                violations_up = sum(
                    1
                    for u in stats.history_up
                    if (u / speed_config.velocidade_contratada_up * 100)
                    < speed_config.percentual_minimo
                )

                # Gráfico de Download
                ax2.plot(
                    times_speed,
                    down_vals,
                    label="Download",
                    color="cyan",
                    linewidth=2,
                    marker="o",
                    markersize=4,
                )
                ax2.axhline(
                    y=speed_config.velocidade_contratada_down,
                    color="green",
                    linestyle="--",
                    label=f"Contrato ({speed_config.velocidade_contratada_down} Mbps)",
                )
                ax2.axhline(
                    y=speed_config.velocidade_contratada_down * 0.8,
                    color="red",
                    linestyle=":",
                    label="Mínimo ANATEL (80%)",
                )
                ax2.set_ylabel("Download (Mbps)")
                ax2.legend(loc="upper right")
                ax2.grid(True, alpha=0.3)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

                # Gráfico de Upload
                ax3.plot(
                    times_speed,
                    up_vals,
                    label="Upload",
                    color="orange",
                    linewidth=2,
                    marker="o",
                    markersize=4,
                )
                ax3.axhline(
                    y=speed_config.velocidade_contratada_up,
                    color="green",
                    linestyle="--",
                    label=f"Contrato ({speed_config.velocidade_contratada_up} Mbps)",
                )
                ax3.axhline(
                    y=speed_config.velocidade_contratada_up * 0.8,
                    color="red",
                    linestyle=":",
                    label="Mínimo ANATEL (80%)",
                )
                ax3.set_xlabel("Tempo")
                ax3.set_ylabel("Upload (Mbps)")
                ax3.legend(loc="upper right")
                ax3.grid(True, alpha=0.3)
                ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

                plt.suptitle(
                    f"V's Speed Report - {stats.test_count} testes\n"
                    f"Download: Média {avg_down:.1f} Mbps (Min: {min_down:.1f}, Max: {max_down:.1f}) | "
                    f"Violações ANATEL: {violations_down}\n"
                    f"Upload: Média {avg_up:.1f} Mbps (Min: {min_up:.1f}, Max: {max_up:.1f}) | "
                    f"Violações ANATEL: {violations_up}",
                    fontsize=10,
                    fontweight="bold",
                )

                plt.tight_layout()
                pdf.savefig(fig2, dpi=150)
                plt.close(fig2)

        with _export_lock:
            _export_status["message"] = (
                f"[green]✅ Relatório exportado: {pdf_filename}[/]"
            )
            _export_status["completed"] = True
            _export_status["running"] = False

    except ImportError as e:
        with _export_lock:
            _export_status["message"] = f"[red]❌ matplotlib não disponível: {e}[/]"
            _export_status["completed"] = True
            _export_status["running"] = False
    except Exception as e:
        with _export_lock:
            _export_status["message"] = (
                f"[red]❌ Erro ao gerar relatório: {str(e)[:50]}[/]"
            )
            _export_status["completed"] = True
            _export_status["running"] = False


def export_combined_report() -> str:
    """Inicia exportação do relatório combinado em thread separada."""
    global _export_status

    with _export_lock:
        if _export_status["running"]:
            return "[yellow]⏳ Exportação já em andamento...[/]"

        # Verificar se há dados para exportar
        if not local_stats.history and get_speed_tester().stats.test_count == 0:
            return "[yellow]Nenhum dado para exportar ainda[/]"

        _export_status["running"] = True
        _export_status["completed"] = False
        _export_status["message"] = None

    # Iniciar thread de exportação
    export_thread = threading.Thread(target=_generate_combined_pdf_worker, daemon=True)
    export_thread.start()

    return "[cyan]📄 Gerando relatório PDF em background...[/]"


def get_export_status() -> Optional[str]:
    """Retorna status da exportação se completada."""
    global _export_status

    with _export_lock:
        if _export_status["completed"]:
            msg = _export_status["message"]
            _export_status["completed"] = False
            _export_status["message"] = None
            return msg
    return None


# --- Gráfico ASCII ---
def make_ascii_graph(
    stats: PingStats, width: int = 40, height: int = 8, label: str = ""
) -> str:
    """Cria gráfico ASCII de linha a partir do histórico de ping."""
    history = list(stats.history)
    if not history:
        return " " * width

    # Filtrar valores None, substituir por 0 para exibição
    values = [v if v is not None else 0 for v in history[-width:]]
    if not values:
        return " " * width

    # Normalizar para altura
    max_val = max(max(values), config.lag_threshold_ms * 1.5) if values else 100

    chars = "▁▂▃▄▅▆▇█"

    result = []
    for v in values:
        if v == 0:
            result.append(" ")
        else:
            # Normalizar para faixa 0-7
            normalized = min(7, int((v / max_val) * 7))
            result.append(chars[normalized])

    # Preencher até largura
    graph_line = "".join(result).ljust(width)

    # Adicionar linha de stats
    if stats.min_ms is not None:
        stats_line = (
            f"Min:{stats.min_ms:.0f} Máx:{stats.max_ms:.0f} Méd:{stats.avg_ms:.0f}ms"
        )
    else:
        stats_line = "Aguardando dados..."

    return f"{label}\n{graph_line}\n[dim]{stats_line}[/]"


# --- Componentes da Interface ---
def make_header():
    """Cria o cabeçalho do dashboard."""
    os_name = platform.system()
    if is_android():
        os_name = "Android (Termux)"

    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # Informações de portas
    ports_info = (
        f"TCP:{port_scanner_state.total_tcp} UDP:{port_scanner_state.total_udp}"
    )

    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_row(
        f"[b bold cyan]💀 V's NETWORK STALKER v3.1[/]  [dim]|  {current_date} {current_time}[/]"
    )
    grid.add_row(
        f"[dim]SO: {os_name} | Gateway: {config.gateway_ip} | DNS: {config.external_ip} | "
        f"Portas: {ports_info} | Limite: {config.lag_threshold_ms}ms[/]"
    )
    grid.add_row(
        "[dim italic]Teclas: [H]elp [G]ateway [E]xternal [T]hreshold [I]nterval [P]ortas [S]can e[X]portar [Q]uit[/]"
    )
    return Panel(grid, style="white on blue")


def make_ping_table(local_ms, ext_ms, threshold):
    """Cria a tabela de status dos Pings."""
    table = Table(expand=True, box=box.ROUNDED)
    table.add_column("Destino", justify="center")
    table.add_column("Ping (ms)", justify="center")
    table.add_column("Status", justify="center")

    # Formatação Local
    if local_ms is None:
        local_display = "TIMEOUT"
        local_style = "bold white on red"
        local_status = "CRÍTICO"
    else:
        local_display = f"{local_ms:.1f} ms"
        if local_ms > threshold:
            local_style = "bold red"
            local_status = "LAG 🏠"
        else:
            local_style = "green"
            local_status = "OK"

    # Formatação Externa
    if ext_ms is None:
        ext_display = "TIMEOUT"
        ext_style = "bold white on red"
        ext_status = "CRÍTICO"
    else:
        ext_display = f"{ext_ms:.1f} ms"
        if ext_ms > threshold:
            ext_style = "bold red"
            ext_status = "LAG 🌐"
        else:
            ext_style = "green"
            ext_status = "OK"

    table.add_row(
        f"Gateway ({config.gateway_ip})",
        Text(local_display, style=local_style),
        Text(local_status, style=local_style),
    )
    table.add_row(
        f"DNS ({config.external_ip})",
        Text(ext_display, style=ext_style),
        Text(ext_status, style=ext_style),
    )

    return Panel(table, title="📡 Status da Conexão", border_style="cyan")


def make_graph_panel():
    """Cria painel com ambos os gráficos de ping mostrando info de tempo."""
    local_graph = make_ascii_graph(
        local_stats, width=config.graph_width, label="[cyan]Gateway[/]"
    )
    ext_graph = make_ascii_graph(
        external_stats, width=config.graph_width, label="[orange1]Externo[/]"
    )

    # Info de intervalo de tempo
    if local_stats.start_time:
        start_str = local_stats.start_time.strftime("%H:%M:%S")
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        time_info = f"[dim]{start_str} → {now_str}[/]"
    else:
        time_info = "[dim]Aguardando dados...[/]"

    # Indicador de linha de threshold
    threshold_info = f"[red]--- Limite: {config.lag_threshold_ms}ms ---[/]"

    content = Text.from_markup(
        f"{time_info}\n\n{local_graph}\n\n{ext_graph}\n\n{threshold_info}"
    )
    return Panel(
        content, title="📊 Histórico de Ping (Tempo Real)", border_style="magenta"
    )


def make_process_table(procs):
    """Cria a tabela de processos suspeitos."""
    table = Table(expand=True, box=box.SIMPLE_HEAD)
    table.add_column("PID", style="dim", width=8)
    table.add_column("Processo", style="bold yellow")
    table.add_column("Uso Total (MB)", justify="right", style="magenta")

    if not procs:
        if is_android():
            table.add_row("-", "[dim]Sem acesso (Requer Root?)[/]", "-")
        else:
            table.add_row("-", "[dim]Nenhum tráfego detectado[/]", "-")
    else:
        for pid, name, bytes_total in procs:
            mb = bytes_total / (1024 * 1024)
            proc_name = name if name else "Desconhecido"
            table.add_row(str(pid), proc_name, f"{mb:.2f} MB")

    return Panel(
        table, title="🔍 Top Consumo de Rede (Acumulado)", border_style="yellow"
    )


def make_ports_panel():
    """Cria painel de portas TCP em listening."""
    table = Table(expand=True, box=box.SIMPLE_HEAD)
    table.add_column("Porta", style="bold yellow", width=8, justify="center")
    table.add_column("Processo", style="bold green")
    table.add_column("End.", style="dim", width=10)

    # Mostrar no máximo 8 portas
    ports_to_show = port_scanner_state.listening_tcp[:8]

    if not ports_to_show:
        table.add_row("-", "[dim]Nenhuma porta encontrada[/]", "-")
    else:
        for port_info in ports_to_show:
            endereco = port_info.endereco if port_info.endereco != "Todas" else "*"
            table.add_row(str(port_info.porta), port_info.processo[:20], endereco[:10])

    # Info adicional
    total = len(port_scanner_state.listening_tcp)
    extra_info = f" (+{total - 8})" if total > 8 else ""

    last_scan = port_scanner_state.last_scan_time or "N/A"

    return Panel(
        table,
        title=f"🔌 Portas TCP ({total}{extra_info}) [dim]Último: {last_scan}[/]",
        border_style="green",
    )


def make_connections_panel():
    """Cria painel de processos com mais conexões."""
    table = Table(expand=True, box=box.SIMPLE_HEAD)
    table.add_column("Processo", style="bold cyan")
    table.add_column("Conexões", style="bold yellow", justify="center", width=8)
    table.add_column("RAM", style="dim", justify="right", width=8)

    connections = port_scanner_state.top_connections[:5]

    if not connections:
        table.add_row("[dim]Aguardando scan...[/]", "-", "-")
    else:
        for proc in connections:
            ram_str = f"{proc.memoria_mb:.0f}MB" if proc.memoria_mb > 0 else "N/A"
            table.add_row(proc.nome[:18], str(proc.conexoes), ram_str)

    return Panel(
        table,
        title=f"🏆 Top Conexões (Estab: {port_scanner_state.total_established})",
        border_style="cyan",
    )


def make_speed_panel():
    """Cria painel de velocidade mostrando todos provedores em tempo real."""
    try:
        tester = get_speed_tester()
        snapshot = tester.get_stats_snapshot()

        table = Table(expand=True, box=box.ROUNDED)
        table.add_column("Provedor", style="bold cyan", width=12)
        table.add_column("Download", justify="center", width=10)
        table.add_column("Upload", justify="center", width=10)
        table.add_column("Ping", justify="center", width=8)

        results_by_provider = snapshot.get("results_by_provider", {})
        is_testing = snapshot.get("is_testing", False)

        # Mostrar resultados de cada provedor
        if results_by_provider:
            for provider_name, result in results_by_provider.items():
                try:
                    down_mbps = float(result.download_mbps)
                    up_mbps = float(result.upload_mbps)
                    ping_ms = float(result.ping_ms)
                except (ValueError, TypeError, AttributeError):
                    continue

                # Verificar compliance
                min_down = speed_config.velocidade_contratada_down * (
                    speed_config.percentual_minimo / 100
                )
                min_up = speed_config.velocidade_contratada_up * (
                    speed_config.percentual_minimo / 100
                )

                down_ok = down_mbps >= min_down
                up_ok = up_mbps >= min_up

                down_style = "green" if down_ok else "bold red"
                up_style = "green" if up_ok else "bold red"

                # Nome curto do provedor
                short_name = str(provider_name)[:11]

                table.add_row(
                    short_name,
                    f"[{down_style}]{down_mbps:.0f} Mbps[/]",
                    f"[{up_style}]{up_mbps:.0f} Mbps[/]",
                    f"{ping_ms:.0f}ms",
                )

        # Se estiver testando, mostrar progresso em tempo real
        if is_testing:
            current_provider = snapshot.get("current_provider", "")
            progress_mbps = snapshot.get("progress_mbps", 0.0)
            progress_phase = snapshot.get("progress_phase", "")

            if current_provider:
                # Mostrar velocidade em tempo real se disponível
                if progress_mbps > 0 and progress_phase == "download":
                    table.add_row(
                        f"[yellow]{current_provider[:11]}[/]",
                        f"[yellow]{progress_mbps:.0f} Mbps[/]",
                        "[dim]baixando...[/]",
                        "[dim]...[/]",
                    )
                elif progress_phase == "upload":
                    table.add_row(
                        f"[yellow]{current_provider[:11]}[/]",
                        "[dim]ok[/]",
                        "[yellow]upload...[/]",
                        "[dim]...[/]",
                    )
                else:
                    table.add_row(
                        f"[yellow]{current_provider[:11]}[/]",
                        "[dim]conectando[/]",
                        "[dim]...[/]",
                        "[dim]...[/]",
                    )
            else:
                table.add_row(
                    "[yellow]...[/]", "[dim]iniciando[/]", "[dim]...[/]", "[dim]...[/]"
                )
        elif not results_by_provider:
            if snapshot.get("last_error"):
                error_msg = str(snapshot.get("last_error", "Erro"))[:20]
                table.add_row("-", f"[red]{error_msg}[/]", "-", "-")
            else:
                table.add_row(
                    "[dim]...[/]", "[dim]aguardando[/]", "[dim]...[/]", "[dim]...[/]"
                )

        test_count = snapshot.get("test_count", 0)
        num_providers = len(results_by_provider)

        return Panel(
            table,
            title=f"Velocidade ({num_providers} provedores, {test_count} testes)",
            subtitle=f"[dim]Contrato: {speed_config.velocidade_contratada_down:.0f}/{speed_config.velocidade_contratada_up:.0f} Mbps | Min: {speed_config.percentual_minimo:.0f}%[/]",
            border_style="magenta",
        )
    except Exception as e:
        return Panel(
            f"[red]Erro: {str(e)[:30]}[/]",
            title="Velocidade",
            border_style="red",
        )


def make_log_panel(log_events):
    """Cria o painel de histórico de alertas."""
    lines = []
    for line in log_events:
        lines.append(Text.from_markup(line))

    # Juntar com newlines criando um grupo renderizável
    content = Text()
    for i, line in enumerate(lines):
        content.append_text(line)
        if i < len(lines) - 1:
            content.append("\n")

    return Panel(
        content, title="📜 Histórico de Alertas (Últimos Eventos)", border_style="red"
    )


def make_help_panel():
    """Cria painel de ajuda com atalhos de teclado."""
    help_text = """
[bold cyan]CONTROLES:[/]

  [yellow]H[/] - Mostrar/esconder esta ajuda
  [yellow]G[/] - Ciclar IP do Gateway (192.168.x.1, 10.0.0.1)
  [yellow]E[/] - Ciclar DNS externo (8.8.8.8, 1.1.1.1, etc)
  [yellow]T[/] - Ciclar limite de lag (50, 100, 150, 200, 300ms)
  [yellow]I[/] - Ciclar intervalo de refresh (0.5, 1, 2, 5s)
  [yellow]P[/] - Mostrar/esconder painel de portas
  [yellow]V[/] - Mostrar/esconder painel de velocidade
  [yellow]C[/] - Ciclar velocidade contratada (100, 200, 300, 500, 600, 1000 Mbps)
  [yellow]S[/] - Atualizar scan de portas manualmente
  [yellow]X[/] - Exportar dados para CSV e gráfico PNG
  [yellow]Q[/] - Sair

[dim]Os valores ciclam automaticamente entre opções comuns.[/]
[dim]Velocidade: Monitor contínuo (ANATEL exige mínimo 80% da contratada)[/]
"""
    return Panel(Text.from_markup(help_text), title="❓ Ajuda", border_style="green")


def main():
    global running, show_help, port_scanner_state, scan_counter

    # Layout Principal
    layout = Layout()

    log_events = deque(maxlen=config.history_size)
    log_events.append("[dim]Monitoramento iniciado... aguardando anomalias.[/]")

    if is_android():
        log_events.append(
            "[yellow]Android detectado: Leitura de processos pode ser limitada.[/]"
        )

    # Scan inicial de portas em background (não trava a inicialização)
    def _initial_port_scan():
        global port_scanner_state
        try:
            port_scanner_state = run_full_scan()
        except Exception:
            pass  # Silently fail, will show empty state

    threading.Thread(target=_initial_port_scan, daemon=True).start()
    log_events.append("[dim]Scan de portas iniciando em background...[/]")

    # Iniciar teste de velocidade contínuo em background
    try:
        start_continuous_testing()
        log_events.append(
            f"[cyan]Monitor de velocidade iniciado (Contrato: {speed_config.velocidade_contratada_down}/{speed_config.velocidade_contratada_up} Mbps)[/]"
        )
    except Exception as e:
        log_events.append(f"[red]Erro ao iniciar speed test: {e}[/]")

    with Live(layout, refresh_per_second=4, screen=True):
        while running:
            try:
                # Verificar entrada de teclado
                key = check_keyboard()
                if key:
                    msg = handle_key(key)
                    if msg:
                        log_events.append(
                            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
                        )

                # Verificar status da exportação em background
                export_msg = get_export_status()
                if export_msg:
                    log_events.append(
                        f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {export_msg}"
                    )

                start_time = datetime.datetime.now().strftime("%H:%M:%S")

                # 1. Executa Testes de Ping
                local_ms = run_ping(config.gateway_ip)
                ext_ms = run_ping(config.external_ip)

                # Atualizar stats para gráfico
                local_stats.add(local_ms)
                external_stats.add(ext_ms)

                # 2. Verifica Processos de Rede
                procs = get_top_network_hogs()

                # 3. Scan de portas periódico
                scan_counter += 1
                if scan_counter >= config.port_scan_interval:
                    scan_counter = 0
                    try:
                        port_scanner_state = run_full_scan()
                    except Exception:
                        pass  # Silently fail port scan

                # 4. Lógica de Log e Alerta (com análise inteligente de origem)
                alert_triggered = False

                if local_ms and local_ms > config.lag_threshold_ms:
                    log_events.append(
                        f"[{start_time}] [bold red]ALERTA:[/] Lag local alto: {local_ms:.1f}ms (Gateway)"
                    )
                    alert_triggered = True
                elif ext_ms and ext_ms > config.lag_threshold_ms:
                    log_events.append(
                        f"[{start_time}] [bold orange1]ALERTA:[/] Lag externo detectado: {ext_ms:.1f}ms (DNS)"
                    )
                    alert_triggered = True
                elif local_ms is None or ext_ms is None:
                    log_events.append(
                        f"[{start_time}] [bold white on red]CRÍTICO:[/] Perda de pacote detectada!"
                    )
                    alert_triggered = True

                if alert_triggered:
                    # Usar análise inteligente de origem do lag
                    suspeito, explicacao = analyze_lag_source(
                        local_ms, ext_ms, config.lag_threshold_ms, procs
                    )
                    log_events.append(f"   ↳ [bold yellow]Diagnóstico:[/] {suspeito}")
                    log_events.append(f"   ↳ [dim]{explicacao}[/]")

                    # Mostrar processo com mais conexões se houver (como info secundária)
                    if procs and not suspeito.startswith("🔌"):
                        top_hog = procs[0]
                        conns = top_hog[2] // (1024 * 1024)  # Número de conexões
                        hog_name = top_hog[1] if top_hog[1] else "Desconhecido"
                        log_events.append(
                            f"   ↳ [dim]Top conexões: {hog_name} ({conns} ativas)[/]"
                        )

                # 5. Construir Layout
                if show_help:
                    layout.split_column(
                        Layout(name="header", size=5),
                        Layout(name="help", ratio=1),
                    )
                    layout["header"].update(make_header())
                    layout["help"].update(make_help_panel())
                else:
                    layout.split_column(
                        Layout(name="header", size=5),
                        Layout(name="body", ratio=1),
                        Layout(name="footer", size=10),
                    )

                    if config.show_ports:
                        # Layout com portas: 3 colunas
                        layout["body"].split_row(
                            Layout(name="left", ratio=1),
                            Layout(name="center", ratio=1),
                            Layout(name="right", ratio=1),
                        )
                        layout["left"].split_column(
                            Layout(name="ping_stats", ratio=1),
                            Layout(name="graph", ratio=2),
                        )
                        layout["center"].split_column(
                            Layout(name="processes", ratio=1),
                            Layout(name="speed", ratio=1)
                            if config.show_speed
                            else Layout(name="processes_only", ratio=1),
                        )
                        if config.show_speed:
                            layout["processes"].update(make_process_table(procs))
                            layout["speed"].update(make_speed_panel())
                        else:
                            layout["center"].update(make_process_table(procs))
                        layout["right"].split_column(
                            Layout(name="ports", ratio=1),
                            Layout(name="connections", ratio=1),
                        )
                        layout["ports"].update(make_ports_panel())
                        layout["connections"].update(make_connections_panel())
                    else:
                        # Layout sem portas: 2 colunas
                        layout["body"].split_row(
                            Layout(name="left", ratio=1),
                            Layout(name="center", ratio=1),
                        )
                        layout["left"].split_column(
                            Layout(name="ping_stats", ratio=1),
                            Layout(name="graph", ratio=2),
                        )
                        if config.show_speed:
                            layout["center"].split_column(
                                Layout(name="processes", ratio=1),
                                Layout(name="speed", ratio=1),
                            )
                            layout["processes"].update(make_process_table(procs))
                            layout["speed"].update(make_speed_panel())
                        else:
                            layout["center"].update(make_process_table(procs))

                    layout["header"].update(make_header())
                    layout["ping_stats"].update(
                        make_ping_table(local_ms, ext_ms, config.lag_threshold_ms)
                    )
                    layout["graph"].update(make_graph_panel())
                    layout["footer"].update(make_log_panel(log_events))

                time.sleep(config.interval)

            except KeyboardInterrupt:
                break

    # Cleanup e exportar relatório final
    stop_continuous_testing()

    # Exportar relatório combinado ao sair (em background, não bloqueia)
    tester = get_speed_tester()
    if tester.stats.test_count > 0 or local_stats.history:
        console.print("\n[cyan]📄 Gerando relatório final em background...[/]")
        export_combined_report()
        # Aguardar no máximo 3 segundos para o relatório ser gerado
        import time as time_module

        for _ in range(30):  # 30 x 0.1s = 3s máximo
            time_module.sleep(0.1)
            status = get_export_status()
            if status:
                console.print(status)
                break


if __name__ == "__main__":
    main()
