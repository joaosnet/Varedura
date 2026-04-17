"""
Varedura - System Monitor & Docker Cleanup Tool

Usage:
    uv run main.py

Main entry point providing a Rich-based menu for all tools.
"""

import json
import sys
import threading
import itertools
from datetime import datetime
from pathlib import Path
from rich.columns import Columns
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich import box
from i18n import t, init as i18n_init, set_language, get_language, get_supported_languages
from mascot.renderer import MascotRenderer
from mascot.frames import STATES, FRAMES

console = Console(record=True)
i18n_init()
mascot = MascotRenderer(console)

_PREFS_FILE = Path.home() / ".varedura_prefs.json"
_MCP_CONFIG_FILE = Path(".vscode") / "mcp.json"
_recording_enabled = True
_session_recorder = None

# Animated emoji sequences for each menu item (cycled at ~2 fps)
_MENU_EMOJIS = {
    "network":  ["🌐", "📡", "🛰️ ", "🔍"],
    "docker":   ["🐳", "🧹", "🗑️ ", "♻️ "],
    "port":     ["🔌", "🔎", "📊", "🎯"],
    "settings": ["⚙️ ", "🔧", "🛠️ ", "⚙️ "],
    "quit":     ["👋", "🚪", "👋", "🚪"],
}

# All available cleanup steps with their i18n keys and default ON/OFF
CLEANUP_STEPS = [
    ("containers",   "cleanup_prefs.step_containers",  True),
    ("images",       "cleanup_prefs.step_images",       True),
    ("volumes",      "cleanup_prefs.step_volumes",      True),
    ("networks",     "cleanup_prefs.step_networks",     True),
    ("builder",      "cleanup_prefs.step_builder",      True),
    ("stop_docker",  "cleanup_prefs.step_stop_docker",  False),
    ("wsl_sparse",   "cleanup_prefs.step_wsl_sparse",   False),
    ("compact_vhdx", "cleanup_prefs.step_compact_vhdx", False),
    ("temp_files",   "cleanup_prefs.step_temp_files",   False),
    ("recycle_bin",  "cleanup_prefs.step_recycle_bin",   False),
]


def _load_prefs() -> dict:
    """Load all preferences from disk."""
    try:
        if _PREFS_FILE.exists():
            return json.loads(_PREFS_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _save_prefs(data: dict) -> None:
    """Save preferences to disk."""
    try:
        _PREFS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception:
        pass


def _load_recording_pref() -> bool:
    """Load recording preference from disk (default: enabled)."""
    return bool(_load_prefs().get("recording_enabled", True))


def _save_recording_pref(enabled: bool) -> None:
    """Save recording preference to disk."""
    data = _load_prefs()
    data["recording_enabled"] = enabled
    _save_prefs(data)


def _load_cleanup_steps() -> dict[str, bool] | None:
    """Load cleanup step preferences. Returns None if never configured."""
    data = _load_prefs()
    return data.get("cleanup_steps")


def _save_cleanup_steps(steps: dict[str, bool]) -> None:
    """Save cleanup step preferences."""
    data = _load_prefs()
    data["cleanup_steps"] = steps
    _save_prefs(data)


def _get_cleanup_steps() -> dict[str, bool]:
    """Get cleanup steps, using defaults if not yet configured."""
    saved = _load_cleanup_steps()
    if saved is not None:
        return saved
    return {key: default for key, _, default in CLEANUP_STEPS}


def show_cleanup_prefs(first_run: bool = False) -> dict[str, bool]:
    """Interactive toggle screen for cleanup step preferences.

    Shows a numbered list of steps the user can toggle ON/OFF.
    Returns the final step dict.
    """
    steps = _get_cleanup_steps()

    title_key = "cleanup_prefs.first_run_title" if first_run else "cleanup_prefs.title"

    while True:
        console.print(Panel(
            f"[bold cyan]{t(title_key)}[/]",
            style="blue",
        ))

        if first_run:
            console.print(f"\n[yellow]{t('cleanup_prefs.first_run_intro')}[/]\n")

        console.print(f"  [dim]{t('cleanup_prefs.instructions')}[/]\n")

        tbl = Table(box=box.ROUNDED, expand=True, show_header=False)
        tbl.add_column("#", style="bold yellow", width=4)
        tbl.add_column("", width=8)
        tbl.add_column("Step", style="white")

        for i, (key, label_key, _) in enumerate(CLEANUP_STEPS, 1):
            on = steps.get(key, False)
            icon = "[bold green]✓[/]" if on else "[dim]✗[/]"
            status = f"[green]{t('cleanup_prefs.on')}[/]" if on else f"[dim]{t('cleanup_prefs.off')}[/]"
            tbl.add_row(str(i), f"{icon} {status}", t(label_key))

        console.print(tbl)

        enabled_count = sum(1 for v in steps.values() if v)
        console.print(
            f"\n  [cyan]{t('cleanup_prefs.summary', count=enabled_count, total=len(CLEANUP_STEPS))}[/]\n"
        )

        choice = console.input(f"[bold cyan]{t('menu.select_option')}[/]").strip()

        if not choice:
            # Enter pressed — save and exit
            _save_cleanup_steps(steps)
            console.print(f"\n[green]{t('cleanup_prefs.saved')}[/]")
            return steps

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(CLEANUP_STEPS):
                key = CLEANUP_STEPS[idx][0]
                old_val = steps.get(key, False)
                steps[key] = not old_val
                console.print(f"\n[green]✓ {t(label_key)}: {t('cleanup_prefs.on' if not old_val else 'cleanup_prefs.off')}[/]\n")
        except (ValueError, IndexError):
            console.print(f"\n[red]{t('menu.invalid_option')}[/]\n")


def _is_mcp_configured() -> bool:
    """Check if the MCP server config exists for this workspace."""
    try:
        if _MCP_CONFIG_FILE.exists():
            data = json.loads(_MCP_CONFIG_FILE.read_text(encoding="utf-8"))
            return "varedura" in data.get("servers", {})
    except Exception:
        pass
    return False


def _toggle_mcp_config() -> None:
    """Add or remove the Varedura MCP server from .vscode/mcp.json."""
    try:
        if _is_mcp_configured():
            # Remove config
            data = json.loads(_MCP_CONFIG_FILE.read_text(encoding="utf-8"))
            data.get("servers", {}).pop("varedura", None)
            if not data.get("servers"):
                _MCP_CONFIG_FILE.unlink(missing_ok=True)
            else:
                _MCP_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
            console.print(f"\n[yellow]{t('mcp.removed')}[/]")
        else:
            # Add config
            console.print(f"\n[cyan]{t('mcp.installing')}[/]")
            _MCP_CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

            data = {}
            if _MCP_CONFIG_FILE.exists():
                try:
                    data = json.loads(_MCP_CONFIG_FILE.read_text(encoding="utf-8"))
                except Exception:
                    data = {}

            data.setdefault("servers", {})
            data["servers"]["varedura"] = {
                "type": "stdio",
                "command": "uv",
                "args": ["run", "python", "-m", "mcp_server"],
            }
            _MCP_CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

            console.print(f"[green]{t('mcp.installed')}[/]")
            console.print(f"[dim]{t('mcp.config_path', path=str(_MCP_CONFIG_FILE.resolve()))}[/]")
            console.print(f"[dim]{t('mcp.usage_hint')}[/]")
            console.print(f"[dim]{t('mcp.run_hint')}[/]")
    except Exception as e:
        console.print(f"[red]{t('mcp.error', error=str(e))}[/]")


def _build_menu_layout(mascot_panel: Panel, frame_idx: int = 0) -> Columns:
    """Build the full menu layout with a given mascot panel."""
    def _emoji(key: str) -> str:
        seq = _MENU_EMOJIS[key]
        return seq[frame_idx % len(seq)]

    header = Table.grid(expand=True)
    header.add_column(justify="center")
    header.add_row(f"[bold cyan]{t('menu.title')}[/]")
    header.add_row(f"[dim]{t('menu.subtitle')}[/]")

    menu = Table(box=box.ROUNDED, expand=True, show_header=False)
    menu.add_column("Key", style="bold yellow", width=5)
    menu.add_column("Option", style="white")
    menu.add_column("Description", style="dim")

    menu.add_row("1", f"{_emoji('network')} {t('menu.option_1')}", t("menu.desc_1"))
    menu.add_row("2", f"{_emoji('docker')} {t('menu.option_2')}", t("menu.desc_2"))
    menu.add_row("3", f"{_emoji('port')} {t('menu.option_3')}", t("menu.desc_3"))
    menu.add_row("", "", "")
    menu.add_row("S", f"{_emoji('settings')} {t('menu.option_settings')}", t("menu.desc_settings"))
    menu.add_row("Q", f"{_emoji('quit')} {t('menu.quit')}", t("menu.quit_desc"))

    menu_panel = Panel(menu, title=t("menu.tools"), border_style="cyan")

    return Group(
        Panel(header, style="blue"),
        "",
        Columns([mascot_panel, menu_panel], expand=True, padding=(0, 2)),
        "",
        f"[bold cyan]{t('menu.select_option')}[/]",
    )


def show_animated_menu() -> str:
    """Display the main menu with a continuously animated mascot.

    Returns the user's menu choice. The mascot cycles through idle
    frames at ~2 fps while waiting for input.
    """
    frames = FRAMES.get(STATES.IDLE, FRAMES[STATES.IDLE])
    frame_cycle = itertools.cycle(frames)
    message = t("mascot.welcome")

    # Shared state for the input thread
    user_input: list[str] = []
    input_ready = threading.Event()

    def _read_input() -> None:
        try:
            line = input()
        except EOFError:
            line = "q"
        user_input.append(line.strip().lower())
        input_ready.set()

    input_thread = threading.Thread(target=_read_input, daemon=True)

    with Live(console=console, refresh_per_second=2, screen=True) as live:
        input_thread.start()
        frame_idx = 0
        while not input_ready.is_set():
            frame_path = next(frame_cycle)
            mascot_panel = mascot.render_static_from_path(frame_path, message)
            layout = _build_menu_layout(mascot_panel, frame_idx)
            live.update(layout)
            frame_idx += 1
            input_ready.wait(timeout=0.5)

    return user_input[0] if user_input else ""


def _start_recording_session():
    """Start recording the current user session if enabled."""
    if not _recording_enabled:
        return None
    try:
        from recorder.session_recorder import SessionRecorder
        recorder = SessionRecorder(console=console, width=console.width)
        recorder.start()
        console.print(f"[dim]{t('recorder.recording_started')}[/]")
        return recorder
    except Exception:
        return None


def _stop_recording_session(recorder):
    """Stop session recording and save a single GIF for the whole run."""
    if recorder is None:
        return
    try:
        recorder.stop()
        console.print(f"[dim]{t('recorder.recording_stopped')}[/]")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        recordings_dir = Path("recordings")
        recordings_dir.mkdir(exist_ok=True)

        # Save GIF
        gif_path = recorder.save_gif(recordings_dir / f"session_{timestamp}.gif")
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
    try:
        mascot.show_result(True, t("mascot.scanning"))
        from monitor.stalker import main as stalker_main

        stalker_main(external_console=console, session_recorder=_session_recorder)
    except KeyboardInterrupt:
        pass
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_stalker', error=e)}[/]")
        mascot.show_result(False, t("mascot.error"))


def run_docker_cleanup():
    """Run Docker cleanup using the user's saved step preferences.

    On first run (no prefs saved), shows the cleanup wizard first.
    """
    # First-run wizard if cleanup steps were never configured
    if _load_cleanup_steps() is None:
        show_cleanup_prefs(first_run=True)
        console.input(f"\n[dim]{t('menu.press_enter')}[/]")

    steps = _get_cleanup_steps()
    enabled = [k for k, v in steps.items() if v]

    if not enabled:
        console.print(f"\n[yellow]{t('menu.no_steps_enabled')}[/]")
        console.print(f"[dim]{t('menu.configure_steps_hint')}[/]\n")
        console.input(f"[dim]{t('menu.press_enter')}[/]")
        return

    success = False
    try:
        from docker_cleaner.core import WSLDockerCleaner
        from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn

        cleaner = WSLDockerCleaner(console=console)

        # Map step keys to cleaner methods
        step_methods = {
            "containers":   lambda: cleaner.docker_cleanup(prune_only="containers"),
            "images":       lambda: cleaner.docker_cleanup(prune_only="images"),
            "volumes":      lambda: cleaner.docker_cleanup(prune_only="volumes"),
            "networks":     lambda: cleaner.docker_cleanup(prune_only="networks"),
            "builder":      lambda: cleaner.docker_cleanup(prune_only="builder"),
            "stop_docker":  cleaner.stop_docker_wsl,
            "wsl_sparse":   cleaner.configure_wsl_sparse,
            "compact_vhdx": cleaner.compact_vhdx_files,
            "temp_files":   cleaner.cleanup_temp_files,
            "recycle_bin":  cleaner.cleanup_recycle_bin,
        }

        step_weight = {
            "containers": 10, "images": 15, "volumes": 10, "networks": 5,
            "builder": 10, "stop_docker": 15, "wsl_sparse": 10,
            "compact_vhdx": 20, "temp_files": 10, "recycle_bin": 5,
        }

        total_weight = sum(step_weight.get(k, 10) for k in enabled)

        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        )

        with progress:
            task_id = progress.add_task(
                f"[cyan]{t('menu.starting_cleanup')}", total=total_weight
            )
            cleaner.silent_console = True
            for key in enabled:
                # Find label
                label = key
                for k, lbl_key, _ in CLEANUP_STEPS:
                    if k == key:
                        label = t(lbl_key)
                        break
                progress.update(task_id, description=f"[cyan]{label}")
                method = step_methods.get(key)
                if method:
                    try:
                        method()
                    except Exception as e:
                        console.print(f"[red]  {label}: {e}[/]")
                progress.update(task_id, advance=step_weight.get(key, 10))
            cleaner.silent_console = False

        success = True
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_cleaner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_cleanup', error=e)}[/]")
    finally:
        mascot.show_result(success, t("mascot.success") if success else t("mascot.error"))


def run_lmarena_models():
    """Run LMArena models generator."""
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


def run_port_scanner():
    """Executa o escaner de portas standalone."""
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


def toggle_recording():
    """Toggle automatic GIF recording."""
    global _recording_enabled, _session_recorder
    _recording_enabled = not _recording_enabled
    _save_recording_pref(_recording_enabled)
    if _recording_enabled:
        if _session_recorder is None:
            _session_recorder = _start_recording_session()
        console.print(f"\n[green]{t('recorder.toggle_on')}[/]")
    else:
        if _session_recorder is not None:
            _stop_recording_session(_session_recorder)
            _session_recorder = None
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


def show_settings():
    """Show the settings menu with all configurable options."""
    while True:
        # Current status
        rec_status_icon = "🔴" if _recording_enabled else "⚫"
        rec_status_text = t("settings.rec_on") if _recording_enabled else t("settings.rec_off")
        lang_names = {"pt": t("lang.pt"), "en": t("lang.en")}
        current_lang = lang_names.get(get_language(), get_language())
        mcp_configured = _is_mcp_configured()
        mcp_status_icon = "🟢" if mcp_configured else "⚫"
        mcp_status_text = t("mcp.status_on") if mcp_configured else t("mcp.status_off")

        cleanup_steps = _get_cleanup_steps()
        cleanup_count = sum(1 for v in cleanup_steps.values() if v)
        cleanup_summary = t("cleanup_prefs.summary", count=cleanup_count, total=len(CLEANUP_STEPS))

        # Header
        header = Table.grid(expand=True)
        header.add_column(justify="center")
        header.add_row(f"[bold cyan]{t('settings.title')}[/]")
        console.print(Panel(header, style="blue"))
        console.print()

        status = Table(box=box.SIMPLE, show_header=True, expand=True)
        status.add_column(t("settings.current_status"), style="bold cyan")
        status.add_column("", style="white")
        status.add_row(t("settings.option_rec"), f"{rec_status_icon} {rec_status_text}")
        status.add_row(t("settings.option_lang"), f"🌐 {current_lang}")
        status.add_row(t("settings.option_cleanup"), f"🐳 {cleanup_summary}")
        status.add_row(t("mcp.option"), f"{mcp_status_icon} {mcp_status_text}")
        console.print(Panel(status, border_style="dim"))
        console.print()

        # Options
        menu = Table(box=box.ROUNDED, expand=True, show_header=False)
        menu.add_column("Key", style="bold yellow", width=5)
        menu.add_column("Option", style="white")
        menu.add_column("Description", style="dim")

        menu.add_row("1", f"{rec_status_icon} {t('settings.option_rec')}", t("settings.desc_rec"))
        menu.add_row("2", t("settings.option_lang"), t("settings.desc_lang"))
        menu.add_row("3", t("settings.option_cleanup"), t("settings.desc_cleanup"))
        menu.add_row("4", f"{mcp_status_icon} {t('mcp.option')}", t("mcp.desc"))
        menu.add_row("", "", "")
        menu.add_row("V", t("settings.back"), t("settings.desc_back"))

        console.print(Panel(menu, border_style="cyan"))
        console.print()

        choice = console.input(f"[bold cyan]{t('menu.select_option')}[/]").strip().lower()

        if choice == "1":
            console.print(f"\n[bold yellow]→ {t('settings.option_rec')}[/]")
            toggle_recording()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "2":
            console.print(f"\n[bold yellow]→ {t('settings.option_lang')}[/]")
            change_language()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "3":
            console.print(f"\n[bold yellow]→ {t('settings.option_cleanup')}[/]")
            show_cleanup_prefs()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "4":
            console.print(f"\n[bold yellow]→ {t('mcp.option')}[/]")
            _toggle_mcp_config()
            console.input(f"\n[dim]{t('menu.press_enter')}[/]")
        elif choice == "v":
            break
        else:
            console.print(f"[red]{t('menu.invalid_option')}[/]")
            console.input(f"[dim]{t('menu.press_enter_short')}[/]")


def _ask_recording_prompt() -> bool:
    """Show a startup prompt asking whether to record the session as GIF.

    Returns True to enable recording, False for streaming.
    """
    saved = _load_recording_pref()
    saved_label = t("recorder.prompt_saved_on") if saved else t("recorder.prompt_saved_off")

    console.print()
    console.print(Panel(
        f"[bold cyan]{t('recorder.prompt_question')}[/]\n\n"
        f"[yellow]{t('recorder.prompt_note')}[/]\n\n"
        f"[dim]{t('recorder.prompt_why')}[/]",
        title=t("recorder.prompt_title"),
        border_style="cyan",
    ))
    console.print()
    console.print(f"  {t('recorder.prompt_options', pref=saved_label)}")
    console.print()

    answer = console.input("[bold cyan]> [/]").strip().lower()

    if answer in ("y", "s"):
        return True
    elif answer == "n":
        return False
    else:
        return saved


def main():
    """Main entry point."""
    global _recording_enabled, _session_recorder
    _recording_enabled = _ask_recording_prompt()
    _save_recording_pref(_recording_enabled)

    if _recording_enabled:
        console.print(f"\n[green]{t('recorder.chosen_recording')}[/]\n")
        _session_recorder = _start_recording_session()
    else:
        console.print(f"\n[green]{t('recorder.chosen_streaming')}[/]\n")
        _session_recorder = None

    try:
        while True:
            choice = show_animated_menu()

            if choice == "1":
                console.print(f"\n[bold green]✓ {t('menu.option_1')}[/]\n")
                run_network_stalker()
                console.input(f"\n[dim]{t('menu.press_enter')}[/]")
            elif choice == "2":
                console.print(f"\n[bold green]✓ {t('menu.option_2')}[/]\n")
                run_docker_cleanup()
                console.input(f"\n[dim]{t('menu.press_enter')}[/]")
            elif choice == "3":
                console.print(f"\n[bold green]✓ {t('menu.option_3')}[/]\n")
                run_port_scanner()
                console.input(f"\n[dim]{t('menu.press_enter')}[/]")
            elif choice == "lmarena":
                console.print(f"\n[bold green]✓ LMArena[/]\n")
                run_lmarena_models()
                console.input(f"\n[dim]{t('menu.press_enter')}[/]")
            elif choice == "s":
                console.print(f"\n[bold green]✓ {t('menu.option_settings')}[/]\n")
                show_settings()
            elif choice == "q":
                mascot.show_wave(t("mascot.goodbye"))
                break
            else:
                console.print(f"[red]{t('menu.invalid_option')}[/]")
                console.input(f"[dim]{t('menu.press_enter_short')}[/]")
    finally:
        if _session_recorder is not None:
            _stop_recording_session(_session_recorder)
            _session_recorder = None
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        mascot.show_wave(t("mascot.goodbye"))
        sys.exit(0)
