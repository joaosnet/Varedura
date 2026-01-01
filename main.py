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
from rich.text import Text
from rich import box

console = Console()


def show_menu():
    """Display the main menu."""
    console.clear()

    # Header
    header = Table.grid(expand=True)
    header.add_column(justify="center")
    header.add_row("[bold cyan]🐳 Docker-Clennear v2.0[/]")
    header.add_row("[dim]System Monitor & Docker Cleanup Tool[/]")
    console.print(Panel(header, style="blue"))
    console.print()

    # Menu options
    menu = Table(box=box.ROUNDED, expand=True, show_header=False)
    menu.add_column("Key", style="bold yellow", width=5)
    menu.add_column("Option", style="white")
    menu.add_column("Description", style="dim")

    menu.add_row("1", "Network Stalker", "Monitor network latency in real-time")
    menu.add_row("2", "Docker Cleanup", "Quick Docker system prune")
    menu.add_row("3", "Docker Full Cleanup", "Full cleanup with VHDX compaction")
    menu.add_row("4", "LMArena Models", "Generate LMArena models list")
    menu.add_row("", "", "")
    menu.add_row("Q", "Quit", "Exit the program")

    console.print(Panel(menu, title="🔧 Tools", border_style="cyan"))
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


def main():
    """Main entry point."""
    while True:
        show_menu()

        choice = console.input("[bold cyan]Select option: [/]").strip().lower()

        if choice == "1":
            run_network_stalker()
        elif choice == "2":
            console.print("\n[yellow]Starting Docker Cleanup...[/]\n")
            run_docker_cleanup()
            console.input("\n[dim]Press Enter to continue...[/]")
        elif choice == "3":
            console.print("\n[yellow]Starting Full Docker Cleanup...[/]\n")
            run_docker_full_cleanup()
            console.input("\n[dim]Press Enter to continue...[/]")
        elif choice == "4":
            console.print("\n[yellow]Starting LMArena Models Generator...[/]\n")
            run_lmarena_models()
            console.input("\n[dim]Press Enter to continue...[/]")
        elif choice == "q":
            console.print("\n[cyan]Goodbye! 👋[/]\n")
            sys.exit(0)
        else:
            console.print("[red]Invalid option. Try again.[/]")
            console.input("[dim]Press Enter...[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[cyan]Goodbye! 👋[/]\n")
        sys.exit(0)
