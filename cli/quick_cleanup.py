"""Entrypoint CLI para executar a limpeza rápida do WSL Docker."""

from rich.console import Console
from typing import Optional
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.live import Live
import subprocess
import os
import sys
import shutil
import time
from i18n import t

IS_WINDOWS = sys.platform.startswith("win")


def run_cmd(console, cmd, desc=""):
    if desc:
        console.print(f"\n[bold blue][{t('quick.info')}][/bold blue] {desc}")
    console.print(f"[yellow]{t('quick.executing', cmd=cmd)}[/yellow]")
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=180
        )
        if result.stdout:
            console.print(f"[green]{t('quick.output', output=result.stdout.strip())}[/green]")
        if result.stderr and result.returncode != 0:
            console.print(f"[red]{t('quick.error', error=result.stderr.strip())}[/red]")
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        console.print(f"[red]{t('quick.timeout')}[/red]")
        return False
    except Exception as e:
        console.print(f"[red]{t('quick.error', error=str(e))}[/red]")
        return False


def quick_cleanup(console: Optional[Console] = None):
    """Perform a quick cleanup. If a `console` is provided, use it for output."""
    if console is None:
        console = Console()
    overall_progress = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    )
    current_task_progress = Progress(TextColumn("{task.description}"), console=console)
    from rich.console import Group

    progress_group = Group(Panel(Group(current_task_progress)), overall_progress)
    overall_task = overall_progress.add_task(
        f"[cyan]{t('quick.running_quick')}", total=100
    )
    with Live(progress_group, refresh_per_second=10, console=console):
        try:
            current_task = current_task_progress.add_task(t("quick.cleaning_docker"))
            overall_progress.update(
                overall_task, description=f"[cyan]{t('quick.cleaning_docker')}"
            )
            run_cmd(
                console,
                "docker system prune -af --volumes",
                t("quick.cleaning_docker_aggressive"),
            )
            current_task_progress.remove_task(current_task)
            overall_progress.update(overall_task, advance=40)

            current_task = current_task_progress.add_task(t("quick.stopping_docker_wsl"))
            overall_progress.update(
                overall_task, description=f"[cyan]{t('quick.stopping_docker_wsl')}"
            )
            if IS_WINDOWS:
                run_cmd(
                    console,
                    'taskkill /F /IM "Docker Desktop.exe" /T 2>NUL',
                    t("quick.stopping_docker_desktop"),
                )
                time.sleep(3)
                run_cmd(console, "wsl --shutdown", t("quick.stopping_wsl"))
            else:
                if shutil.which("systemctl"):
                    run_cmd(console, "sudo systemctl stop docker", t("quick.stopping_docker_desktop"))
                else:
                    run_cmd(console, "sudo killall Docker com.docker.hyperkit dockerd 2>/dev/null || true",
                            t("quick.stopping_docker_desktop"))
            time.sleep(5)
            current_task_progress.remove_task(current_task)
            overall_progress.update(overall_task, advance=30)

            current_task = current_task_progress.add_task(t("quick.compacting_vhdx"))
            overall_progress.update(
                overall_task, description=f"[cyan]{t('quick.compacting_vhdx')}"
            )
            if IS_WINDOWS:
                vhdx_path = os.path.expandvars(r"%LOCALAPPDATA%\Docker\wsl\data\ext4.vhdx")
                if os.path.exists(vhdx_path):
                    size_before = os.path.getsize(vhdx_path) / (1024**3)
                    console.print(f"\n[bold]{t('quick.size_before', size=f'{size_before:.2f}')}[/bold]")
                    ps_cmd = f'Optimize-VHD -Path "{vhdx_path}" -Mode Full'
                    if run_cmd(
                        console,
                        f'powershell -Command "{ps_cmd}"',
                        t("quick.compacting_vhdx_desc"),
                    ):
                        time.sleep(5)
                        if os.path.exists(vhdx_path):
                            size_after = os.path.getsize(vhdx_path) / (1024**3)
                            space_saved = size_before - size_after
                            console.print(f"[bold]{t('quick.size_after', size=f'{size_after:.2f}')}[/bold]")
                            console.print(
                                f"[bold]{t('quick.space_saved', size=f'{space_saved:.2f}')}[/bold]"
                            )
                else:
                    console.print(
                        f"[yellow]{t('quick.vhdx_not_found', path=vhdx_path)}[/yellow]"
                    )
            else:
                console.print(f"[dim]{t('cleanup.vhdx_windows_only')}[/dim]")
            current_task_progress.remove_task(current_task)
            overall_progress.update(overall_task, advance=30)
            overall_progress.update(
                overall_task, description=f"[green]{t('quick.cleanup_done')}"
            )
        except Exception as e:
            console.print(f"[red]{t('quick.cleanup_error', error=str(e))}[/red]")
            return False
    console.print(f"\n[bold green]{t('quick.cleanup_complete')}[/bold green]")
    console.print(f"[bold]{t('quick.restart_docker')}[/bold]")
    return True


if __name__ == "__main__":
    console = Console()
    try:
        success = quick_cleanup()
        if success:
            console.print(f"\n[bold green]{t('quick.success')}[/bold green]")
        else:
            console.print(f"\n[bold red]{t('quick.failure')}[/bold red]")
        input(f"\n{t('quick.press_enter')}")
    except KeyboardInterrupt:
        console.print(f"\n[bold yellow]{t('quick.interrupted')}[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]{t('quick.unexpected_error', error=str(e))}[/bold red]")
        input(t("quick.press_enter"))
