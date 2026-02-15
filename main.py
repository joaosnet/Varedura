"""
Varedura - System Monitor & Docker Cleanup Tool

Usage:
    uv run main.py

Main entry point providing a Rich-based menu for all tools.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from i18n import t, init as i18n_init, set_language, get_language, get_supported_languages
from mascot.renderer import MascotRenderer
from mascot.frames import STATES

console = Console()
i18n_init()
mascot = MascotRenderer(console)

_PREFS_FILE = Path.home() / ".varedura_prefs.json"
_recording_enabled = True


def _load_recording_pref() -> bool:
    """Load recording preference from disk (default: enabled)."""
    try:
        if _PREFS_FILE.exists():
            data = json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
            return bool(data.get("recording_enabled", True))
    except Exception:
        pass
    return True


def _save_recording_pref(enabled: bool) -> None:
    """Save recording preference to disk."""
    try:
        data = {}
        if _PREFS_FILE.exists():
            data = json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
        data["recording_enabled"] = enabled
        _PREFS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def show_menu():
    """Display the main menu with mascot."""
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
    rec_status = "🔴" if _recording_enabled else "⚫"
    menu.add_row("R", f"{rec_status} {t('menu.option_rec')}", t("menu.desc_rec"))
    menu.add_row("L", t("menu.option_lang"), t("menu.desc_lang"))
    menu.add_row("Q", t("menu.quit"), t("menu.quit_desc"))

    menu_panel = Panel(menu, title=t("menu.tools"), border_style="cyan")

    # Show mascot alongside menu
    mascot_panel = mascot.render_static(STATES.IDLE, t("mascot.welcome"))
    console.print(Columns([mascot_panel, menu_panel], expand=True, padding=(0, 2)))
    console.print()


def _start_recording(tool_name: str):
    """Start recording a tool session if enabled."""
    if not _recording_enabled:
        return None
    try:
        from recorder.session_recorder import SessionRecorder
        recorder = SessionRecorder()
        recorder.start()
        console.print(f"[dim]{t('recorder.recording_started')}[/]")
        return recorder
    except Exception:
        return None


def _stop_recording(recorder, tool_name: str):
    """Stop recording and save GIF. Also updates screenshots/demo.gif for README."""
    if recorder is None:
        return
    try:
        recorder.stop()
        console.print(f"[dim]{t('recorder.recording_stopped')}[/]")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        recordings_dir = Path("recordings")
        recordings_dir.mkdir(exist_ok=True)

        # Save SVG (always works)
        svg_path = recorder.save_svg(recordings_dir / f"{tool_name}_{timestamp}.svg")
        if svg_path:
            console.print(f"[green]{t('recorder.svg_saved', path=str(svg_path))}[/]")

        # Try to save GIF
        gif_path = recorder.save_gif(recordings_dir / f"{tool_name}_{timestamp}.gif")
        if gif_path:
            console.print(f"[green]{t('recorder.gif_saved', path=str(gif_path))}[/]")

            # Auto-update screenshots/demo.gif for README
            import shutil
            demo_dir = Path("screenshots")
            demo_dir.mkdir(exist_ok=True)
            demo_gif = demo_dir / "demo.gif"
            shutil.copy2(gif_path, demo_gif)
            console.print(f"[dim]{t('recorder.demo_updated', path=str(demo_gif))}[/]")
    except Exception as e:
        console.print(f"[dim]{t('recorder.gif_error', error=str(e))}[/]")


def run_network_stalker():
    """Run the network stalker monitor."""
    recorder = _start_recording("network_stalker")
    try:
        mascot.show_result(True, t("mascot.scanning"))
        from monitor.stalker import main as stalker_main

        stalker_main()
    except KeyboardInterrupt:
        pass
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_stalker', error=e)}[/]")
        mascot.show_result(False, t("mascot.error"))
    finally:
        _stop_recording(recorder, "network_stalker")


def run_docker_cleanup():
    """Run quick Docker cleanup."""
    recorder = _start_recording("docker_cleanup")
    success = False
    try:
        from docker_cleaner.core import WSLDockerCleaner

        cleaner = WSLDockerCleaner()
        cleaner.docker_cleanup()
        success = True
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_cleaner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_cleanup', error=e)}[/]")
    finally:
        mascot.show_result(success, t("mascot.success") if success else t("mascot.error"))
        _stop_recording(recorder, "docker_cleanup")


def run_docker_full_cleanup():
    """Run full Docker cleanup with VHDX compaction."""
    recorder = _start_recording("docker_full_cleanup")
    success = False
    try:
        from docker_cleaner.core import WSLDockerCleaner

        cleaner = WSLDockerCleaner()
        cleaner.run_full_cleanup_with_progress()
        success = True
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_cleaner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_cleanup', error=e)}[/]")
    finally:
        mascot.show_result(success, t("mascot.success") if success else t("mascot.error"))
        _stop_recording(recorder, "docker_full_cleanup")


def run_lmarena_models():
    """Run LMArena models generator."""
    recorder = _start_recording("lmarena")
    success = False
    try:
        from lmarena.generator import main as generator_main

        generator_main()
        success = True
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_lmarena', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_generating_models', error=e)}[/]")
    finally:
        mascot.show_result(success, t("mascot.success") if success else t("mascot.error"))
        _stop_recording(recorder, "lmarena")


def run_port_scanner():
    """Executa o escaner de portas standalone."""
    recorder = _start_recording("port_scanner")
    success = False
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
        success = True

    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_scanner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_scan', error=e)}[/]")
    finally:
        mascot.show_result(success, t("mascot.success") if success else t("mascot.error"))
        _stop_recording(recorder, "port_scanner")


def toggle_recording():
    """Toggle automatic GIF recording."""
    global _recording_enabled
    _recording_enabled = not _recording_enabled
    _save_recording_pref(_recording_enabled)
    if _recording_enabled:
        console.print(f"\n[green]{t('recorder.toggle_on')}[/]")
    else:
        console.print(f"\n[yellow]{t('recorder.toggle_off')}[/]")


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
    global _recording_enabled
    _recording_enabled = _load_recording_pref()

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
        elif choice == "r":
            toggle_recording()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "l":
            change_language()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "q":
            mascot.show_wave(t("mascot.goodbye"))
            sys.exit(0)
        else:
            console.print(f"[red]{t('menu.invalid_option')}[/]")
            console.input(f"[dim]{t('menu.press_enter_short')}[/]")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        mascot.show_wave(t("mascot.goodbye"))
        sys.exit(0)
