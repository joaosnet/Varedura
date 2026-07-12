"""
Legacy Rich interface for Varedura.

Usage:
    uv run main.py

Main entry point providing the Textual TUI, with a Rich legacy fallback.
"""

import os
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
from i18n import (
    t,
    init as i18n_init,
    set_language,
    get_language,
    get_supported_languages,
)
from cli.ui_shared import (
    CLEANUP_STEPS,
    STEP_WEIGHT,
    build_cleanup_steps_table,
    build_scanner_tables,
    get_cleanup_steps as _get_cleanup_steps,
    is_mcp_configured as _is_mcp_configured,
    load_cleanup_steps as _load_cleanup_steps,
    load_recording_pref as _load_recording_pref,
    save_cleanup_steps as _save_cleanup_steps,
    save_recording_pref as _save_recording_pref,
    toggle_mcp_config as _toggle_mcp_config_state,
)
from mascot.renderer import MascotRenderer
from mascot.frames import STATES, FRAMES

console = Console(record=True)
i18n_init()
mascot = MascotRenderer(console)

_recording_enabled = True
_session_recorder = None

# Animated emoji sequences for each menu item (cycled at ~2 fps)
_MENU_EMOJIS = {
    "network": ["🌐", "📡", "🛰️ ", "🔍"],
    "docker": ["🐳", "🧹", "🗑️ ", "♻️ "],
    "port": ["🔌", "🔎", "📊", "🎯"],
    "settings": ["⚙️ ", "🔧", "🛠️ ", "⚙️ "],
    "quit": ["👋", "🚪", "👋", "🚪"],
}


def show_cleanup_prefs(first_run: bool = False) -> dict[str, bool]:
    """Interactive toggle screen for cleanup step preferences.

    Shows a numbered list of steps the user can toggle ON/OFF.
    Returns the final step dict.
    """
    steps = _get_cleanup_steps()

    title_key = "cleanup_prefs.first_run_title" if first_run else "cleanup_prefs.title"

    while True:
        console.print(
            Panel(
                f"[bold cyan]{t(title_key)}[/]",
                style="blue",
            )
        )

        if first_run:
            console.print(f"\n[yellow]{t('cleanup_prefs.first_run_intro')}[/]\n")

        console.print(f"  [dim]{t('cleanup_prefs.instructions')}[/]\n")

        console.print(build_cleanup_steps_table(steps))

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
                label_key = CLEANUP_STEPS[idx][1]
                old_val = steps.get(key, False)
                steps[key] = not old_val
                console.print(
                    f"\n[green]✓ {t(label_key)}: {t('cleanup_prefs.on' if not old_val else 'cleanup_prefs.off')}[/]\n"
                )
        except (ValueError, IndexError):
            console.print(f"\n[red]{t('menu.invalid_option')}[/]\n")


def _toggle_mcp_config() -> None:
    """Add or remove the Varedura MCP server from .vscode/mcp.json."""
    for style, message in _toggle_mcp_config_state():
        prefix = "\n" if style in {"yellow", "cyan", "red"} else ""
        console.print(f"{prefix}[{style}]{message}[/]")


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
    menu.add_row(
        "S",
        f"{_emoji('settings')} {t('menu.option_settings')}",
        t("menu.desc_settings"),
    )
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


def _ensure_legacy_network_targets() -> bool:
    """Small Rich fallback for the shared schema-v3 target catalogue."""
    from cli.ui_shared import load_network_config, save_network_config
    from monitor.ping_targets import (
        MAX_PERSISTENT_TARGETS,
        TargetSelection,
        create_custom_target,
        target_catalog,
    )

    config = load_network_config()
    current = TargetSelection.from_config(config)
    if current.onboarding_completed and current.targets:
        return True

    catalog = target_catalog()
    table = Table(title=t("network.onboarding_title"), box=box.SIMPLE_HEAVY)
    table.add_column("#", justify="right")
    table.add_column(t("network.col_target"))
    table.add_column(t("network.custom_target"))
    for index, target in enumerate(catalog, 1):
        detail = target.warning or target.description
        table.add_row(str(index), target.label, f"{target.host} {detail}".strip())
    console.print(table)
    console.print(f"[dim]{t('network.targets_help')}[/]")
    raw = console.input(
        f"[cyan]1-{len(catalog)} (vírgulas) ou hostname/IP; Enter cancela:[/] "
    ).strip()
    if not raw:
        console.print(f"[yellow]{t('network.onboarding_deferred')}[/]")
        return False

    selected = []
    seen = set()
    for token in (part.strip() for part in raw.split(",")):
        try:
            if token.isdigit() and 1 <= int(token) <= len(catalog):
                target = catalog[int(token) - 1]
            else:
                target = create_custom_target(token)
        except ValueError as exc:
            console.print(f"[red]{exc}[/]")
            return False
        if target.id not in seen:
            selected.append(target)
            seen.add(target.id)
        if len(selected) > MAX_PERSISTENT_TARGETS:
            console.print(f"[red]{t('network.too_many_targets')}[/]")
            return False
    if not selected:
        return False
    primary_raw = console.input(
        f"[cyan]{t('network.primary_target')} (1-{len(selected)}, padrão 1):[/] "
    ).strip()
    primary_index = int(primary_raw) - 1 if primary_raw.isdigit() else 0
    if not 0 <= primary_index < len(selected):
        console.print(f"[red]{t('network.choose_primary')}[/]")
        return False
    selection = TargetSelection(
        tuple(selected),
        selected[primary_index].id,
        league_auto_detect=bool(config.get("league_auto_detect", True)),
        onboarding_completed=True,
    )
    config.update(selection.to_config())
    save_network_config(config)
    return True


def run_network_stalker():
    """Run the network stalker monitor."""
    try:
        if not _ensure_legacy_network_targets():
            return
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
    cleaner = None
    try:
        from docker_cleaner.core import WSLDockerCleaner
        from rich.progress import (
            Progress,
            TextColumn,
            BarColumn,
            TaskProgressColumn,
            TimeRemainingColumn,
        )

        cleaner = WSLDockerCleaner(console=console)

        # Map step keys to cleaner methods
        step_methods = {
            "containers": lambda: cleaner.docker_cleanup(prune_only="containers"),
            "images": lambda: cleaner.docker_cleanup(prune_only="images"),
            "volumes": lambda: cleaner.docker_cleanup(prune_only="volumes"),
            "networks": lambda: cleaner.docker_cleanup(prune_only="networks"),
            "builder": lambda: cleaner.docker_cleanup(prune_only="builder"),
            "stop_docker": cleaner.stop_docker_wsl,
            "wsl_sparse": cleaner.configure_wsl_sparse,
            "compact_vhdx": cleaner.compact_vhdx_files,
            "temp_files": cleaner.cleanup_temp_files,
            "recycle_bin": cleaner.cleanup_recycle_bin,
        }

        total_weight = sum(STEP_WEIGHT.get(k, 10) for k in enabled)

        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
        )

        failures = []
        with progress:
            task_id = progress.add_task(
                f"[cyan]{t('menu.starting_cleanup')}", total=total_weight
            )
            cleaner.silent_console = True
            try:
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
                            if method() is False:
                                failures.append(label)
                        except Exception as e:
                            failures.append(label)
                            console.print(f"[red]  {label}: {e}[/]")
                    progress.update(task_id, advance=STEP_WEIGHT.get(key, 10))
            finally:
                cleaner.silent_console = False

        success = not failures
        if failures:
            error_message = t("menu.error_during_cleanup", error=", ".join(failures))
            cleaner.log(error_message, "ERROR")
            console.print(f"[red]{error_message}[/]")
    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_cleaner', error=e)}[/]")
    except Exception as e:
        error_message = t("menu.error_during_cleanup", error=e)
        if cleaner:
            cleaner.log(error_message, "ERROR")
        console.print(f"[red]{error_message}[/]")
    finally:
        mascot.show_result(
            success, t("mascot.success") if success else t("mascot.error")
        )


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
        mascot.show_result(
            success, t("mascot.success") if success else t("mascot.error")
        )


def run_port_scanner():
    """Executa o escaner de portas standalone."""
    success = False
    try:
        from monitor.port_scanner import run_full_scan

        console.print(f"\n[bold cyan]{t('scanner.scanning')}[/]\n")
        state = run_full_scan()

        tcp_table, conn_table, summary_panel = build_scanner_tables(state)
        console.print(tcp_table)
        console.print(conn_table)
        console.print(summary_panel)
        success = True

    except ImportError as e:
        console.print(f"[red]{t('menu.error_loading_scanner', error=e)}[/]")
    except Exception as e:
        console.print(f"[red]{t('menu.error_during_scan', error=e)}[/]")
    finally:
        mascot.show_result(
            success, t("mascot.success") if success else t("mascot.error")
        )


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
        console.print(
            f"  [bold yellow]{i}[/] {lang_names.get(lang_code, lang_code)}{marker}"
        )
    console.print()
    choice = console.input("[bold cyan]> [/]").strip()
    langs = list(get_supported_languages())
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(langs):
            new_lang = set_language(langs[idx])
            console.print(
                f"\n[green]{t('lang.changed', lang=lang_names.get(new_lang, new_lang))}[/]"
            )
    except (ValueError, IndexError):
        pass


def show_settings():
    """Show the settings menu with all configurable options."""
    while True:
        # Current status
        rec_status_icon = "🔴" if _recording_enabled else "⚫"
        rec_status_text = (
            t("settings.rec_on") if _recording_enabled else t("settings.rec_off")
        )
        lang_names = {"pt": t("lang.pt"), "en": t("lang.en")}
        current_lang = lang_names.get(get_language(), get_language())
        mcp_configured = _is_mcp_configured()
        mcp_status_icon = "🟢" if mcp_configured else "⚫"
        mcp_status_text = t("mcp.status_on") if mcp_configured else t("mcp.status_off")

        cleanup_steps = _get_cleanup_steps()
        cleanup_count = sum(1 for v in cleanup_steps.values() if v)
        cleanup_summary = t(
            "cleanup_prefs.summary", count=cleanup_count, total=len(CLEANUP_STEPS)
        )

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

        menu.add_row(
            "1", f"{rec_status_icon} {t('settings.option_rec')}", t("settings.desc_rec")
        )
        menu.add_row("2", t("settings.option_lang"), t("settings.desc_lang"))
        menu.add_row("3", t("settings.option_cleanup"), t("settings.desc_cleanup"))
        menu.add_row("4", f"{mcp_status_icon} {t('mcp.option')}", t("mcp.desc"))
        menu.add_row("", "", "")
        menu.add_row("V", t("settings.back"), t("settings.desc_back"))

        console.print(Panel(menu, border_style="cyan"))
        console.print()

        choice = (
            console.input(f"[bold cyan]{t('menu.select_option')}[/]").strip().lower()
        )

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
    saved_label = (
        t("recorder.prompt_saved_on") if saved else t("recorder.prompt_saved_off")
    )

    console.print()
    console.print(
        Panel(
            f"[bold cyan]{t('recorder.prompt_question')}[/]\n\n"
            f"[yellow]{t('recorder.prompt_note')}[/]\n\n"
            f"[dim]{t('recorder.prompt_why')}[/]",
            title=t("recorder.prompt_title"),
            border_style="cyan",
        )
    )
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


def run_legacy_rich():
    """Run the original Rich-based interface."""
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
                console.print("\n[bold green]✓ LMArena[/]\n")
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


def main():
    """Main entry point."""
    argv = sys.argv[1:]
    use_legacy = (
        "--legacy-rich" in argv or os.environ.get("VAREDURA_UI", "").lower() == "rich"
    )
    if use_legacy:
        run_legacy_rich()
        return

    from cli.textual_app import run_textual_app

    run_textual_app()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        mascot.show_wave(t("mascot.goodbye"))
        sys.exit(0)
