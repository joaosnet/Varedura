"""Entrypoint CLI para executar a limpeza rápida do WSL Docker."""
from rich.console import Console
from typing import Optional
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.live import Live
import subprocess
import os
import time


def run_cmd(console, cmd, desc=""):
    if desc:
        console.print(f"\n[bold blue][INFO][/bold blue] {desc}")
    console.print(f"[yellow]Executando:[/yellow] {cmd}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180)
        if result.stdout:
            console.print(f"[green]Saída:[/green] {result.stdout.strip()}")
        if result.stderr and result.returncode != 0:
            console.print(f"[red]Erro:[/red] {result.stderr.strip()}")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        console.print("[red]TIMEOUT: Comando demorou muito para executar[/red]")
        return False
    except Exception as e:
        console.print(f"[red]Erro:[/red] {str(e)}")
        return False


def quick_cleanup(console: Optional[Console] = None):
    """Perform a quick cleanup. If a `console` is provided, use it for output.

    This allows the function to be called from an external UI by passing a
    `rich.console.Console(file=...)` writing to a capture target.
    """
    if console is None:
        console = Console()
    overall_progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console
    )
    current_task_progress = Progress(TextColumn("{task.description}"), console=console)
    from rich.console import Group
    progress_group = Group(Panel(Group(current_task_progress)), overall_progress)
    overall_task = overall_progress.add_task("[cyan]Executando limpeza rápida...", total=100)
    with Live(progress_group, refresh_per_second=10, console=console):
        try:
            current_task = current_task_progress.add_task("Limpando sistema Docker...")
            overall_progress.update(overall_task, description="[cyan]Limpando sistema Docker...")
            run_cmd(console, "docker system prune -af --volumes", "Limpando sistema Docker (agressivo)")
            current_task_progress.remove_task(current_task)
            overall_progress.update(overall_task, advance=40)

            current_task = current_task_progress.add_task("Parando Docker e WSL...")
            overall_progress.update(overall_task, description="[cyan]Parando Docker e WSL...")
            run_cmd(console, 'taskkill /F /IM "Docker Desktop.exe" /T 2>NUL', "Parando Docker Desktop")
            time.sleep(3)
            run_cmd(console, "wsl --shutdown", "Parando WSL")
            time.sleep(5)
            current_task_progress.remove_task(current_task)
            overall_progress.update(overall_task, advance=30)

            current_task = current_task_progress.add_task("Compactando arquivo VHDX...")
            overall_progress.update(overall_task, description="[cyan]Compactando arquivo VHDX...")
            vhdx_path = os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx")
            if os.path.exists(vhdx_path):
                size_before = os.path.getsize(vhdx_path) / (1024**3)
                console.print(f"\n[bold]Tamanho antes:[/bold] {size_before:.2f} GB")
                ps_cmd = f'Optimize-VHD -Path "{vhdx_path}" -Mode Full'
                if run_cmd(console, f'powershell -Command "{ps_cmd}"', "Compactando arquivo VHDX"):
                    time.sleep(5)
                    if os.path.exists(vhdx_path):
                        size_after = os.path.getsize(vhdx_path) / (1024**3)
                        space_saved = size_before - size_after
                        console.print(f"[bold]Tamanho após:[/bold] {size_after:.2f} GB")
                        console.print(f"[bold]Espaço economizado:[/bold] {space_saved:.2f} GB")
            else:
                console.print(f"[yellow]Arquivo VHDX não encontrado: {vhdx_path}[/yellow]")
            current_task_progress.remove_task(current_task)
            overall_progress.update(overall_task, advance=30)
            overall_progress.update(overall_task, description="[green]Limpeza concluída!")
        except Exception as e:
            console.print(f"[red]Erro durante a limpeza: {str(e)}[/red]")
            return False
    console.print("\n[bold green]== LIMPEZA CONCLUÍDA ==[/bold green]")
    console.print("[bold]Reinicie o Docker Desktop para usar normalmente.[/bold]")
    return True


if __name__ == "__main__":
    console = Console()
    try:
        success = quick_cleanup()
        if success:
            console.print("\n[bold green]Limpeza concluída com sucesso![/bold green]")
        else:
            console.print("\n[bold red]Ocorreu um erro durante a limpeza.[/bold red]")
        input("\nPressione Enter para sair...")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrompido pelo usuário[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]Erro inesperado: {str(e)}[/bold red]")
        input("Pressione Enter para sair...")
