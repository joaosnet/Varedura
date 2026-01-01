"""
V's Network Stalker v3.0 - Real-time Network Monitor with Interactive Controls

Features:
    - Real-time ping monitoring (local gateway + external)
    - Live ASCII graph with peaks and minimums
    - Process network usage table
    - Interactive keyboard controls
    - Export to PNG/CSV
"""

import subprocess
import platform
import time
import datetime
import psutil
import re
import os

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

# Windows keyboard input
if platform.system().lower() == "windows":
    import msvcrt
else:
    import sys
    import select


# ==============================================================================
# CONFIGURAÇÕES DO STALKER (Modifiable at runtime)
# ==============================================================================
@dataclass
class StalkerConfig:
    gateway_ip: str = "192.168.18.1"  # IP do Roteador
    external_ip: str = "8.8.8.8"  # Google DNS
    lag_threshold_ms: int = 100  # Limite para considerar LAG (ms)
    interval: float = 1.0  # Intervalo de atualização (segundos)
    history_size: int = 8  # Quantas linhas de log manter
    graph_width: int = 50  # Largura do gráfico ASCII
    graph_history: int = 100  # Quantos pontos manter no histórico


@dataclass
class PingStats:
    """Statistics for ping history with timestamps."""

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
show_help = False
running = True


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
    """Identifica os processos (Top 5) com maior tráfego acumulado."""
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


# --- Keyboard Input ---
def check_keyboard():
    """Non-blocking keyboard check."""
    global show_help, running, config

    if platform.system().lower() == "windows":
        if msvcrt.kbhit():
            key = msvcrt.getch().decode("utf-8", errors="ignore").lower()
            return key
    else:
        # Unix-like systems
        if select.select([sys.stdin], [], [], 0)[0]:
            return sys.stdin.read(1).lower()
    return None


def handle_key(key: str) -> Optional[str]:
    """Handle keyboard input. Returns message for log or None."""
    global show_help, running, config

    if key == "q":
        running = False
        return None
    elif key == "h":
        show_help = not show_help
        return "[dim]Toggle help panel[/]"
    elif key == "g":
        return prompt_change_gateway()
    elif key == "e":
        return prompt_change_external()
    elif key == "t":
        return prompt_change_threshold()
    elif key == "i":
        return prompt_change_interval()
    elif key == "x":
        return export_data()
    return None


def prompt_change_gateway() -> str:
    """Change gateway IP (simplified - just cycles common values)."""
    common_gateways = ["192.168.1.1", "192.168.0.1", "192.168.18.1", "10.0.0.1"]
    try:
        current_idx = common_gateways.index(config.gateway_ip)
        config.gateway_ip = common_gateways[(current_idx + 1) % len(common_gateways)]
    except ValueError:
        config.gateway_ip = common_gateways[0]
    return f"[yellow]Gateway alterado para: {config.gateway_ip}[/]"


def prompt_change_external() -> str:
    """Change external IP (cycle through DNS options)."""
    dns_servers = ["8.8.8.8", "1.1.1.1", "208.67.222.222", "9.9.9.9"]
    try:
        current_idx = dns_servers.index(config.external_ip)
        config.external_ip = dns_servers[(current_idx + 1) % len(dns_servers)]
    except ValueError:
        config.external_ip = dns_servers[0]
    return f"[yellow]DNS externo alterado para: {config.external_ip}[/]"


def prompt_change_threshold() -> str:
    """Cycle through threshold values."""
    thresholds = [50, 100, 150, 200, 300]
    try:
        current_idx = thresholds.index(config.lag_threshold_ms)
        config.lag_threshold_ms = thresholds[(current_idx + 1) % len(thresholds)]
    except ValueError:
        config.lag_threshold_ms = thresholds[0]
    return f"[yellow]Threshold alterado para: {config.lag_threshold_ms}ms[/]"


def prompt_change_interval() -> str:
    """Cycle through interval values."""
    intervals = [0.5, 1.0, 2.0, 5.0]
    try:
        current_idx = intervals.index(config.interval)
        config.interval = intervals[(current_idx + 1) % len(intervals)]
    except ValueError:
        config.interval = intervals[0]
    return f"[yellow]Intervalo alterado para: {config.interval}s[/]"


def export_data() -> str:
    """Export ping history to CSV and PNG with timestamps."""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    # Export CSV with timestamps
    csv_filename = f"exports/ping_history_{timestamp}.csv"
    try:
        import os

        os.makedirs("exports", exist_ok=True)
        with open(csv_filename, "w") as f:
            f.write("timestamp,local_ms,external_ms\n")
            for ts, local, ext in zip(
                local_stats.timestamps, local_stats.history, external_stats.history
            ):
                ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
                local_val = f"{local:.1f}" if local is not None else ""
                ext_val = f"{ext:.1f}" if ext is not None else ""
                f.write(f"{ts_str},{local_val},{ext_val}\n")
    except Exception as e:
        return f"[red]Erro ao exportar CSV: {e}[/]"

    # Export PNG using matplotlib
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        fig, ax = plt.subplots(figsize=(14, 7))

        # Use timestamps for x-axis
        times = list(local_stats.timestamps)
        local_valid = list(local_stats.history)
        ext_valid = list(external_stats.history)

        ax.plot(
            times,
            local_valid,
            label=f"Gateway ({config.gateway_ip})",
            color="cyan",
            linewidth=2,
        )
        ax.plot(
            times,
            ext_valid,
            label=f"External ({config.external_ip})",
            color="orange",
            linewidth=2,
        )

        # Mark threshold
        ax.axhline(
            y=config.lag_threshold_ms,
            color="red",
            linestyle="--",
            label=f"Threshold ({config.lag_threshold_ms}ms)",
        )

        # Format x-axis as time
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        plt.xticks(rotation=45)

        ax.set_xlabel("Time")
        ax.set_ylabel("Ping (ms)")

        # Title with time range
        if times:
            start_str = times[0].strftime("%Y-%m-%d %H:%M:%S")
            end_str = times[-1].strftime("%H:%M:%S")
            ax.set_title(f"V's Network Stalker - Ping History\n{start_str} → {end_str}")
        else:
            ax.set_title("V's Network Stalker - Ping History")

        ax.legend()
        ax.grid(True, alpha=0.3)

        png_filename = f"exports/ping_graph_{timestamp}.png"
        plt.savefig(png_filename, dpi=150, bbox_inches="tight")
        plt.close()

        return f"[green]Exportado: {csv_filename} e {png_filename}[/]"
    except ImportError:
        return f"[yellow]CSV exportado: {csv_filename} (matplotlib não disponível para PNG)[/]"
    except Exception as e:
        return f"[yellow]CSV exportado: {csv_filename} | PNG erro: {e}[/]"


# --- ASCII Graph ---
def make_ascii_graph(
    stats: PingStats, width: int = 40, height: int = 8, label: str = ""
) -> str:
    """Create ASCII line graph from ping history."""
    history = list(stats.history)
    if not history:
        return " " * width

    # Filter None values, replace with 0 for display
    values = [v if v is not None else 0 for v in history[-width:]]
    if not values:
        return " " * width

    # Normalize to height
    max_val = max(max(values), config.lag_threshold_ms * 1.5) if values else 100

    chars = "▁▂▃▄▅▆▇█"

    result = []
    for v in values:
        if v == 0:
            result.append(" ")
        else:
            # Normalize to 0-7 range
            normalized = min(7, int((v / max_val) * 7))
            result.append(chars[normalized])

    # Pad to width
    graph_line = "".join(result).ljust(width)

    # Add stats line
    if stats.min_ms is not None:
        stats_line = (
            f"Min:{stats.min_ms:.0f} Max:{stats.max_ms:.0f} Avg:{stats.avg_ms:.0f}ms"
        )
    else:
        stats_line = "Aguardando dados..."

    return f"{label}\n{graph_line}\n[dim]{stats_line}[/]"


# --- Interface Components ---
def make_header():
    """Cria o cabeçalho do dashboard."""
    os_name = platform.system()
    if is_android():
        os_name = "Android (Termux)"

    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_row(
        f"[b bold cyan]💀 V's NETWORK STALKER v3.0[/]  [dim]|  {current_date} {current_time}[/]"
    )
    grid.add_row(
        f"[dim]OS: {os_name} | Gateway: {config.gateway_ip} | DNS: {config.external_ip} | "
        f"Threshold: {config.lag_threshold_ms}ms | Interval: {config.interval}s[/]"
    )
    grid.add_row(
        "[dim italic]Teclas: [H]elp [G]ateway [E]xternal [T]hreshold [I]nterval e[X]port [Q]uit[/]"
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
    """Create panel with both ping graphs showing time info."""
    local_graph = make_ascii_graph(
        local_stats, width=config.graph_width, label="[cyan]Gateway[/]"
    )
    ext_graph = make_ascii_graph(
        external_stats, width=config.graph_width, label="[orange1]External[/]"
    )

    # Time range info
    if local_stats.start_time:
        start_str = local_stats.start_time.strftime("%H:%M:%S")
        now_str = datetime.datetime.now().strftime("%H:%M:%S")
        time_info = f"[dim]{start_str} → {now_str}[/]"
    else:
        time_info = "[dim]Aguardando dados...[/]"

    # Threshold line indicator
    threshold_info = f"[red]--- Threshold: {config.lag_threshold_ms}ms ---[/]"

    content = Text.from_markup(
        f"{time_info}\n\n{local_graph}\n\n{ext_graph}\n\n{threshold_info}"
    )
    return Panel(content, title="📊 Ping History (Real-time)", border_style="magenta")


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


def make_log_panel(log_events):
    """Cria o painel de histórico de alertas."""
    lines = []
    for line in log_events:
        lines.append(Text.from_markup(line))

    # Join with newlines by creating a renderable group
    content = Text()
    for i, line in enumerate(lines):
        content.append_text(line)
        if i < len(lines) - 1:
            content.append("\n")

    return Panel(
        content, title="📜 Histórico de Alertas (Últimos Eventos)", border_style="red"
    )


def make_help_panel():
    """Create help panel with keybindings."""
    help_text = """
[bold cyan]CONTROLES:[/]

  [yellow]H[/] - Mostrar/esconder esta ajuda
  [yellow]G[/] - Ciclar IP do Gateway (192.168.x.1, 10.0.0.1)
  [yellow]E[/] - Ciclar DNS externo (8.8.8.8, 1.1.1.1, etc)
  [yellow]T[/] - Ciclar threshold de lag (50, 100, 150, 200, 300ms)
  [yellow]I[/] - Ciclar intervalo de refresh (0.5, 1, 2, 5s)
  [yellow]X[/] - Exportar dados para CSV e gráfico PNG
  [yellow]Q[/] - Sair

[dim]Os valores ciclam automaticamente entre opções comuns.[/]
"""
    return Panel(Text.from_markup(help_text), title="❓ Ajuda", border_style="green")


def main():
    global running, show_help

    # Layout Principal
    layout = Layout()

    log_events = deque(maxlen=config.history_size)
    log_events.append("[dim]Monitoramento iniciado... aguardando anomalias.[/]")

    if is_android():
        log_events.append(
            "[yellow]Android detectado: Leitura de processos pode ser limitada.[/]"
        )

    with Live(layout, refresh_per_second=4, screen=True) as live:
        while running:
            try:
                # Check for keyboard input
                key = check_keyboard()
                if key:
                    msg = handle_key(key)
                    if msg:
                        log_events.append(
                            f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}"
                        )

                start_time = datetime.datetime.now().strftime("%H:%M:%S")

                # 1. Executa Testes
                local_ms = run_ping(config.gateway_ip)
                ext_ms = run_ping(config.external_ip)

                # Update stats for graph
                local_stats.add(local_ms)
                external_stats.add(ext_ms)

                # 2. Verifica Processos
                procs = get_top_network_hogs()

                # 3. Lógica de Log e Alerta
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

                if alert_triggered and procs:
                    top_hog = procs[0]
                    mb = top_hog[2] / (1024 * 1024)
                    hog_name = top_hog[1] if top_hog[1] else "Desconhecido"
                    log_events.append(
                        f"   ↳ [dim]Suspeito principal: {hog_name} ({mb:.1f} MB)[/]"
                    )

                # 4. Build Layout
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
                    layout["body"].split_row(
                        Layout(name="left", ratio=1),
                        Layout(name="right", ratio=1),
                    )
                    layout["left"].split_column(
                        Layout(name="ping_stats", ratio=1),
                        Layout(name="graph", ratio=2),
                    )
                    layout["right"].update(make_process_table(procs))

                    layout["header"].update(make_header())
                    layout["ping_stats"].update(
                        make_ping_table(local_ms, ext_ms, config.lag_threshold_ms)
                    )
                    layout["graph"].update(make_graph_panel())
                    layout["footer"].update(make_log_panel(log_events))

                time.sleep(config.interval)

            except KeyboardInterrupt:
                break


if __name__ == "__main__":
    main()
