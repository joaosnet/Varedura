"""
Docker-Clennear - System Monitor & Docker Cleanup Tool

Usage:
    uv run main.py

Main entry point providing a Rich-based menu for all tools.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def show_menu():
    """Display the main menu."""
    console.clear()

    # Header
    header = Table.grid(expand=True)
    header.add_column(justify="center")
    header.add_row("[bold cyan]🐳 Docker-Clennear v2.1[/]")
    header.add_row("[dim]Monitor de Sistema & Ferramenta de Limpeza Docker[/]")
    console.print(Panel(header, style="blue"))
    console.print()

    # Menu options
    menu = Table(box=box.ROUNDED, expand=True, show_header=False)
    menu.add_column("Key", style="bold yellow", width=5)
    menu.add_column("Option", style="white")
    menu.add_column("Description", style="dim")

    menu.add_row(
        "1", "Network Stalker", "Monitor de rede em tempo real com scanner de portas"
    )
    menu.add_row("2", "Docker Cleanup", "Limpeza rápida do Docker")
    menu.add_row("3", "Docker Full Cleanup", "Limpeza completa com compactação VHDX")
    menu.add_row("4", "LMArena Models", "Gerar lista de modelos LMArena")
    menu.add_row("5", "Port Scanner", "Escaner de portas standalone")
    menu.add_row("", "", "")
    menu.add_row("Q", "Sair", "Encerrar o programa")

    console.print(Panel(menu, title="🔧 Ferramentas", border_style="cyan"))
    console.print()


def run_network_stalker():
    """Run the network stalker monitor."""
    try:
        from monitor.stalker import main as stalker_main

        stalker_main()
    except KeyboardInterrupt:
        pass
    except ImportError as e:
        console.print(f"[red]Error loading Network Stalker: {e}[/]")


def run_docker_cleanup():
    """Run quick Docker cleanup."""
    try:
        from docker_cleaner.core import WSLDockerCleaner

        cleaner = WSLDockerCleaner()
        cleaner.docker_cleanup()
    except ImportError as e:
        console.print(f"[red]Error loading Docker Cleaner: {e}[/]")
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/]")


def run_docker_full_cleanup():
    """Run full Docker cleanup with VHDX compaction."""
    try:
        from docker_cleaner.core import WSLDockerCleaner

        cleaner = WSLDockerCleaner()
        cleaner.run_full_cleanup_with_progress()
    except ImportError as e:
        console.print(f"[red]Error loading Docker Cleaner: {e}[/]")
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/]")


def run_lmarena_models():
    """Run LMArena models generator."""
    try:
        from lmarena.generator import main as generator_main

        generator_main()
    except ImportError as e:
        console.print(f"[red]Error loading LMArena generator: {e}[/]")
    except Exception as e:
        console.print(f"[red]Error generating models: {e}[/]")


def run_port_scanner():
    """Executa o escaner de portas standalone."""
    try:
        from monitor.port_scanner import run_full_scan
        from rich.table import Table
        from rich.panel import Panel

        console.print("\n[bold cyan]🔍 Escaneando portas...[/]\n")
        state = run_full_scan()

        # Tabela TCP
        tcp_table = Table(
            title=f"🔌 Portas TCP em Listening ({state.total_tcp})", border_style="cyan"
        )
        tcp_table.add_column("Porta", style="bold yellow", justify="center")
        tcp_table.add_column("Processo", style="bold green")
        tcp_table.add_column("Endereço", style="dim")

        for port in state.listening_tcp[:15]:
            tcp_table.add_row(str(port.porta), port.processo, port.endereco)

        console.print(tcp_table)

        # Tabela de conexões
        conn_table = Table(
            title=f"\n🏆 Top Processos por Conexões (Estabelecidas: {state.total_established})",
            border_style="green",
        )
        conn_table.add_column("Processo", style="bold cyan")
        conn_table.add_column("Conexões", style="bold yellow", justify="center")
        conn_table.add_column("RAM (MB)", style="dim", justify="right")

        for proc in state.top_connections:
            ram_str = f"{proc.memoria_mb:.1f}" if proc.memoria_mb > 0 else "N/A"
            conn_table.add_row(proc.nome, str(proc.conexoes), ram_str)

        console.print(conn_table)

        # Resumo
        console.print(
            Panel(
                f"[bold green]📊 Resumo:[/] {state.total_tcp} TCP | {state.total_udp} UDP | {state.total_established} Estabelecidas\n"
                f"[Último scan: {state.last_scan_time}]",
                border_style="blue",
            )
        )

    except ImportError as e:
        console.print(f"[red]Erro ao carregar port scanner: {e}[/]")
    except Exception as e:
        console.print(f"[red]Erro durante scan: {e}[/]")


def main():
    """Main entry point."""
    while True:
        show_menu()

        choice = console.input("[bold cyan]Selecione uma opção: [/]").strip().lower()

        if choice == "1":
            run_network_stalker()
        elif choice == "2":
            console.print("\n[yellow]Iniciando Limpeza Docker...[/]\n")
            run_docker_cleanup()
            console.input("\n[dim]Pressione Enter para continuar...[/]")
        elif choice == "3":
            console.print("\n[yellow]Iniciando Limpeza Completa Docker...[/]\n")
            run_docker_full_cleanup()
            console.input("\n[dim]Pressione Enter para continuar...[/]")
        elif choice == "4":
            console.print("\n[yellow]Iniciando Gerador de Modelos LMArena...[/]\n")
            run_lmarena_models()
            console.input("\n[dim]Pressione Enter para continuar...[/]")
        elif choice == "5":
            run_port_scanner()
            console.input("\n[dim]Pressione Enter para continuar...[/]")
        elif choice == "q":
            console.print("\n[cyan]Até logo! 👋[/]\n")
            sys.exit(0)
        else:
            console.print("[red]Opção inválida. Tente novamente.[/]")
            console.input("[dim]Pressione Enter...[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye! 👋[/]\n")
        sys.exit(0)
