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
from i18n import t

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

    # Export options
    export_max_points: int = 5000  # Máximo de pontos a manter ao exportar (downsampling)
    allow_full_history_export: bool = False  # Se True, permite exportar todo o histórico sem downsampling
    export_error_log: str = "exports/export_errors.log"  # Arquivo para registrar falhas de exportação
    prefs_file: str = "exports/stalker_prefs.json"  # Arquivo para persistir preferências de exportação


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


# ==============================================================================
# INFORMAÇÕES CONTRATUAIS E HISTÓRICO COMPLETO PARA RELATÓRIO FORMAL
# ==============================================================================
@dataclass
class ContractInfo:
    """Informações do contrato de internet para relatório formal."""

    operadora: str = "WLAN SISTEMAS"
    plano: str = "PACOTE R/C SUMMER 500MB+EXITLAG"
    velocidade_down_mbps: float = 500.0  # Mbps para cálculos
    velocidade_up_mbps: float = 250.0  # Mbps para cálculos
    # ANATEL Resolução 574/2011
    percentual_medio_anatel: float = 80.0  # Média mensal mínima
    percentual_instantaneo_anatel: float = 40.0  # Instantâneo mínimo
    # Informações de contato
    telefone_operadora: str = "(91) 3182-2990"
    whatsapp_operadora: str = "(91) 98538-9877"
    email_operadora: str = "financeiro@wlansistemas.com.br"


contract_info = ContractInfo()

# Histórico completo para relatório (sem limite de tamanho)
# Armazena TODAS as medições desde o início do teste
full_ping_history: list = []  # [(timestamp, local_ms, external_ms), ...]
full_speed_history: list = []  # [(timestamp, down, up, ping, provider, servidor), ...]
test_session_start: Optional[datetime.datetime] = None


def save_prefs() -> None:
    """Persiste preferências relevantes para exportação em JSON."""
    try:
        prefs = {
            "allow_full_history_export": config.allow_full_history_export,
            "export_max_points": config.export_max_points,
        }
        os.makedirs(os.path.dirname(config.prefs_file), exist_ok=True)
        with open(config.prefs_file, "w", encoding="utf-8") as f:
            import json

            json.dump(prefs, f)
    except Exception:
        # Não falhar criticamente; apenas log em console
        try:
            console.print(f"[red]{t('stalker.warning_save_prefs')}[/]")
        except Exception:
            pass


def load_prefs() -> None:
    """Carrega preferências salvas, se o arquivo existir."""
    try:
        if os.path.exists(config.prefs_file):
            import json

            with open(config.prefs_file, "r", encoding="utf-8") as f:
                prefs = json.load(f)
                if "allow_full_history_export" in prefs:
                    config.allow_full_history_export = bool(
                        prefs["allow_full_history_export"]
                    )
                if "export_max_points" in prefs:
                    config.export_max_points = int(prefs["export_max_points"])
    except Exception:
        try:
            console.print(f"[red]{t('stalker.warning_load_prefs')}[/]")
        except Exception:
            pass


def set_allow_full_history_export(value: bool) -> None:
    """Define a flag e persiste em disco."""
    config.allow_full_history_export = bool(value)
    save_prefs()


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
            t("stalker.router_cable"),
            t("stalker.router_cable_desc"),
        )

    # Caso 2: Só gateway com timeout (crítico)
    if local_ms is None:
        return (
            t("stalker.router"),
            t("stalker.router_no_response"),
        )

    # Caso 3: Só externo com timeout
    if ext_ms is None:
        return (
            t("stalker.provider_dns"),
            t("stalker.provider_dns_desc"),
        )

    # Caso 4: Ambos acima do threshold
    local_lag = local_ms > threshold
    ext_lag = ext_ms > threshold

    if local_lag and ext_lag:
        # Se a diferença entre local e externo é pequena, provável roteador
        diff = abs(ext_ms - local_ms)
        if diff < 20:  # Menos de 20ms de diferença
            return (
                t("stalker.router"),
                t("stalker.router_overloaded", local=f"{local_ms:.0f}", ext=f"{ext_ms:.0f}"),
            )
        else:
            # Grande diferença: pode ser tanto roteador quanto provedor
            return (
                t("stalker.router_provider"),
                t("stalker.compound_lag", local=f"{local_ms:.0f}"),
            )

    # Caso 5: Só externo com lag (local ok)
    if ext_lag and not local_lag:
        return (
            t("stalker.provider_route"),
            t("stalker.external_slow", local=f"{local_ms:.0f}"),
        )

    # Caso 6: Só local com lag (raro, já que ext passa por local)
    if local_lag and not ext_lag:
        return (
            t("stalker.router_fluctuation"),
            t("stalker.check_stability"),
        )

    # Caso 7: Tudo OK, mas ainda assim quer info
    if procs:
        top_proc = procs[0][1] if procs[0][1] else t("scanner.unknown")
        return t("stalker.ok_process", process=top_proc), t("stalker.ok_stable")

    return t("stalker.ok"), t("stalker.network_stable")


# --- Entrada de Teclado ---
# Debounce: evita múltiplas leituras acidentais
_last_key_time = 0.0
_KEY_COOLDOWN = 0.3  # 300ms cooldown entre teclas


def _flush_stdin():
    """Limpa completamente o buffer de entrada do teclado."""
    if platform.system().lower() == "windows":
        while msvcrt.kbhit():
            msvcrt.getch()
    else:
        import termios
        try:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)
        except (termios.error, OSError):
            pass


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
        return f"[dim]{t('stalker.help_toggled')}[/]"
    elif key == "g":
        return prompt_change_gateway()
    elif key == "e":
        return prompt_change_external()
    elif key == "t":
        return prompt_change_threshold()
    elif key == "i":
        return prompt_change_interval()
    elif key == "x":
        return prompt_export_report()
    elif key == "p":
        config.show_ports = not config.show_ports
        status = t("stalker.ports_enabled") if config.show_ports else t("stalker.ports_disabled")
        return f"[yellow]{t('stalker.ports_panel', status=status)}[/]"
    elif key == "s":
        port_scanner_state = run_full_scan()
        return f"[green]{t('stalker.port_scan_updated', tcp=port_scanner_state.total_tcp, udp=port_scanner_state.total_udp)}[/]"
    elif key == "v":
        config.show_speed = not config.show_speed
        if config.show_speed:
            return f"[yellow]{t('stalker.speed_panel_on')}[/]"
        else:
            # Exportar relatório ao pausar velocidade
            export_msg = export_combined_report()
            return f"[yellow]{t('stalker.speed_panel_off')}[/] | {export_msg}"
    elif key == "c":
        return prompt_change_contracted_speed()
    elif key == "f":
        # Alterna a preferência de exportação completa e persiste
        new_val = not config.allow_full_history_export
        set_allow_full_history_export(new_val)
        status = t("stalker.ports_enabled") if new_val else t("stalker.ports_disabled")
        return f"[yellow]{t('stalker.export_full_toggle', status=status, path=config.prefs_file)}[/]"
    return None


def prompt_change_gateway() -> str:
    """Altera IP do gateway (cicla entre valores comuns)."""
    common_gateways = ["192.168.1.1", "192.168.0.1", "192.168.18.1", "10.0.0.1"]
    try:
        current_idx = common_gateways.index(config.gateway_ip)
        config.gateway_ip = common_gateways[(current_idx + 1) % len(common_gateways)]
    except ValueError:
        config.gateway_ip = common_gateways[0]
    return f"[yellow]{t('stalker.gateway_changed', ip=config.gateway_ip)}[/]"


def prompt_change_external() -> str:
    """Altera IP externo (cicla entre servidores DNS)."""
    dns_servers = ["8.8.8.8", "1.1.1.1", "208.67.222.222", "9.9.9.9"]
    try:
        current_idx = dns_servers.index(config.external_ip)
        config.external_ip = dns_servers[(current_idx + 1) % len(dns_servers)]
    except ValueError:
        config.external_ip = dns_servers[0]
    return f"[yellow]{t('stalker.dns_changed', ip=config.external_ip)}[/]"


def prompt_change_threshold() -> str:
    """Cicla entre valores de threshold."""
    thresholds = [50, 100, 150, 200, 300]
    try:
        current_idx = thresholds.index(config.lag_threshold_ms)
        config.lag_threshold_ms = thresholds[(current_idx + 1) % len(thresholds)]
    except ValueError:
        config.lag_threshold_ms = thresholds[0]
    return f"[yellow]{t('stalker.threshold_changed', value=config.lag_threshold_ms)}[/]"


def prompt_change_interval() -> str:
    """Cicla entre valores de intervalo."""
    intervals = [0.5, 1.0, 2.0, 5.0]
    try:
        current_idx = intervals.index(config.interval)
        config.interval = intervals[(current_idx + 1) % len(intervals)]
    except ValueError:
        config.interval = intervals[0]
    return f"[yellow]{t('stalker.interval_changed', value=config.interval)}[/]"


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
    return f"[yellow]{t('stalker.contracted_speed_changed', down=new_speed[0], up=new_speed[1])}[/]"


def prompt_export_report(simulated_choice: str | None = None) -> str:
    """Prompts the user whether to export a full history report.

    Args:
        simulated_choice: Optional string for tests: 's' (yes), 'n' (no), 'sa' (yes + sempre salvar).

    Returns:
        A status message string to be logged/displayed.
    """
    # Contagem de pontos estimada
    total_points = len(full_ping_history) if full_ping_history else len(local_stats.timestamps)
    # Mensagem de aviso
    warning = t("stalker.export_warning")

    # Usar escolha simulada (para testes)
    if simulated_choice is not None:
        choice = simulated_choice.lower()
    else:
        # Se já está marcado como permissivo, não perguntar
        if config.allow_full_history_export:
            msg = export_combined_report(full_history=True)
            return f"[cyan]{t('stalker.exporting_full_config')}[/] | {msg}"

        # Pergunta interativa simples (compatível Windows/Unix)
        try:
            if platform.system().lower() == "windows":
                print(t("stalker.export_points_prompt", points=total_points, warning=warning), end=" ")
                ch = msvcrt.getwch()
                print(ch)
                choice = ch.lower()
            else:
                print(t("stalker.export_points_prompt", points=total_points, warning=warning), end=" ")
                choice = sys.stdin.read(1).lower()
                print(choice)
        except Exception:
            choice = "n"

    if choice not in ("s", "y", "sa"):
        return f"[yellow]{t('stalker.export_cancelled')}[/]"

    # Se o usuário escolheu 'sa', persistir preferencia
    if choice == "sa":
        set_allow_full_history_export(True)

    # Confirmed: start export with full_history=True
    msg = export_combined_report(full_history=True)
    return f"[cyan]{t('stalker.exporting_full')}[/] | {msg}"


# --- Estado de Exportação em Background ---
_export_status = {"running": False, "message": None, "completed": False}
_export_lock = threading.Lock()


def _generate_combined_pdf_worker(full_history: bool = False):
    """Worker que gera o PDF formal completo em background.

    Args:
        full_history: Se True, força exportar todo o histórico (pode consumir muita memória).
    """
    global _export_status

    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs("exports", exist_ok=True)

        # Importar matplotlib e reportlab
        import matplotlib

        matplotlib.use("Agg")  # Backend não-interativo para threads
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from matplotlib.backends.backend_pdf import PdfPages

        pdf_filename = f"exports/relatorio_formal_{timestamp}.pdf"
        pdf_temp = pdf_filename + ".tmp"
        csv_ping_filename = f"exports/ping_history_{timestamp}.csv"
        csv_speed_filename = f"exports/speed_history_{timestamp}.csv"

        # Usar histórico completo ao invés do limitado
        ping_data = (
            full_ping_history
            if full_ping_history
            else [
                (ts, local, ext)
                for ts, local, ext in zip(
                    local_stats.timestamps, local_stats.history, external_stats.history
                )
            ]
        )

        # Determinar se usaremos o histórico completo
        use_full = full_history or getattr(config, "allow_full_history_export", False)

        # Evitar arquivos enormes: reduzir amostragem se o histórico for muito grande
        MAX_PTS = int(getattr(config, "export_max_points", 5000))
        if not use_full and len(ping_data) > MAX_PTS:
            step = max(1, len(ping_data) // MAX_PTS)
            ping_data = ping_data[::step]

        # Exportar CSVs primeiro (histórico completo)
        try:
            with open(csv_ping_filename, "w", encoding="utf-8") as f:
                f.write("timestamp,local_ms,external_ms,status_local,status_externo\n")
                for ts, local, ext in ping_data:
                    ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                    local_val = f"{local:.1f}" if local is not None else "TIMEOUT"
                    ext_val = f"{ext:.1f}" if ext is not None else "TIMEOUT"
                    status_local = (
                        "TIMEOUT"
                        if local is None
                        else ("ALTO" if local > config.lag_threshold_ms else "OK")
                    )
                    status_ext = (
                        "TIMEOUT"
                        if ext is None
                        else ("ALTO" if ext > config.lag_threshold_ms else "OK")
                    )
                    f.write(
                        f"{ts_str},{local_val},{ext_val},{status_local},{status_ext}\n"
                    )
        except Exception:
            pass

        # CSV de Velocidade
        tester = get_speed_tester()
        stats = tester.stats

        # Copiar históricos para evitar mutações e reduzir se muito grandes
        speed_ts = list(stats.timestamps)
        speed_down = list(stats.history_down)
        speed_up = list(stats.history_up)
        if len(speed_ts) > MAX_PTS:
            step = max(1, len(speed_ts) // MAX_PTS)
            speed_ts = speed_ts[::step]
            speed_down = speed_down[::step]
            speed_up = speed_up[::step]

        if stats.test_count > 0:
            try:
                with open(csv_speed_filename, "w", encoding="utf-8") as f:
                    f.write(
                        "timestamp,download_mbps,upload_mbps,contrato_down,contrato_up,"
                        "pct_down,pct_up,status_anatel_medio,status_anatel_instantaneo\n"
                    )
                    for ts, down, up in zip(
                        speed_ts, speed_down, speed_up
                    ):
                        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                        pct_down = (down / contract_info.velocidade_down_mbps) * 100
                        pct_up = (up / contract_info.velocidade_up_mbps) * 100
                        status_medio = (
                            "OK"
                            if pct_down >= contract_info.percentual_medio_anatel
                            and pct_up >= contract_info.percentual_medio_anatel
                            else "ABAIXO"
                        )
                        status_instant = (
                            "OK"
                            if pct_down >= contract_info.percentual_instantaneo_anatel
                            and pct_up >= contract_info.percentual_instantaneo_anatel
                            else "VIOLAÇÃO"
                        )
                        f.write(
                            f"{ts_str},{down:.2f},{up:.2f},"
                            f"{contract_info.velocidade_down_mbps},{contract_info.velocidade_up_mbps},"
                            f"{pct_down:.1f},{pct_up:.1f},{status_medio},{status_instant}\n"
                        )
            except Exception:
                pass

        # ======================================================================
        # GERAR PDF FORMAL COMPLETO - ESTILO OFICIAL ANATEL/GOV.BR
        # ======================================================================
        # Cores oficiais inspiradas no gov.br/ANATEL
        AZUL_GOV = "#071D41"  # Azul escuro gov.br
        AZUL_ANATEL = "#1351B4"  # Azul ANATEL
        AMARELO_GOV = "#FFCD07"  # Amarelo destaque
        CINZA_CLARO = "#F8F8F8"

        with PdfPages(pdf_temp) as pdf:
            # === PÁGINA 1: CAPA PROFISSIONAL ===
            fig_capa = plt.figure(figsize=(8.5, 11), facecolor="white")
            ax_capa = fig_capa.add_subplot(111)
            ax_capa.axis("off")
            ax_capa.set_xlim(0, 1)
            ax_capa.set_ylim(0, 1)

            # Header azul institucional
            rect_header = plt.Rectangle(
                (0, 0.85), 1, 0.15, facecolor=AZUL_GOV, transform=ax_capa.transAxes
            )
            ax_capa.add_patch(rect_header)

            # Linha amarela decorativa
            rect_line = plt.Rectangle(
                (0, 0.84), 1, 0.01, facecolor=AMARELO_GOV, transform=ax_capa.transAxes
            )
            ax_capa.add_patch(rect_line)

            # Título principal no header
            ax_capa.text(
                0.5,
                0.93,
                "AGÊNCIA NACIONAL DE TELECOMUNICAÇÕES",
                ha="center",
                va="center",
                fontsize=12,
                color="white",
                fontweight="bold",
                transform=ax_capa.transAxes,
            )
            ax_capa.text(
                0.5,
                0.88,
                "ANATEL",
                ha="center",
                va="center",
                fontsize=24,
                color="white",
                fontweight="bold",
                transform=ax_capa.transAxes,
            )

            # Data/hora atual
            now = datetime.datetime.now()
            data_str = now.strftime("%d/%m/%Y")
            hora_str = now.strftime("%H:%M:%S")

            # Período do teste
            if test_session_start:
                inicio_str = test_session_start.strftime("%d/%m/%Y %H:%M:%S")
            elif ping_data:
                inicio_str = ping_data[0][0].strftime("%d/%m/%Y %H:%M:%S")
            else:
                inicio_str = "N/A"
            fim_str = now.strftime("%d/%m/%Y %H:%M:%S")

            # Título do documento
            ax_capa.text(
                0.5,
                0.72,
                "RELATÓRIO TÉCNICO DE AUDITORIA",
                ha="center",
                va="center",
                fontsize=18,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_capa.transAxes,
            )
            ax_capa.text(
                0.5,
                0.67,
                "Qualidade do Serviço de Comunicação Multimídia",
                ha="center",
                va="center",
                fontsize=14,
                color=AZUL_ANATEL,
                transform=ax_capa.transAxes,
            )

            # Box de informações contratuais
            rect_info = plt.Rectangle(
                (0.08, 0.35),
                0.84,
                0.25,
                facecolor=CINZA_CLARO,
                transform=ax_capa.transAxes,
                linewidth=2,
                edgecolor=AZUL_ANATEL,
            )
            ax_capa.add_patch(rect_info)

            ax_capa.text(
                0.5,
                0.57,
                "DADOS DA PRESTADORA E CONTRATO",
                ha="center",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_capa.transAxes,
            )

            info_lines = [
                f"Prestadora: {contract_info.operadora}",
                f"Plano: {contract_info.plano}",
                f"Velocidade Contratada: {contract_info.velocidade_down_mbps:.0f} Mbps (download) / {contract_info.velocidade_up_mbps:.0f} Mbps (upload)",
                "",
                f"Período de Análise: {inicio_str} até {fim_str}",
                f"Total de Medições: {len(ping_data)} (ping) | {stats.test_count} (velocidade)",
            ]

            for i, line in enumerate(info_lines):
                ax_capa.text(
                    0.5,
                    0.52 - i * 0.03,
                    line,
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="#333333",
                    transform=ax_capa.transAxes,
                )

            # Referências legais
            ax_capa.text(
                0.5,
                0.25,
                "FUNDAMENTAÇÃO LEGAL",
                ha="center",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_capa.transAxes,
            )

            legal_lines = [
                "• Resolução nº 574/2011 da ANATEL",
                "• RQUAL - Regulamento de Qualidade dos Serviços de Telecomunicações",
                "• Resolução nº 777/2025 - Regulamento Geral de Direitos do Consumidor",
                "• Lei nº 8.078/1990 - Código de Defesa do Consumidor",
            ]

            for i, line in enumerate(legal_lines):
                ax_capa.text(
                    0.5,
                    0.21 - i * 0.025,
                    line,
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#555555",
                    transform=ax_capa.transAxes,
                )

            # Footer
            rect_footer = plt.Rectangle(
                (0, 0), 1, 0.06, facecolor=AZUL_GOV, transform=ax_capa.transAxes
            )
            ax_capa.add_patch(rect_footer)

            ax_capa.text(
                0.5,
                0.03,
                f"Gerado em: {data_str} às {hora_str} | Conforme metodologia ANATEL Qualidade",
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                transform=ax_capa.transAxes,
            )

            pdf.savefig(fig_capa, dpi=150, facecolor="white")
            plt.close(fig_capa)

            # === PÁGINA 2: METODOLOGIA - ESTILO PROFISSIONAL ===
            fig_met = plt.figure(figsize=(8.5, 11), facecolor="white")
            ax_met = fig_met.add_subplot(111)
            ax_met.axis("off")
            ax_met.set_xlim(0, 1)
            ax_met.set_ylim(0, 1)

            # Header azul
            rect_header = plt.Rectangle(
                (0, 0.92), 1, 0.08, facecolor=AZUL_GOV, transform=ax_met.transAxes
            )
            ax_met.add_patch(rect_header)
            ax_met.text(
                0.5,
                0.96,
                "METODOLOGIA DE AFERIÇÃO",
                ha="center",
                va="center",
                fontsize=14,
                color="white",
                fontweight="bold",
                transform=ax_met.transAxes,
            )

            # Seção 1: Base Legal
            ax_met.text(
                0.08,
                0.86,
                "1. BASE LEGAL",
                ha="left",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_met.transAxes,
            )

            base_legal = [
                "Conforme a Resolução nº 574/2011 da ANATEL e o RQUAL,",
                "as prestadoras devem garantir:",
                "",
                f"• Velocidade MÉDIA mensal: mínimo de {contract_info.percentual_medio_anatel:.0f}% do contratado",
                f"• Velocidade INSTANTÂNEA: mínimo de {contract_info.percentual_instantaneo_anatel:.0f}% em cada medição",
            ]
            for i, line in enumerate(base_legal):
                ax_met.text(
                    0.08,
                    0.82 - i * 0.025,
                    line,
                    ha="left",
                    va="center",
                    fontsize=9,
                    color="#333333",
                    transform=ax_met.transAxes,
                )

            # Seção 2: Procedimento
            ax_met.text(
                0.08,
                0.66,
                "2. PROCEDIMENTO DE TESTE",
                ha="left",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_met.transAxes,
            )

            procedimento = [
                "Para que a aferição seja válida conforme regulamentação:",
                "",
                "• Equipamento conectado via cabo de rede (LAN)",
                "• Conexão direta na porta LAN da ONU/Roteador",
                "• Testes via Wi-Fi NÃO são considerados válidos",
            ]
            for i, line in enumerate(procedimento):
                ax_met.text(
                    0.08,
                    0.62 - i * 0.025,
                    line,
                    ha="left",
                    va="center",
                    fontsize=9,
                    color="#333333",
                    transform=ax_met.transAxes,
                )

            # Seção 3: Parâmetros
            ax_met.text(
                0.08,
                0.46,
                "3. PARÂMETROS DE ANÁLISE",
                ha="left",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_met.transAxes,
            )

            # Box de parâmetros
            rect_params = plt.Rectangle(
                (0.08, 0.28),
                0.84,
                0.16,
                facecolor=CINZA_CLARO,
                transform=ax_met.transAxes,
                linewidth=1,
                edgecolor=AZUL_ANATEL,
            )
            ax_met.add_patch(rect_params)

            params = [
                f"Velocidade Contratada: {contract_info.velocidade_down_mbps:.0f} Mbps (↓) / {contract_info.velocidade_up_mbps:.0f} Mbps (↑)",
                f"Mínimo 80%: {contract_info.velocidade_down_mbps * 0.8:.0f} Mbps (↓) / {contract_info.velocidade_up_mbps * 0.8:.0f} Mbps (↑)",
                f"Mínimo 40%: {contract_info.velocidade_down_mbps * 0.4:.0f} Mbps (↓) / {contract_info.velocidade_up_mbps * 0.4:.0f} Mbps (↑)",
            ]
            for i, line in enumerate(params):
                ax_met.text(
                    0.5,
                    0.40 - i * 0.04,
                    line,
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="#333333",
                    transform=ax_met.transAxes,
                )

            # Seção 4: Pontos de Teste
            ax_met.text(
                0.08,
                0.22,
                "4. PONTOS DE TESTE",
                ha="left",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_met.transAxes,
            )

            pontos = [
                f"Gateway Local: {config.gateway_ip}",
                f"Servidor Externo: {config.external_ip}",
                f"Limite de Latência: {config.lag_threshold_ms} ms",
            ]
            for i, line in enumerate(pontos):
                ax_met.text(
                    0.08,
                    0.18 - i * 0.025,
                    line,
                    ha="left",
                    va="center",
                    fontsize=9,
                    color="#333333",
                    transform=ax_met.transAxes,
                )

            # Footer
            rect_footer = plt.Rectangle(
                (0, 0), 1, 0.04, facecolor=AZUL_GOV, transform=ax_met.transAxes
            )
            ax_met.add_patch(rect_footer)
            ax_met.text(
                0.5,
                0.02,
                "ANATEL - Agência Nacional de Telecomunicações",
                ha="center",
                va="center",
                fontsize=7,
                color="white",
                transform=ax_met.transAxes,
            )

            pdf.savefig(fig_met, dpi=150, facecolor="white")
            plt.close(fig_met)

            # === PÁGINAS 3+: TABELA DE MEDIÇÕES DE PING (ESTILO PROFISSIONAL) ===
            if ping_data:
                rows_per_page = 35  # Reduzido para caber header/footer
                total_pages = (len(ping_data) + rows_per_page - 1) // rows_per_page

                for page_num in range(total_pages):
                    start_idx = page_num * rows_per_page
                    end_idx = min(start_idx + rows_per_page, len(ping_data))
                    page_data = ping_data[start_idx:end_idx]

                    fig_ping = plt.figure(figsize=(8.5, 11), facecolor="white")
                    ax_ping = fig_ping.add_subplot(111)
                    ax_ping.axis("off")
                    ax_ping.set_xlim(0, 1)
                    ax_ping.set_ylim(0, 1)

                    # Header institucional
                    rect_header = plt.Rectangle(
                        (0, 0.92),
                        1,
                        0.08,
                        facecolor=AZUL_GOV,
                        transform=ax_ping.transAxes,
                    )
                    ax_ping.add_patch(rect_header)
                    ax_ping.text(
                        0.5,
                        0.96,
                        f"REGISTRO DE MEDIÇÕES DE PING - Página {page_num + 1}/{total_pages}",
                        ha="center",
                        va="center",
                        fontsize=12,
                        color="white",
                        fontweight="bold",
                        transform=ax_ping.transAxes,
                    )

                    # Cabeçalho da tabela (fundo azul)
                    rect_table_header = plt.Rectangle(
                        (0.02, 0.86),
                        0.96,
                        0.04,
                        color=AZUL_ANATEL,
                        transform=ax_ping.transAxes,
                    )
                    ax_ping.add_patch(rect_table_header)
                    ax_ping.text(
                        0.04,
                        0.88,
                        "#",
                        ha="left",
                        va="center",
                        fontsize=8,
                        color="white",
                        fontweight="bold",
                        transform=ax_ping.transAxes,
                    )
                    ax_ping.text(
                        0.12,
                        0.88,
                        "Timestamp",
                        ha="left",
                        va="center",
                        fontsize=8,
                        color="white",
                        fontweight="bold",
                        transform=ax_ping.transAxes,
                    )
                    ax_ping.text(
                        0.45,
                        0.88,
                        "Gateway",
                        ha="left",
                        va="center",
                        fontsize=8,
                        color="white",
                        fontweight="bold",
                        transform=ax_ping.transAxes,
                    )
                    ax_ping.text(
                        0.62,
                        0.88,
                        "Externo",
                        ha="left",
                        va="center",
                        fontsize=8,
                        color="white",
                        fontweight="bold",
                        transform=ax_ping.transAxes,
                    )
                    ax_ping.text(
                        0.80,
                        0.88,
                        "Status",
                        ha="left",
                        va="center",
                        fontsize=8,
                        color="white",
                        fontweight="bold",
                        transform=ax_ping.transAxes,
                    )

                    # Linhas da tabela com zebra striping
                    row_height = 0.022
                    for row_idx, (ts, local, ext) in enumerate(page_data):
                        y_pos = 0.84 - row_idx * row_height
                        global_idx = start_idx + row_idx + 1

                        # Zebra striping
                        if row_idx % 2 == 0:
                            rect_row = plt.Rectangle(
                                (0.02, y_pos - row_height / 2),
                                0.96,
                                row_height,
                                color=CINZA_CLARO,
                                transform=ax_ping.transAxes,
                            )
                            ax_ping.add_patch(rect_row)

                        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                        local_str = f"{local:.1f}ms" if local is not None else "TIMEOUT"
                        ext_str = f"{ext:.1f}ms" if ext is not None else "TIMEOUT"

                        if local is None or ext is None:
                            status = "CRÍTICO"
                            status_color = "#DC3545"
                        elif (
                            local > config.lag_threshold_ms
                            or ext > config.lag_threshold_ms
                        ):
                            status = "ALTO"
                            status_color = "#FFC107"
                        else:
                            status = "OK"
                            status_color = "#28A745"

                        ax_ping.text(
                            0.04,
                            y_pos,
                            str(global_idx),
                            ha="left",
                            va="center",
                            fontsize=7,
                            color="#333",
                            transform=ax_ping.transAxes,
                        )
                        ax_ping.text(
                            0.12,
                            y_pos,
                            ts_str,
                            ha="left",
                            va="center",
                            fontsize=7,
                            color="#333",
                            transform=ax_ping.transAxes,
                        )
                        ax_ping.text(
                            0.45,
                            y_pos,
                            local_str,
                            ha="left",
                            va="center",
                            fontsize=7,
                            color="#333",
                            transform=ax_ping.transAxes,
                        )
                        ax_ping.text(
                            0.62,
                            y_pos,
                            ext_str,
                            ha="left",
                            va="center",
                            fontsize=7,
                            color="#333",
                            transform=ax_ping.transAxes,
                        )
                        ax_ping.text(
                            0.80,
                            y_pos,
                            status,
                            ha="left",
                            va="center",
                            fontsize=7,
                            color=status_color,
                            fontweight="bold",
                            transform=ax_ping.transAxes,
                        )

                    # Footer institucional
                    rect_footer = plt.Rectangle(
                        (0, 0), 1, 0.04, facecolor=AZUL_GOV, transform=ax_ping.transAxes
                    )
                    ax_ping.add_patch(rect_footer)
                    ax_ping.text(
                        0.5,
                        0.02,
                        "ANATEL - Agência Nacional de Telecomunicações",
                        ha="center",
                        va="center",
                        fontsize=7,
                        color="white",
                        transform=ax_ping.transAxes,
                    )

                    pdf.savefig(fig_ping, dpi=150, facecolor="white")
                    plt.close(fig_ping)

            # === GRÁFICO DE PING (ESTILO INSTITUCIONAL) ===
            fig1 = plt.figure(figsize=(14, 8), facecolor="white")
            ax1 = fig1.add_subplot(111)

            times_ping = (
                [p[0] for p in ping_data] if ping_data else list(local_stats.timestamps)
            )
            local_valid = (
                [p[1] for p in ping_data] if ping_data else list(local_stats.history)
            )
            ext_valid = (
                [p[2] for p in ping_data] if ping_data else list(external_stats.history)
            )

            if times_ping:
                # Cores institucionais
                ax1.plot(
                    times_ping,
                    local_valid,
                    label=f"Gateway ({config.gateway_ip})",
                    color=AZUL_ANATEL,
                    linewidth=2,
                    marker="o",
                    markersize=3,
                )
                ax1.plot(
                    times_ping,
                    ext_valid,
                    label=f"Externo ({config.external_ip})",
                    color=AMARELO_GOV,
                    linewidth=2,
                    marker="s",
                    markersize=3,
                )
                ax1.axhline(
                    y=config.lag_threshold_ms,
                    color="#DC3545",
                    linestyle="--",
                    linewidth=2,
                    label=f"Limite ({config.lag_threshold_ms}ms)",
                )
                ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
                plt.xticks(rotation=45)

                start_str = times_ping[0].strftime("%Y-%m-%d %H:%M:%S")
                end_str = times_ping[-1].strftime("%H:%M:%S")
                ax1.set_title(
                    f"Gráfico de Latência (Ping)\n{start_str} → {end_str}",
                    fontsize=14,
                    fontweight="bold",
                    color=AZUL_GOV,
                )

                # Estatísticas
                valid_local = [x for x in local_valid if x is not None]
                valid_ext = [x for x in ext_valid if x is not None]
                if valid_local and valid_ext:
                    stats_text = (
                        f"Gateway - Min: {min(valid_local):.1f}ms | "
                        f"Máx: {max(valid_local):.1f}ms | Méd: {sum(valid_local) / len(valid_local):.1f}ms\n"
                        f"Externo - Min: {min(valid_ext):.1f}ms | "
                        f"Máx: {max(valid_ext):.1f}ms | Méd: {sum(valid_ext) / len(valid_ext):.1f}ms"
                    )
                    ax1.text(
                        0.02,
                        0.98,
                        stats_text,
                        transform=ax1.transAxes,
                        fontsize=9,
                        verticalalignment="top",
                        bbox=dict(
                            boxstyle="round",
                            facecolor=CINZA_CLARO,
                            edgecolor=AZUL_ANATEL,
                            alpha=0.9,
                        ),
                    )
            else:
                ax1.text(
                    0.5, 0.5, "Sem dados de ping disponíveis", ha="center", va="center"
                )

            ax1.set_xlabel("Tempo", fontweight="bold")
            ax1.set_ylabel("Ping (ms)", fontweight="bold")
            ax1.legend(loc="upper right")
            ax1.grid(True, alpha=0.3)
            ax1.set_facecolor("#FAFAFA")

            plt.tight_layout()
            pdf.savefig(fig1, dpi=150, facecolor="white")
            plt.close(fig1)

            # === TABELA DE TESTES DE VELOCIDADE (ESTILO PROFISSIONAL) ===
            if stats.test_count > 0:
                fig_speed = plt.figure(figsize=(8.5, 11), facecolor="white")
                ax_speed = fig_speed.add_subplot(111)
                ax_speed.axis("off")
                ax_speed.set_xlim(0, 1)
                ax_speed.set_ylim(0, 1)

                # Header institucional
                rect_header = plt.Rectangle(
                    (0, 0.92), 1, 0.08, facecolor=AZUL_GOV, transform=ax_speed.transAxes
                )
                ax_speed.add_patch(rect_header)
                ax_speed.text(
                    0.5,
                    0.96,
                    f"REGISTRO DE TESTES DE VELOCIDADE - {stats.test_count} testes",
                    ha="center",
                    va="center",
                    fontsize=12,
                    color="white",
                    fontweight="bold",
                    transform=ax_speed.transAxes,
                )

                # Cabeçalho da tabela (reorganizado com Provedor)
                rect_table_header = plt.Rectangle(
                    (0.02, 0.86),
                    0.96,
                    0.04,
                    color=AZUL_ANATEL,
                    transform=ax_speed.transAxes,
                )
                ax_speed.add_patch(rect_table_header)

                # Colunas: #, Timestamp, Provedor, Down, Up, Status
                col_positions = [0.03, 0.08, 0.28, 0.46, 0.60, 0.74, 0.88]
                headers = [
                    "#",
                    "Horário",
                    "Provedor",
                    "Download",
                    "Upload",
                    "%Vel",
                    "Status",
                ]
                for pos, header in zip(col_positions, headers):
                    ax_speed.text(
                        pos,
                        0.88,
                        header,
                        ha="left",
                        va="center",
                        fontsize=7,
                        color="white",
                        fontweight="bold",
                        transform=ax_speed.transAxes,
                    )

                # Obter lista de provedores (se disponível)
                providers = (
                    list(stats.history_providers)
                    if hasattr(stats, "history_providers")
                    else []
                )

                # Linhas da tabela
                row_height = 0.025
                for row_idx, (ts, down, up) in enumerate(
                    zip(stats.timestamps, stats.history_down, stats.history_up)
                ):
                    y_pos = 0.84 - row_idx * row_height

                    # Zebra striping
                    if row_idx % 2 == 0:
                        rect_row = plt.Rectangle(
                            (0.02, y_pos - row_height / 2),
                            0.96,
                            row_height,
                            color=CINZA_CLARO,
                            transform=ax_speed.transAxes,
                        )
                        ax_speed.add_patch(rect_row)

                    ts_str = ts.strftime("%H:%M:%S")
                    pct_down = (down / contract_info.velocidade_down_mbps) * 100
                    pct_up = (up / contract_info.velocidade_up_mbps) * 100
                    pct_avg = (pct_down + pct_up) / 2

                    # Obter provedor
                    provider_name = (
                        providers[row_idx] if row_idx < len(providers) else "—"
                    )
                    # Abreviar nome do provedor se for muito longo
                    if len(provider_name) > 12:
                        provider_name = provider_name[:11] + "…"

                    if pct_down < 40 or pct_up < 40:
                        status = "VIOLAÇÃO"
                        status_color = "#DC3545"
                    elif pct_down < 80 or pct_up < 80:
                        status = "ABAIXO"
                        status_color = "#FFC107"
                    else:
                        status = "CONFORME"
                        status_color = "#28A745"

                    # Dados da linha
                    ax_speed.text(
                        col_positions[0],
                        y_pos,
                        str(row_idx + 1),
                        ha="left",
                        va="center",
                        fontsize=6,
                        color="#333",
                        transform=ax_speed.transAxes,
                    )
                    ax_speed.text(
                        col_positions[1],
                        y_pos,
                        ts_str,
                        ha="left",
                        va="center",
                        fontsize=6,
                        color="#333",
                        transform=ax_speed.transAxes,
                    )
                    ax_speed.text(
                        col_positions[2],
                        y_pos,
                        provider_name,
                        ha="left",
                        va="center",
                        fontsize=6,
                        color=AZUL_ANATEL,
                        transform=ax_speed.transAxes,
                    )
                    ax_speed.text(
                        col_positions[3],
                        y_pos,
                        f"{down:.0f}Mbps",
                        ha="left",
                        va="center",
                        fontsize=6,
                        color="#333",
                        transform=ax_speed.transAxes,
                    )
                    ax_speed.text(
                        col_positions[4],
                        y_pos,
                        f"{up:.0f}Mbps",
                        ha="left",
                        va="center",
                        fontsize=6,
                        color="#333",
                        transform=ax_speed.transAxes,
                    )
                    ax_speed.text(
                        col_positions[5],
                        y_pos,
                        f"{pct_avg:.0f}%",
                        ha="left",
                        va="center",
                        fontsize=6,
                        color="#333",
                        transform=ax_speed.transAxes,
                    )
                    ax_speed.text(
                        col_positions[6],
                        y_pos,
                        status,
                        ha="left",
                        va="center",
                        fontsize=6,
                        color=status_color,
                        fontweight="bold",
                        transform=ax_speed.transAxes,
                    )

                # Footer institucional
                rect_footer = plt.Rectangle(
                    (0, 0), 1, 0.04, facecolor=AZUL_GOV, transform=ax_speed.transAxes
                )
                ax_speed.add_patch(rect_footer)
                ax_speed.text(
                    0.5,
                    0.02,
                    "ANATEL - Agência Nacional de Telecomunicações",
                    ha="center",
                    va="center",
                    fontsize=7,
                    color="white",
                    transform=ax_speed.transAxes,
                )

                pdf.savefig(fig_speed, dpi=150, facecolor="white")
                plt.close(fig_speed)

                # Gráfico de velocidade (ESTILO INSTITUCIONAL)
                fig2 = plt.figure(figsize=(14, 10), facecolor="white")
                ax2 = fig2.add_subplot(211)
                ax3 = fig2.add_subplot(212)

                times_speed = list(stats.timestamps)
                down_vals = list(stats.history_down)
                up_vals = list(stats.history_up)

                avg_down = sum(down_vals) / len(down_vals) if down_vals else 0
                avg_up = sum(up_vals) / len(up_vals) if up_vals else 0
                min_down = min(down_vals) if down_vals else 0
                max_down = max(down_vals) if down_vals else 0
                min_up = min(up_vals) if up_vals else 0
                max_up = max(up_vals) if up_vals else 0

                # Gráfico de Download (cores institucionais)
                ax2.plot(
                    times_speed,
                    down_vals,
                    label="Download",
                    color=AZUL_ANATEL,
                    linewidth=2,
                    marker="o",
                    markersize=5,
                )
                ax2.axhline(
                    y=contract_info.velocidade_down_mbps,
                    color="#28A745",
                    linestyle="--",
                    linewidth=2,
                    label=f"Contrato ({contract_info.velocidade_down_mbps:.0f} Mbps)",
                )
                ax2.axhline(
                    y=contract_info.velocidade_down_mbps * 0.8,
                    color=AMARELO_GOV,
                    linestyle=":",
                    linewidth=2,
                    label="Mínimo 80%",
                )
                ax2.axhline(
                    y=contract_info.velocidade_down_mbps * 0.4,
                    color="#DC3545",
                    linestyle=":",
                    linewidth=2,
                    label="Mínimo 40%",
                )
                ax2.set_ylabel("Download (Mbps)", fontweight="bold")
                ax2.legend(loc="upper right")
                ax2.grid(True, alpha=0.3)
                ax2.set_facecolor("#FAFAFA")
                ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

                # Gráfico de Upload (cores institucionais)
                ax3.plot(
                    times_speed,
                    up_vals,
                    label="Upload",
                    color=AMARELO_GOV,
                    linewidth=2,
                    marker="s",
                    markersize=5,
                )
                ax3.axhline(
                    y=contract_info.velocidade_up_mbps,
                    color="#28A745",
                    linestyle="--",
                    linewidth=2,
                    label=f"Contrato ({contract_info.velocidade_up_mbps:.0f} Mbps)",
                )
                ax3.axhline(
                    y=contract_info.velocidade_up_mbps * 0.8,
                    color=AMARELO_GOV,
                    linestyle=":",
                    linewidth=2,
                    label="Mínimo 80%",
                )
                ax3.axhline(
                    y=contract_info.velocidade_up_mbps * 0.4,
                    color="#DC3545",
                    linestyle=":",
                    linewidth=2,
                    label="Mínimo 40%",
                )
                ax3.set_xlabel("Tempo", fontweight="bold")
                ax3.set_ylabel("Upload (Mbps)", fontweight="bold")
                ax3.legend(loc="upper right")
                ax3.grid(True, alpha=0.3)
                ax3.set_facecolor("#FAFAFA")
                ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

                plt.suptitle(
                    f"Gráfico de Velocidade - {stats.test_count} testes\n"
                    f"Download: Média {avg_down:.1f} Mbps (Min: {min_down:.1f}, Max: {max_down:.1f})\n"
                    f"Upload: Média {avg_up:.1f} Mbps (Min: {min_up:.1f}, Max: {max_up:.1f})",
                    fontsize=10,
                    fontweight="bold",
                    color=AZUL_GOV,
                )

                plt.tight_layout()
                pdf.savefig(fig2, dpi=150, facecolor="white")
                plt.close(fig2)

            # === PÁGINA: ANÁLISE E DIAGNÓSTICO (ESTILO PROFISSIONAL) ===
            fig_analise = plt.figure(figsize=(8.5, 11), facecolor="white")
            ax_analise = fig_analise.add_subplot(111)
            ax_analise.axis("off")
            ax_analise.set_xlim(0, 1)
            ax_analise.set_ylim(0, 1)

            # Header institucional
            rect_header = plt.Rectangle(
                (0, 0.92), 1, 0.08, facecolor=AZUL_GOV, transform=ax_analise.transAxes
            )
            ax_analise.add_patch(rect_header)
            ax_analise.text(
                0.5,
                0.96,
                "ANÁLISE E DIAGNÓSTICO",
                ha="center",
                va="center",
                fontsize=14,
                color="white",
                fontweight="bold",
                transform=ax_analise.transAxes,
            )

            # Calcular estatísticas gerais
            valid_local = (
                [p[1] for p in ping_data if p[1] is not None] if ping_data else []
            )
            valid_ext = (
                [p[2] for p in ping_data if p[2] is not None] if ping_data else []
            )
            timeouts = (
                len([p for p in ping_data if p[1] is None or p[2] is None])
                if ping_data
                else 0
            )
            high_latency = (
                len(
                    [
                        p
                        for p in ping_data
                        if (p[1] and p[1] > config.lag_threshold_ms)
                        or (p[2] and p[2] > config.lag_threshold_ms)
                    ]
                )
                if ping_data
                else 0
            )

            # Estatísticas de velocidade
            if stats.test_count > 0:
                avg_down = sum(stats.history_down) / len(stats.history_down)
                avg_up = sum(stats.history_up) / len(stats.history_up)
                pct_avg_down = (avg_down / contract_info.velocidade_down_mbps) * 100
                pct_avg_up = (avg_up / contract_info.velocidade_up_mbps) * 100
                conclusao_down = "CONFORME" if pct_avg_down >= 80 else "NAO CONFORME"
                conclusao_up = "CONFORME" if pct_avg_up >= 80 else "NAO CONFORME"
            else:
                avg_down = avg_up = pct_avg_down = pct_avg_up = 0
                conclusao_down = conclusao_up = "SEM DADOS"

            # Seção 1: Latência
            ax_analise.text(
                0.08,
                0.86,
                "1. ESTATISTICAS DE LATENCIA (PING)",
                ha="left",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_analise.transAxes,
            )

            if valid_local and valid_ext:
                latencia_lines = [
                    f"Total de Medições: {len(ping_data)}",
                    f"Timeouts: {timeouts} ({(timeouts / len(ping_data) * 100) if ping_data else 0:.1f}%)",
                    f"Alta Latência (>{config.lag_threshold_ms}ms): {high_latency}",
                    "",
                    f"Gateway ({config.gateway_ip}): Min {min(valid_local):.1f}ms / Max {max(valid_local):.1f}ms / Med {sum(valid_local) / len(valid_local):.1f}ms",
                    f"Externo ({config.external_ip}): Min {min(valid_ext):.1f}ms / Max {max(valid_ext):.1f}ms / Med {sum(valid_ext) / len(valid_ext):.1f}ms",
                ]
            else:
                latencia_lines = ["Dados insuficientes para análise de latência"]

            for i, line in enumerate(latencia_lines):
                ax_analise.text(
                    0.08,
                    0.82 - i * 0.03,
                    line,
                    ha="left",
                    va="center",
                    fontsize=9,
                    color="#333",
                    transform=ax_analise.transAxes,
                )

            # Seção 2: Velocidade
            ax_analise.text(
                0.08,
                0.60,
                "2. ESTATISTICAS DE VELOCIDADE",
                ha="left",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_analise.transAxes,
            )

            velocidade_lines = [
                f"Total de Testes: {stats.test_count}",
                "",
                f"Download: Média {avg_down:.1f} Mbps ({pct_avg_down:.1f}% do contratado) - {conclusao_down}",
                f"Upload: Média {avg_up:.1f} Mbps ({pct_avg_up:.1f}% do contratado) - {conclusao_up}",
            ]
            for i, line in enumerate(velocidade_lines):
                ax_analise.text(
                    0.08,
                    0.56 - i * 0.03,
                    line,
                    ha="left",
                    va="center",
                    fontsize=9,
                    color="#333",
                    transform=ax_analise.transAxes,
                )

            # Seção 3: Conclusão (box destacado)
            ax_analise.text(
                0.08,
                0.38,
                "3. CONCLUSAO FINAL",
                ha="left",
                va="center",
                fontsize=11,
                color=AZUL_GOV,
                fontweight="bold",
                transform=ax_analise.transAxes,
            )

            if stats.test_count > 0 and pct_avg_down >= 80 and pct_avg_up >= 80:
                conclusao_cor = "#28A745"  # Verde
                conclusao_texto = "SERVIÇO CONFORME"
                conclusao_detalhe = (
                    "A velocidade média está dentro dos parâmetros ANATEL (mín 80%)."
                )
            elif stats.test_count > 0:
                conclusao_cor = "#DC3545"  # Vermelho
                conclusao_texto = "SERVIÇO NÃO CONFORME"
                conclusao_detalhe = (
                    "A velocidade média está ABAIXO dos parâmetros ANATEL (mín 80%)."
                )
            else:
                conclusao_cor = "#FFC107"  # Amarelo
                conclusao_texto = "DADOS INSUFICIENTES"
                conclusao_detalhe = "Não há dados suficientes para conclusão."

            # Box de conclusão
            rect_conclusao = plt.Rectangle(
                (0.08, 0.22),
                0.84,
                0.12,
                facecolor=CINZA_CLARO,
                transform=ax_analise.transAxes,
                linewidth=2,
                edgecolor=conclusao_cor,
            )
            ax_analise.add_patch(rect_conclusao)
            ax_analise.text(
                0.5,
                0.30,
                conclusao_texto,
                ha="center",
                va="center",
                fontsize=14,
                color=conclusao_cor,
                fontweight="bold",
                transform=ax_analise.transAxes,
            )
            ax_analise.text(
                0.5,
                0.25,
                conclusao_detalhe,
                ha="center",
                va="center",
                fontsize=9,
                color="#333",
                transform=ax_analise.transAxes,
            )

            # Footer institucional
            rect_footer = plt.Rectangle(
                (0, 0), 1, 0.04, facecolor=AZUL_GOV, transform=ax_analise.transAxes
            )
            ax_analise.add_patch(rect_footer)
            ax_analise.text(
                0.5,
                0.02,
                "ANATEL - Agencia Nacional de Telecomunicacoes",
                ha="center",
                va="center",
                fontsize=7,
                color="white",
                transform=ax_analise.transAxes,
            )

            pdf.savefig(fig_analise, dpi=150, facecolor="white")
            plt.close(fig_analise)

        # Verificar se o arquivo temporário foi gerado corretamente
        if not os.path.exists(pdf_temp) or os.path.getsize(pdf_temp) == 0:
            # Remover temporários se existirem e falhar para disparar o handler
            try:
                if os.path.exists(pdf_temp):
                    os.remove(pdf_temp)
            except Exception:
                pass
            raise RuntimeError("Arquivo PDF gerado inválido/zerado")

        # Agora criar página de assinaturas com campos editáveis usando reportlab
        try:
            from reportlab.pdfgen import canvas as rl_canvas
            from reportlab.lib.pagesizes import letter
            from reportlab.lib.colors import black, lightgrey
            from PyPDF2 import PdfReader, PdfWriter

            # Criar PDF temporário com formulário
            form_pdf_path = f"exports/temp_form_{timestamp}.pdf"
            c = rl_canvas.Canvas(form_pdf_path, pagesize=letter)
            width, height = letter  # 612 x 792 points

            # Título
            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(width / 2, height - 50, "TERMO DE VERIFICAÇÃO")

            # Linha decorativa
            c.setStrokeColor(black)
            c.setLineWidth(2)
            c.line(50, height - 70, width - 50, height - 70)

            # Texto de declaração
            c.setFont("Helvetica", 10)
            c.drawCentredString(
                width / 2,
                height - 100,
                "Declaro que presenciei a realização dos testes de velocidade e latência",
            )
            c.drawCentredString(
                width / 2,
                height - 115,
                "descritos neste relatório, realizados conforme procedimento ANATEL.",
            )

            # Seção Cliente
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 160, "CLIENTE / CONTRATANTE")
            c.line(50, height - 165, 250, height - 165)

            # Campos editáveis do Cliente
            c.setFont("Helvetica", 10)
            y_pos = height - 200

            c.drawString(50, y_pos, "Nome:")
            c.acroForm.textfield(
                name="cliente_nome",
                x=100,
                y=y_pos - 5,
                width=350,
                height=20,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
            )

            y_pos -= 35
            c.drawString(50, y_pos, "CPF/CNPJ:")
            c.acroForm.textfield(
                name="cliente_cpf",
                x=120,
                y=y_pos - 5,
                width=200,
                height=20,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
            )

            y_pos -= 35
            c.drawString(50, y_pos, "Data:")
            c.acroForm.textfield(
                name="cliente_data",
                x=100,
                y=y_pos - 5,
                width=100,
                height=20,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
                value=datetime.datetime.now().strftime("%d/%m/%Y"),
            )

            y_pos -= 50
            c.drawString(50, y_pos, "Assinatura: _____________________________________")

            # Seção Técnico
            y_pos -= 60
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y_pos, "TÉCNICO RESPONSÁVEL")
            c.line(50, y_pos - 5, 250, y_pos - 5)

            c.setFont("Helvetica", 10)
            y_pos -= 40

            c.drawString(50, y_pos, "Nome:")
            c.acroForm.textfield(
                name="tecnico_nome",
                x=100,
                y=y_pos - 5,
                width=350,
                height=20,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
            )

            y_pos -= 35
            c.drawString(50, y_pos, "CPF:")
            c.acroForm.textfield(
                name="tecnico_cpf",
                x=100,
                y=y_pos - 5,
                width=150,
                height=20,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
            )

            y_pos -= 35
            c.drawString(50, y_pos, "Registro/Matrícula:")
            c.acroForm.textfield(
                name="tecnico_registro",
                x=150,
                y=y_pos - 5,
                width=150,
                height=20,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
            )

            y_pos -= 35
            c.drawString(50, y_pos, "Data:")
            c.acroForm.textfield(
                name="tecnico_data",
                x=100,
                y=y_pos - 5,
                width=100,
                height=20,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
                value=datetime.datetime.now().strftime("%d/%m/%Y"),
            )

            y_pos -= 50
            c.drawString(50, y_pos, "Assinatura: _____________________________________")

            # Seção Observações
            y_pos -= 60
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y_pos, "OBSERVAÇÕES")
            c.line(50, y_pos - 5, 150, y_pos - 5)

            c.setFont("Helvetica", 10)
            y_pos -= 30
            c.acroForm.textfield(
                name="observacoes",
                x=50,
                y=y_pos - 60,
                width=500,
                height=70,
                borderWidth=1,
                borderColor=black,
                fillColor=lightgrey,
                textColor=black,
                fontSize=10,
            )

            # Rodapé com informações da operadora
            c.setFont("Helvetica", 8)
            c.drawCentredString(
                width / 2,
                50,
                f"Operadora: {contract_info.operadora} | Tel: {contract_info.telefone_operadora} | WhatsApp: {contract_info.whatsapp_operadora}",
            )
            c.drawCentredString(
                width / 2, 38, f"E-mail: {contract_info.email_operadora}"
            )

            c.save()

            # Mesclar PDFs: relatório + formulário de assinaturas
            reader_main = PdfReader(pdf_temp)
            reader_form = PdfReader(form_pdf_path)
            writer = PdfWriter()

            # Adicionar todas as páginas do relatório principal
            for page in reader_main.pages:
                writer.add_page(page)

            # Adicionar página de formulário
            for page in reader_form.pages:
                writer.add_page(page)

            # Salvar PDF final em arquivo temporário
            final_pdf_temp = pdf_temp.replace(".pdf", "_com_assinaturas.pdf.tmp")
            with open(final_pdf_temp, "wb") as f:
                writer.write(f)

            # Limpar temporários e mover arquivo final de forma atômica
            try:
                if os.path.exists(form_pdf_path):
                    os.remove(form_pdf_path)
                if os.path.exists(pdf_temp):
                    os.remove(pdf_temp)
            except Exception:
                pass

            os.replace(final_pdf_temp, pdf_filename)

        except ImportError as e:
            # Se reportlab/PyPDF2 não estiverem disponíveis
            print(f"[AVISO] Pacotes para assinaturas não disponíveis: {e}")
        except Exception as e:
            # Qualquer outro erro na geração da página de assinaturas
            print(
                f"[ERRO] Falha ao criar página de assinaturas: {type(e).__name__}: {e}"
            )
            import traceback

            traceback.print_exc()

        with _export_lock:
            _export_status["message"] = (
                f"[green]✅ Relatório formal exportado: {pdf_filename}[/]"
            )
            _export_status["completed"] = True
            _export_status["running"] = False

    except ImportError as e:
        with _export_lock:
            _export_status["message"] = f"[red]❌ matplotlib não disponível: {e}[/]"
            _export_status["completed"] = True
            _export_status["running"] = False
    except Exception as e:
        # Limpar arquivos temporários caso erro
        try:
            if 'pdf_temp' in locals() and os.path.exists(pdf_temp):
                os.remove(pdf_temp)
        except Exception:
            pass

        # Registrar traceback em arquivo de log persistente
        try:
            os.makedirs(os.path.dirname(config.export_error_log), exist_ok=True)
            import traceback

            with open(config.export_error_log, "a", encoding="utf-8") as logf:
                logf.write(f"\n--- {datetime.datetime.now().isoformat()} ---\n")
                logf.write(traceback.format_exc())
        except Exception:
            pass

        with _export_lock:
            _export_status["message"] = (
                f"[red]❌ Erro ao gerar relatório: {str(e)[:200]}[/]"
            )
            _export_status["completed"] = True
            _export_status["running"] = False


def export_combined_report(full_history: bool = False) -> str:
    """Inicia exportação do relatório combinado em thread separada.

    Args:
        full_history: Se True, tenta exportar todo o histórico sem downsampling.
    """
    global _export_status

    with _export_lock:
        if _export_status["running"]:
            return f"[yellow]{t('stalker.export_already_running')}[/]"

        # Verificar se há dados para exportar
        if not local_stats.history and get_speed_tester().stats.test_count == 0:
            return f"[yellow]{t('stalker.export_no_data')}[/]"

        _export_status["running"] = True
        _export_status["completed"] = False
        _export_status["message"] = None

    # Iniciar thread de exportação
    export_thread = threading.Thread(
        target=_generate_combined_pdf_worker, args=(full_history,), daemon=True
    )
    export_thread.start()

    if full_history:
        return f"[cyan]{t('stalker.export_pdf_full_bg')}[/]"
    return f"[cyan]{t('stalker.export_pdf_bg')}[/]"


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
        stats_line = t("stalker.graph_stats", min=stats.min_ms, max=stats.max_ms, avg=stats.avg_ms)
    else:
        stats_line = t("stalker.graph_waiting")

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
        f"[b bold cyan]{t('stalker.header_title')}[/]  [dim]|  {current_date} {current_time}[/]"
    )
    grid.add_row(
        f"[dim]{t('stalker.header_info', os=os_name, gateway=config.gateway_ip, dns=config.external_ip, ports=ports_info, threshold=config.lag_threshold_ms)}[/]"
    )
    grid.add_row(
        f"[dim italic]{t('stalker.header_keys')}[/]"
    )
    return Panel(grid, style="white on blue")


def make_ping_table(local_ms, ext_ms, threshold):
    """Cria a tabela de status dos Pings."""
    table = Table(expand=True, box=box.ROUNDED)
    table.add_column(t("stalker.ping_destination"), justify="center")
    table.add_column(t("stalker.ping_ms"), justify="center")
    table.add_column(t("stalker.ping_status"), justify="center")

    # Formatação Local
    if local_ms is None:
        local_display = t("stalker.timeout")
        local_style = "bold white on red"
        local_status = t("stalker.critical")
    else:
        local_display = f"{local_ms:.1f} ms"
        if local_ms > threshold:
            local_style = "bold red"
            local_status = t("stalker.lag_local")
        else:
            local_style = "green"
            local_status = "OK"

    # Formatação Externa
    if ext_ms is None:
        ext_display = t("stalker.timeout")
        ext_style = "bold white on red"
        ext_status = t("stalker.critical")
    else:
        ext_display = f"{ext_ms:.1f} ms"
        if ext_ms > threshold:
            ext_style = "bold red"
            ext_status = t("stalker.lag_external")
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

    return Panel(table, title=t("stalker.connection_status"), border_style="cyan")


def make_graph_panel():
    """Cria painel com ambos os gráficos de ping mostrando info de tempo."""
    local_graph = make_ascii_graph(
        local_stats, width=config.graph_width, label="[cyan]Gateway[/]"
    )
    ext_graph = make_ascii_graph(
        external_stats, width=config.graph_width, label=f"[orange1]{t('stalker.graph_external')}[/]"
    )

    # Info de intervalo de tempo
    if local_stats.start_time:
        start_str = local_stats.start_time.strftime("%H:%M:%S")
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        time_info = f"[dim]{start_str} → {now_str}[/]"
    else:
        time_info = f"[dim]{t('stalker.graph_waiting')}[/]"

    # Indicador de linha de threshold
    threshold_info = f"[red]{t('stalker.graph_threshold', threshold=config.lag_threshold_ms)}[/]"

    content = Text.from_markup(
        f"{time_info}\n\n{local_graph}\n\n{ext_graph}\n\n{threshold_info}"
    )
    return Panel(
        content, title=t("stalker.graph_title"), border_style="magenta"
    )


def make_process_table(procs):
    """Cria a tabela de processos suspeitos."""
    table = Table(expand=True, box=box.SIMPLE_HEAD)
    table.add_column("PID", style="dim", width=8)
    table.add_column(t("stalker.process_col"), style="bold yellow")
    table.add_column(t("stalker.total_usage_mb"), justify="right", style="magenta")

    if not procs:
        if is_android():
            table.add_row("-", f"[dim]{t('stalker.no_access_root')}[/]", "-")
        else:
            table.add_row("-", f"[dim]{t('stalker.no_traffic')}[/]", "-")
    else:
        for pid, name, bytes_total in procs:
            mb = bytes_total / (1024 * 1024)
            proc_name = name if name else t("stalker.unknown_process")
            table.add_row(str(pid), proc_name, f"{mb:.2f} MB")

    return Panel(
        table, title=t("stalker.process_table_title"), border_style="yellow"
    )


def make_ports_panel():
    """Cria painel de portas TCP em listening."""
    table = Table(expand=True, box=box.SIMPLE_HEAD)
    table.add_column(t("stalker.ports_col"), style="bold yellow", width=8, justify="center")
    table.add_column(t("stalker.process_short_col"), style="bold green")
    table.add_column(t("stalker.address_col"), style="dim", width=10)

    # Mostrar no máximo 8 portas
    ports_to_show = port_scanner_state.listening_tcp[:8]

    if not ports_to_show:
        table.add_row("-", f"[dim]{t('stalker.no_ports_found')}[/]", "-")
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
        title=t("stalker.ports_title", total=total, extra=extra_info, last_scan=last_scan),
        border_style="green",
    )


def make_connections_panel():
    """Cria painel de processos com mais conexões."""
    table = Table(expand=True, box=box.SIMPLE_HEAD)
    table.add_column(t("stalker.process_col"), style="bold cyan")
    table.add_column(t("stalker.connections_col"), style="bold yellow", justify="center", width=8)
    table.add_column(t("stalker.ram_col"), style="dim", justify="right", width=8)

    connections = port_scanner_state.top_connections[:5]

    if not connections:
        table.add_row(f"[dim]{t('stalker.waiting_scan')}[/]", "-", "-")
    else:
        for proc in connections:
            ram_str = f"{proc.memoria_mb:.0f}MB" if proc.memoria_mb > 0 else "N/A"
            table.add_row(proc.nome[:18], str(proc.conexoes), ram_str)

    return Panel(
        table,
        title=t("stalker.connections_title", count=port_scanner_state.total_established),
        border_style="cyan",
    )


def make_speed_panel():
    """Cria painel de velocidade mostrando todos provedores em tempo real."""
    try:
        tester = get_speed_tester()
        snapshot = tester.get_stats_snapshot()

        table = Table(expand=True, box=box.ROUNDED)
        table.add_column(t("stalker.speed_provider"), style="bold cyan", width=12)
        table.add_column(t("stalker.speed_download"), justify="center", width=10)
        table.add_column(t("stalker.speed_upload"), justify="center", width=10)
        table.add_column(t("stalker.speed_ping"), justify="center", width=8)

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
                        f"[dim]{t('stalker.speed_downloading')}[/]",
                        "[dim]...[/]",
                    )
                elif progress_phase == "upload":
                    table.add_row(
                        f"[yellow]{current_provider[:11]}[/]",
                        "[dim]ok[/]",
                        f"[yellow]{t('stalker.speed_uploading')}[/]",
                        "[dim]...[/]",
                    )
                else:
                    table.add_row(
                        f"[yellow]{current_provider[:11]}[/]",
                        f"[dim]{t('stalker.speed_connecting')}[/]",
                        "[dim]...[/]",
                        "[dim]...[/]",
                    )
            else:
                table.add_row(
                    "[yellow]...[/]", f"[dim]{t('stalker.speed_starting')}[/]", "[dim]...[/]", "[dim]...[/]"
                )
        elif not results_by_provider:
            if snapshot.get("last_error"):
                error_msg = str(snapshot.get("last_error", t("stalker.speed_error")))[:20]
                table.add_row("-", f"[red]{error_msg}[/]", "-", "-")
            else:
                table.add_row(
                    "[dim]...[/]", f"[dim]{t('stalker.speed_waiting')}[/]", "[dim]...[/]", "[dim]...[/]"
                )

        test_count = snapshot.get("test_count", 0)
        num_providers = len(results_by_provider)

        return Panel(
            table,
            title=t("stalker.speed_title", providers=num_providers, tests=test_count),
            subtitle=f"[dim]{t('stalker.speed_subtitle', down=speed_config.velocidade_contratada_down, up=speed_config.velocidade_contratada_up, min=speed_config.percentual_minimo)}[/]",
            border_style="magenta",
        )
    except Exception as e:
        return Panel(
            f"[red]{t('stalker.speed_error')}: {str(e)[:30]}[/]",
            title=t("stalker.speed_title_error"),
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
        content, title=t("stalker.log_title"), border_style="red"
    )


def make_help_panel():
    """Cria painel de ajuda com atalhos de teclado."""
    help_text = t("stalker.help_text")
    return Panel(Text.from_markup(help_text), title=t("stalker.help_title"), border_style="green")


def main(external_console: Console | None = None, session_recorder=None):
    global running, show_help, port_scanner_state, scan_counter, console

    if external_console is not None:
        console = external_console

    # Reset state so stalker can be re-entered from the main menu
    running = True
    show_help = False
    scan_counter = 0

    # Layout Principal
    layout = Layout()

    log_events = deque(maxlen=config.history_size)
    log_events.append(f"[dim]{t('stalker.monitoring_started')}[/]")

    if is_android():
        log_events.append(
            f"[yellow]{t('stalker.android_detected')}[/]"
        )

    # Scan inicial de portas em background (não trava a inicialização)
    def _initial_port_scan():
        global port_scanner_state
        try:
            port_scanner_state = run_full_scan()
        except Exception:
            pass  # Silently fail, will show empty state

    threading.Thread(target=_initial_port_scan, daemon=True).start()
    log_events.append(f"[dim]{t('stalker.port_scan_bg')}[/]")

    # Iniciar teste de velocidade contínuo em background
    try:
        start_continuous_testing()
        log_events.append(
            f"[cyan]{t('stalker.speed_monitor_started', down=speed_config.velocidade_contratada_down, up=speed_config.velocidade_contratada_up)}[/]"
        )
    except Exception as e:
        log_events.append(f"[red]{t('stalker.speed_start_error', error=e)}[/]")

    # Register layout with session recorder for GIF capture
    if session_recorder is not None:
        session_recorder.set_renderable(layout)

    with Live(layout, console=console, refresh_per_second=4, screen=True):
        while running:
            try:
                global test_session_start
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

                # Registrar no histórico completo para relatório formal
                now = datetime.datetime.now()
                if test_session_start is None:
                    test_session_start = now
                full_ping_history.append((now, local_ms, ext_ms))

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
                        f"[{start_time}] [bold red]{t('stalker.alert_local_lag', ms=local_ms)}[/]"
                    )
                    alert_triggered = True
                elif ext_ms and ext_ms > config.lag_threshold_ms:
                    log_events.append(
                        f"[{start_time}] [bold orange1]{t('stalker.alert_ext_lag', ms=ext_ms)}[/]"
                    )
                    alert_triggered = True
                elif local_ms is None or ext_ms is None:
                    log_events.append(
                        f"[{start_time}] [bold white on red]{t('stalker.alert_packet_loss')}[/]"
                    )
                    alert_triggered = True

                if alert_triggered:
                    # Usar análise inteligente de origem do lag
                    suspeito, explicacao = analyze_lag_source(
                        local_ms, ext_ms, config.lag_threshold_ms, procs
                    )
                    log_events.append(f"   ↳ [bold yellow]{t('stalker.diagnostic')}[/] {suspeito}")
                    log_events.append(f"   ↳ [dim]{explicacao}[/]")

                    # Mostrar processo com mais conexões se houver (como info secundária)
                    if procs and not suspeito.startswith("🔌"):
                        top_hog = procs[0]
                        conns = top_hog[2] // (1024 * 1024)  # Número de conexões
                        hog_name = top_hog[1] if top_hog[1] else t("stalker.unknown_process")
                        log_events.append(
                            f"   ↳ [dim]{t('stalker.top_connections_log', name=hog_name, conns=conns)}[/]"
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

    # Cleanup
    if session_recorder is not None:
        session_recorder.set_renderable(None)
    stop_continuous_testing()

    # Perguntar se usuário quer gerar relatório ao sair
    tester = get_speed_tester()
    if tester.stats.test_count > 0 or local_stats.history:
        try:
            choice = (
                console.input(
                    f"\n[bold cyan]{t('stalker.ask_final_report')}[/]"
                )
                .strip()
                .lower()
            )
        except Exception:
            choice = "n"

        if choice in ("s", "sim", "y", "yes"):
            console.print(f"\n[cyan]{t('stalker.generating_report')}[/]")
            export_combined_report()
            # Aguardar no máximo 3 segundos para o relatório ser gerado
            import time as time_module

            for _ in range(30):  # 30 x 0.1s = 3s máximo
                time_module.sleep(0.1)
                status = get_export_status()
                if status:
                    console.print(status)
                    break
        else:
            console.print(f"[dim]{t('stalker.report_skipped')}[/]")


# Carregar preferências salvas (se existirem)
load_prefs()

if __name__ == "__main__":
    main()
