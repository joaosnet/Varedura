"""
Varedura - System Monitor & Docker Cleanup Tool

Usage:
    uv run main.py

Main entry point providing a Rich-based menu for all tools.
"""

import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from i18n import t, init as i18n_init, set_language, get_language, get_supported_languages

console = Console()
i18n_init()


def show_menu():
    """Display the main menu."""
    console.clear()

    # Header
    header = Table.grid(expand=True)
    header.add_column(justify="center")
    header.add_row(f"[bold cyan]{t('menu.title')}[/]")
    header.add_row(f"[dim]{t('menu.subtitle')}[/]")
    console.print(Panel(header, style="blue"))
    console.print()

    # Menu options
    menu = Table(box=box.ROUNDED, expand=True, show_header=False)
    menu.add_column("Key", style="bold yellow", width=5)
    menu.add_column("Option", style="white")
    menu.add_column("Description", style="dim")

    menu.add_row("1", t("menu.option_1"), t("menu.desc_1"))
    menu.add_row("2", t("menu.option_2"), t("menu.desc_2"))
    menu.add_row("3", t("menu.option_3"), t("menu.desc_3"))
    menu.add_row("4", t("menu.option_4"), t("menu.desc_4"))
    menu.add_row("", "", "")
    menu.add_row("L", t("menu.option_lang"), t("menu.desc_lang"))
    menu.add_row("Q", t("menu.quit"), t("menu.quit_desc"))

    console.print(Panel(menu, title=t("menu.tools"), border_style="cyan"))
    console.print()


def run_network_stalker():
    """Run the network stalker monitor."""
    try:
        from monitor.stalker import main as stalker_main

        stalker_main()
    except KeyboardInterrupt:
        pass
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_stalker', error=e)}[/]")


def run_docker_cleanup():
    """Run quick Docker cleanup."""
    try:
        from docker_cleaner.core import WSLDockerCleaner

        cleaner = WSLDockerCleaner()
        cleaner.docker_cleanup()
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_cleaner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_cleanup', error=e)}[/]")


def run_docker_full_cleanup():
    """Run full Docker cleanup with VHDX compaction."""
    try:
        from docker_cleaner.core import WSLDockerCleaner

        cleaner = WSLDockerCleaner()
        cleaner.run_full_cleanup_with_progress()
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_cleaner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_cleanup', error=e)}[/]")


def run_lmarena_models():
    """Run LMArena models generator."""
    try:
        from lmarena.generator import main as generator_main

        generator_main()
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_lmarena', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_generating_models', error=e)}[/]")


def run_port_scanner():
    """Executa o escaner de portas standalone."""
    try:
        from monitor.port_scanner import run_full_scan
        from rich.table import Table
        from rich.panel import Panel

        console.print(f"\n[bold cyan]{t('scanner.scanning')}[/]\n")
        state = run_full_scan()

        # TCP table
        tcp_table = Table(
            title=t("scanner.tcp_listening", count=state.total_tcp), border_style="cyan"
        )
        tcp_table.add_column(t("scanner.port"), style="bold yellow", justify="center")
        tcp_table.add_column(t("scanner.process"), style="bold green")
        tcp_table.add_column(t("scanner.address"), style="dim")

        for port in state.listening_tcp[:15]:
            tcp_table.add_row(str(port.porta), port.processo, port.endereco)

        console.print(tcp_table)

        # Connections table
        conn_table = Table(
            title=f"\n{t('scanner.top_connections', count=state.total_established)}",
            border_style="green",
        )
        conn_table.add_column(t("scanner.process"), style="bold cyan")
        conn_table.add_column(t("scanner.connections"), style="bold yellow", justify="center")
        conn_table.add_column(t("scanner.ram_mb"), style="dim", justify="right")

        for proc in state.top_connections:
            ram_str = f"{proc.memoria_mb:.1f}" if proc.memoria_mb > 0 else "N/A"
            conn_table.add_row(proc.nome, str(proc.conexoes), ram_str)

        console.print(conn_table)

        # Summary
        console.print(
            Panel(
                f"[bold green]{t('scanner.summary')}[/] {t('scanner.summary_detail', tcp=state.total_tcp, udp=state.total_udp, established=state.total_established)}\n"
                f"[{t('scanner.last_scan', time=state.last_scan_time)}]",
                border_style="blue",
            )
        )

    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_scanner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_scan', error=e)}[/]")


def change_language():
    """Show language selection menu."""
    console.print(f"\n[bold cyan]{t('lang.select')}[/]\n")
    lang_names = {"pt": t("lang.pt"), "en": t("lang.en")}
    current = get_language()
    for i, lang_code in enumerate(get_supported_languages(), 1):
        marker = " ←" if lang_code == current else ""
        console.print(f"  [bold yellow]{i}[/] {lang_names.get(lang_code, lang_code)}{marker}")
    console.print()
    choice = console.input("[bold cyan]> [/]").strip()
    langs = list(get_supported_languages())
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(langs):
            new_lang = set_language(langs[idx])
            console.print(f"\n[green]{t('lang.changed', lang=lang_names.get(new_lang, new_lang))}[/]")
    except (ValueError, IndexError):
        pass


def main():
    """Main entry point."""
    while True:
        show_menu()

        choice = console.input(f"[bold cyan]{t('menu.select_option')}[/]").strip().lower()

        if choice == "1":
            run_network_stalker()
        elif choice == "2":
            console.print(f"\n[yellow]{t('menu.starting_cleanup')}[/]\n")
            run_docker_cleanup()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "3":
            console.print(f"\n[yellow]{t('menu.starting_full_cleanup')}[/]\n")
            run_docker_full_cleanup()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "4":
            run_port_scanner()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "lmarena":
            console.print(f"\n[yellow]{t('menu.starting_lmarena')}[/]\n")
            run_lmarena_models()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "l":
            change_language()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "q":
            console.print(f"\n[cyan]{t('menu.goodbye')}[/]\n")
            sys.exit(0)
        else:
            console.print(f"[red]{t('menu.invalid_option')}[/]")
            console.input(f"[dim]{t('menu.press_enter_short')}[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print(f"\n[cyan]{t('menu.goodbye')}[/]\n")
        sys.exit(0)
