"""
Textual UI launcher for the Docker-Clennear tools.

Usage:
    python main.py

This TUI allows running the quick cleanup, full cleanup, and the LMArena models generator
from a unified interface. Long-running tasks are executed as subprocesses and their output
is shown in the builtin `Log` widget.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import List

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Button, Static, Input, Label, RichLog, Checkbox, LoadingIndicator
from textual.screen import Screen
from textual import work
from textual.worker import Worker, WorkerState
from typing import Callable
from rich.console import Console as RichConsole
from rich.progress import Progress as RichProgress, BarColumn, TextColumn, TaskProgressColumn
from cli.richlog import DailyLogWriter
import logging
import sys


class ConfirmScreen(Screen):
    """Small modal screen for confirmation prompts."""

    def __init__(self, message: str = "Confirm?") -> None:
        super().__init__()
        self.message = message
        self.result = False

    def compose(self) -> ComposeResult:
        yield Static(f"[bold yellow]{self.message}[/bold yellow]")
        with Horizontal():
            yield Button("Confirmar", id="confirm_yes")
            yield Button("Cancelar", id="confirm_no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "confirm_yes":
            self.result = True
        else:
            self.result = False
        self.dismiss()


class CleanupOptionsScreen(Screen):
    """Modal screen offering several cleanup options via checkboxes.

    Use defaults by passing a dict of checkbox ids -> bool.
    The selected values will be available in `self.selected_options` after dismiss.
    """

    def __init__(self, message: str = "Cleanup options", defaults: dict | None = None) -> None:
        super().__init__()
        self.message = message
        self.result = False
        self.defaults = defaults or {}
        self.selected_options: dict = {}

    def compose(self) -> ComposeResult:
        with Container():
            yield Static(f"[bold yellow]{self.message}[/bold yellow]")
            # Place the large list of options in a scrollable vertical area so footer buttons remain visible
            with VerticalScroll(id="opts_body"):
                # Checkboxes for the available granular cleanup steps
                yield Checkbox("Parar Dockers e WSL (taskkill + wsl --shutdown)", id="opt_stop_wsl")
                yield Checkbox("Prune containers (docker container prune -f)", id="opt_prune_containers")
                yield Checkbox("Prune images (docker image prune -af)", id="opt_prune_images")
                yield Checkbox("Prune volumes (docker volume prune -f)", id="opt_prune_volumes")
                yield Checkbox("Prune networks (docker network prune -f)", id="opt_prune_networks")
                yield Checkbox("Prune builder cache (docker builder prune -af)", id="opt_prune_builder")
                yield Checkbox("Prune system (docker system prune -af --volumes)", id="opt_prune_system")
                yield Checkbox("Configurar sparse (WSL)", id="opt_configure_sparse")
                yield Checkbox("Compactar VHDX (admin)", id="opt_compact_vhdx")
                yield Checkbox("Limpar arquivos temporários", id="opt_cleanup_temp")
            # Preset buttons to quickly set common combos — outside scroll area
            with Horizontal(id="opts_presets"):
                yield Button("Quick", id="opts_preset_quick", variant="success")
                yield Button("Full", id="opts_preset_full", variant="warning")
                yield Button("Limpar Seleção", id="opts_clear", variant="error")
            # Footer controls — always visible at the bottom of the modal
            with Horizontal(id="opts_footer"):
                yield Button("Executar", id="opts_exec", variant="primary")
                yield Button("Salvar Preferências", id="opts_save")
                yield Button("Cancelar", id="opts_cancel")

    def on_mount(self) -> None:
        # Initialize default checkbox state
        for chk_id, val in self.defaults.items():
            try:
                chk = self.query_one(f"#{chk_id}", Checkbox)
                chk.value = bool(val)
            except Exception:
                pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "opts_cancel":
            self.result = False
            self.selected_options = {}
            self.dismiss()
            return
        
        # Preset handling: set specific checkboxes
        if event.button.id == "opts_preset_quick":
            # set containers/images/volumes True, others False
            for chk in self.query(Checkbox):
                if chk.id in ("opt_prune_containers", "opt_prune_images", "opt_prune_volumes"):
                    chk.value = True
                else:
                    chk.value = False
            return
        
        if event.button.id == "opts_preset_full":
            for chk in self.query(Checkbox):
                chk.value = True
            return
        
        if event.button.id == "opts_clear":
            for chk in self.query(Checkbox):
                chk.value = False
            return
        
        # Save selected options as default preferences
        if event.button.id == "opts_save":
            opts = {chk.id: chk.value for chk in self.query(Checkbox)}
            # Persist to user home
            try:
                import json
                config_path = Path.home() / ".docker_clennear_prefs.json"
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(opts, f, indent=2)
                # If hosted under an app with write_ui_log, use it
                try:
                    getattr(self.app, "write_ui_log", lambda *_: None)(f"Preferências salvas em: {config_path}")
                except Exception:
                    pass
                # Don't dismiss, let user continue selecting or execute
                return
            except Exception as e:
                try:
                    getattr(self.app, "write_ui_log", lambda *_: None)(f"Erro ao salvar preferências: {e}")
                except Exception:
                    pass
                return
        
        # Execute button - collect checkbox values and dismiss with result=True
        if event.button.id == "opts_exec":
            opts = {}
            for chk in self.query(Checkbox):
                opts[chk.id] = chk.value
            self.selected_options = opts
            self.result = True
            self.dismiss()
            return


class CommandRunnerApp(App[None]):
    CSS = """
    #layout
    Horizontal {
        height: 1fr;
    }
    #sidebar {
        width: 30;
        padding: 1 1;
        border: heavy $accent;
    }
    #main {
        width: 1fr;
        padding: 1 1;
        layout: vertical;
    }
    #log {
        height: 10;
        min-height: 8;
        border: solid $surface;
    }
    #progress {
        height: 3;
        padding: 0 1;
        border: heavy $accent;
    }
    LoadingIndicator.hidden {
        display: none;
    }
    #menu_title, #details_title {
        content-align: center middle;
        padding: 0 1;
        border-bottom: dashed $accent;
    }
    
    /* CleanupOptionsScreen styles */
    CleanupOptionsScreen {
        align: center middle;
    }
    CleanupOptionsScreen > Static {
        width: 100%;
        text-align: center;
        padding: 1;
        background: $boost;
    }
    #opts_body {
        width: 100%;
        height: 1fr;
        border: solid $primary;
        padding: 1 2;
        margin: 1 0;
    }
    #opts_body Checkbox {
        margin: 0 0 1 0;
    }
    #opts_presets {
        width: 100%;
        height: auto;
        padding: 1;
        margin: 1 0;
    }
    #opts_footer {
        width: 100%;
        height: auto;
        dock: bottom;
        padding: 1;
        background: $panel;
    }
    #opts_footer Button {
        margin: 0 1;
    }
    """

    TITLE = "Docker-Clennear UI"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("[bold]Ações Disponíveis[/bold]", id="menu_title")
                
                # Indicador de privilégios de admin
                try:
                    import ctypes
                    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                    admin_status = "[green]✓ Admin[/green]" if is_admin else "[yellow]⚠ Sem Admin[/yellow]"
                    yield Static(f"Status: {admin_status}", id="admin_status")
                except Exception:
                    pass
                
                yield Button("Limpeza Docker", id="docker_cleanup")
                yield Button("Opções de Limpeza", id="docker_options")
                yield Button("LMArena: Gerar Models", id="models_generator")
                yield Button("Abrir pasta de logs", id="open_logs")
                yield Button("Limpar logs UI", id="clear_logs")
                yield Button("Sair", id="exit")
            with VerticalScroll(id="main"):
                yield Static("[bold]Detalhes / Controles[/bold]", id="details_title")
                yield Label("Selecione uma ação à esquerda e use os botões abaixo para rodar.")
                default_models = "lmarena_models.txt" if Path("lmarena_models.txt").exists() else ""
                yield Input(value=default_models, placeholder="Caminho do arquivo para models (ex: lmarena_models.txt)", id="models_path")
                yield Button("Executar Generator", id="run_models")
                yield Static("Progresso:")
                yield Static("", id="progress")
                yield LoadingIndicator(id="spinner", classes="hidden")
                yield Static("Logs de saída:")
                yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "exit":
            self.exit()
            return
        if button_id == "docker_cleanup":
            # Single-command: run the full cleanup by default
            self.write_ui_log("Executando Limpeza Docker Completa (elevada, pode exigir admin)...")
            self._run_full_cleanup()
            return
        if button_id == "docker_options":
            # Present the options screen with sensible defaults
            # Try load saved preferences from file
            defaults = {
                "opt_stop_wsl": False,
                "opt_prune_containers": True,
                "opt_prune_images": True,
                "opt_prune_volumes": True,
                "opt_prune_networks": False,
                "opt_prune_builder": False,
                "opt_prune_system": False,
                "opt_configure_sparse": False,
                "opt_compact_vhdx": False,
                "opt_cleanup_temp": True,
            }
            try:
                import json
                config_path = Path.home() / ".docker_clennear_prefs.json"
                if config_path.exists():
                    with open(config_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            for k, v in loaded.items():
                                defaults[k] = v
            except Exception:
                pass
            opts_screen = CleanupOptionsScreen("Selecione as opções de limpeza", defaults=defaults)
            await self.push_screen(opts_screen)
            if not opts_screen.result:
                self.write_ui_log("Limpeza Docker cancelada pelo usuário.")
                return
            selected = opts_screen.selected_options
            # Execute the selected options in a reasonable order
            # 1) Stop WSL/Docker, 2) Quick cleanup (in-process or subprocess), 3) Full cleanup, 4) Configure/Compact, 5) Cleanup temp
            if selected.get("opt_stop_wsl"):
                self.write_ui_log("Executando: Parar Docker e WSL...")
                # Use a worker to run stop_docker_wsl
                self._run_stop_wsl()
            # Run prune commands selected
            if selected.get("opt_prune_containers"):
                self.write_ui_log("Executando prune containers...")
                self._run_prune_containers()
            if selected.get("opt_prune_images"):
                self.write_ui_log("Executando prune images...")
                self._run_prune_images()
            if selected.get("opt_prune_volumes"):
                self.write_ui_log("Executando prune volumes...")
                self._run_prune_volumes()
            if selected.get("opt_prune_networks"):
                self.write_ui_log("Executando prune networks...")
                self._run_prune_networks()
            if selected.get("opt_prune_builder"):
                self.write_ui_log("Executando prune builder...")
                self._run_prune_builder()
            if selected.get("opt_prune_system"):
                self.write_ui_log("Executando prune system (docker system prune -af --volumes)...")
                self._run_prune_system()
            # Removed legacy quick/full options: execution now maps to the granular options selected above.
            if selected.get("opt_configure_sparse"):
                self.write_ui_log("Configurando sparse (WSL)...")
                self._run_configure_sparse()
            if selected.get("opt_compact_vhdx"):
                self.write_ui_log("Compactando VHDX (pode requerer administrador)...")
                self._run_compact_vhdx()
            if selected.get("opt_cleanup_temp"):
                self.write_ui_log("Limpando arquivos temporários...")
                self._run_cleanup_temp()
            return
        # removed: duplicate full_cleanup handler — consolidated under 'docker_cleanup'
        # Legacy quick-inprocess was removed; keep worker in code for reuse.
        # The `Full Cleanup` button was removed in favor of customizable options.
        # Full Cleanup elevated removed in UI; use the 'Compact VHDX' and 'Configurar sparse' options if required.
        if button_id == "models_generator":
            # focus the input field
            self.query_one(Input).focus()
            return
        if button_id == "run_models":
            path_input = self.query_one(Input)
            path = path_input.value.strip() if path_input.value else ""
            if not path:
                self.write_ui_log("Por favor informe um caminho de arquivo válido para gerar modelos.")
                return
            await self.run_python_script(["-m", "lmarena.generator", path], "Models Generator")

        if button_id == "open_logs":
            logs_dir = Path("logs")
            if not logs_dir.exists():
                self.write_ui_log("Diretório de logs não encontrado: logs")
                return
            try:
                # platform-specific: Windows explorer
                if sys.platform.startswith("win"):
                    os.startfile(str(logs_dir))
                else:
                    import webbrowser

                    webbrowser.open(str(logs_dir))
                self.write_ui_log("Abrindo pasta de logs...")
            except Exception as e:
                self.write_ui_log(f"Falha ao abrir pasta de logs: {e}")
            return

        if button_id == "clear_logs":
            # Clear the UI-only content (won't delete log files)
            try:
                self.query_one(RichLog).clear()
                self.write_ui_log("UI logs limpos")
            except Exception as e:
                self.write_ui_log(f"Erro ao limpar log UI: {e}")
            return

    def write_ui_log(self, message: str) -> None:
        """Write message to UI log and persist to daily log file.
        
        This method works from both async workers and thread workers.
        """
        # Write to file via daily writer
        try:
            if hasattr(self, "daily_writer") and self.daily_writer:
                self.daily_writer.write(message)
        except Exception:
            pass
        
        # Write to UI widget - check if we're in the main thread
        try:
            import threading
            if threading.current_thread() == threading.main_thread():
                # We're in the main thread (async worker or UI context), call directly
                self.write_ui_log_widget(message)
            else:
                # We're in a worker thread, use call_from_thread
                self.call_from_thread(self.write_ui_log_widget, message)
        except Exception:
            # Fallback: always try call_from_thread
            try:
                self.call_from_thread(self.write_ui_log_widget, message)
            except Exception:
                pass

    def write_ui_log_widget(self, message: str) -> None:
        """Directly write to the UI widget (no file persistence).
        
        This method is thread-safe and should be called from any context.
        """
        try:
            logger = self.query_one(RichLog)
            logger.write(message)
        except Exception:
            # Widget not yet available or query failed
            pass

    # -- Progress helpers (simple determinate progress rendered via Rich in a Static widget) --
    def start_progress(self, title: str, total: int = 100) -> None:
        """Start or reset the progress widget.

        This method works from both async workers and thread workers.
        """
        def _do_start():
            try:
                prog_widget = self.query_one("#progress", Static)
                # store simple attributes for tests/unit-checks
                prog_widget.progress_title = title
                prog_widget.progress_total = int(total)
                prog_widget.progress_value = 0
                # Build a simple Rich Progress renderable and update widget content
                rp = RichProgress(TextColumn("{task.description}"), BarColumn(), TaskProgressColumn())
                rp_task = rp.add_task(title, total=total)
                prog_widget.update(rp)
                # Keep the renderable on the widget so we can update
                prog_widget._progress = rp
                prog_widget._task_id = rp_task
                # Show a spinner if available
                try:
                    spinner = self.query_one("#spinner", LoadingIndicator)
                    if spinner and "hidden" in spinner.classes:
                        spinner.remove_class("hidden")
                except Exception:
                    pass
            except Exception:
                pass
        
        # Detect context and call appropriately
        try:
            import threading
            if threading.current_thread() == threading.main_thread():
                _do_start()
            else:
                self.call_from_thread(_do_start)
        except Exception:
            try:
                self.call_from_thread(_do_start)
            except Exception:
                pass

    def update_progress(self, amount: int) -> None:
        """Update the current progress bar with a new absolute amount (0..total)."""
        def _do_update():
            try:
                prog_widget = self.query_one("#progress", Static)
                if not getattr(prog_widget, "_progress", None):
                    return
                rp = prog_widget._progress
                tid = prog_widget._task_id
                rp.update(tid, completed=int(amount))
                prog_widget.update(rp)
                prog_widget.progress_value = int(amount)
            except Exception:
                pass
        
        try:
            import threading
            if threading.current_thread() == threading.main_thread():
                _do_update()
            else:
                self.call_from_thread(_do_update)
        except Exception:
            try:
                self.call_from_thread(_do_update)
            except Exception:
                pass

    def advance_progress(self, delta: int) -> None:
        """Safely advance current progress by delta."""
        def _do_advance():
            try:
                prog_widget = self.query_one("#progress", Static)
                if not getattr(prog_widget, "_progress", None):
                    return
                rp = prog_widget._progress
                tid = prog_widget._task_id
                rp.advance(tid, delta)
                prog_widget.update(rp)
                prog_widget.progress_value = int(rp.tasks[0].completed)
            except Exception:
                pass
        
        try:
            import threading
            if threading.current_thread() == threading.main_thread():
                _do_advance()
            else:
                self.call_from_thread(_do_advance)
        except Exception:
            try:
                self.call_from_thread(_do_advance)
            except Exception:
                pass

    def finish_progress(self) -> None:
        """Mark the current progress as complete and clear the widget after a delay."""
        def _do_finish():
            try:
                prog_widget = self.query_one("#progress", Static)
                if not getattr(prog_widget, "_progress", None):
                    return
                rp = prog_widget._progress
                tid = prog_widget._task_id
                rp.update(tid, completed=rp.tasks[0].total or 100)
                prog_widget.update(rp)
                prog_widget.progress_value = int(rp.tasks[0].completed)
                # Schedule a clear to run after a short delay
                self.set_timer(1.5, lambda: prog_widget.update(""))
                # Hide spinner
                try:
                    spinner = self.query_one("#spinner", LoadingIndicator)
                    if spinner and "hidden" not in spinner.classes:
                        spinner.add_class("hidden")
                except Exception:
                    pass
            except Exception:
                # swallow any issue updating the progress UI to avoid crashing the app
                pass
        
        try:
            import threading
            if threading.current_thread() == threading.main_thread():
                _do_finish()
            else:
                self.call_from_thread(_do_finish)
        except Exception:
            try:
                self.call_from_thread(_do_finish)
            except Exception:
                pass

    class _LogWriter:
        """File-like writer that streams data into the app's Log widget.

        It uses `call_from_thread` to safely schedule UI updates when writing from a worker.
        """

        def __init__(self, app: "CommandRunnerApp", prefix: str = "") -> None:
            self.app = app
            self.prefix = prefix

        def write(self, text: str) -> None:
            """Write text to UI log, with prefix."""
            if not text:
                return
            try:
                # Safely schedule the write on the app thread
                prefixed_text = f"{self.prefix}{text}" if self.prefix else text
                self.app.call_from_thread(lambda: self.app.write_ui_log(prefixed_text))
            except Exception:
                # Silently ignore errors writing to the log
                pass

        def flush(self) -> None:
            """Flush the writer (no-op for console streaming)."""
            pass

    # NOTE: `work`, `Worker` and `WorkerState` are imported at module level.

    @work(thread=True)
    def _run_quick_in_process(self) -> None:
        """Worker function. Runs the quick_cleanup function from `cli.quick_cleanup` in a thread.

        This function is suitable for the Textual `run_worker` API.
        """
        try:
            from cli.quick_cleanup import quick_cleanup

            writer = self._LogWriter(self, prefix="[Quick-InProcess] ")
            console = RichConsole(file=writer)
            # `quick_cleanup` returns True/False
            self.call_from_thread(lambda: self.start_progress("Quick Cleanup", 100))
            self.call_from_thread(lambda: self.update_progress(10))
            success = quick_cleanup(console=console)
            self.call_from_thread(lambda: self.update_progress(100))
            self.call_from_thread(lambda: self.write_ui_log(f"In-process Quick Cleanup finished: {success}"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"In-process Quick Cleanup error: {e}"))

    @work(exclusive=True)
    async def _run_stop_wsl(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Parando Docker e WSL", 100)
            self.update_progress(10)
            
            # Usar versão async com callback de streaming
            await cleaner.stop_docker_wsl_async(stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Stop WSL concluído com sucesso\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Stop WSL error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_configure_sparse(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Configurar sparse", 100)
            self.update_progress(10)
            
            await cleaner.configure_wsl_sparse_async(stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Configure sparse concluído com sucesso\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Configure sparse error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_compact_vhdx(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Compactando VHDX", 100)
            self.update_progress(10)
            
            # Executar compactação com streaming
            await cleaner.compact_vhdx_files_async(stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Compact VHDX concluído com sucesso\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Compact VHDX error: {e}\n")
            self.finish_progress()

    @work(thread=True)
    def _run_cleanup_temp(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            writer = self._LogWriter(self, prefix="[Cleanup-Temp] ")
            cleaner = WSLDockerCleaner()
            self.call_from_thread(lambda: self.start_progress("Limpando arquivos temporários", 100))
            self.call_from_thread(lambda: self.update_progress(20))
            res = cleaner.cleanup_temp_files()
            self.call_from_thread(lambda: self.update_progress(85))
            self.call_from_thread(lambda: self.write_ui_log(f"Cleanup temp finished: {res}"))
            self.call_from_thread(lambda: self.finish_progress())
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Cleanup temp error: {e}"))

    @work(exclusive=True)
    async def _run_prune_containers(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Prune containers", 100)
            self.update_progress(10)
            
            await cleaner.run_command_async("docker container prune -f", shell=True, stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Prune containers completo\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Prune containers error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_prune_images(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Prune images", 100)
            self.update_progress(10)
            
            await cleaner.run_command_async("docker image prune -af", shell=True, stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Prune images completo\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Prune images error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_prune_volumes(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Prune volumes", 100)
            self.update_progress(10)
            
            await cleaner.run_command_async("docker volume prune -f", shell=True, stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Prune volumes completo\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Prune volumes error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_prune_networks(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Prune networks", 100)
            self.update_progress(10)
            
            await cleaner.run_command_async("docker network prune -f", shell=True, stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Prune networks completo\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Prune networks error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_prune_builder(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Prune builder", 100)
            self.update_progress(10)
            
            await cleaner.run_command_async("docker builder prune -af", shell=True, stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Prune builder completo\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Prune builder error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_prune_system(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Prune system", 100)
            self.update_progress(10)
            
            await cleaner.run_command_async("docker system prune -af --volumes", shell=True, stream_callback=self.write_ui_log)
            
            self.update_progress(100)
            self.write_ui_log("Prune system completo\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Prune system error: {e}\n")
            self.finish_progress()

    @work(exclusive=True)
    async def _run_full_cleanup(self) -> None:
        """Executa limpeza completa do Docker e WSL com streaming em tempo real."""
        try:
            from docker_cleaner.core import WSLDockerCleaner
            cleaner = WSLDockerCleaner()
            
            self.start_progress("Full Cleanup", 100)
            self.update_progress(5)
            
            # Executar cada etapa com streaming
            self.write_ui_log("=== INICIANDO LIMPEZA COMPLETA ===\n")
            
            # 1. Limpeza Docker
            self.update_progress(10)
            self.write_ui_log("Etapa 1/5: Limpeza do Docker...\n")
            await cleaner.docker_cleanup_async(stream_callback=self.write_ui_log)
            
            # 2. Parar Docker/WSL
            self.update_progress(30)
            self.write_ui_log("Etapa 2/5: Parando Docker e WSL...\n")
            await cleaner.stop_docker_wsl_async(stream_callback=self.write_ui_log)
            
            # 3. Configurar sparse
            self.update_progress(50)
            self.write_ui_log("Etapa 3/5: Configurando modo sparse...\n")
            await cleaner.configure_wsl_sparse_async(stream_callback=self.write_ui_log)
            
            # 4. Compactar VHDX
            self.update_progress(70)
            self.write_ui_log("Etapa 4/5: Compactando arquivos VHDX...\n")
            await cleaner.compact_vhdx_files_async(stream_callback=self.write_ui_log)
            
            # 5. Limpeza de temp files (síncrona)
            self.update_progress(90)
            self.write_ui_log("Etapa 5/5: Limpando arquivos temporários...\n")
            cleaner.cleanup_temp_files()
            
            self.update_progress(100)
            self.write_ui_log("=== LIMPEZA COMPLETA FINALIZADA ===\n")
            self.write_ui_log(f"Espaço total economizado: {cleaner.total_space_saved:.2f} GB\n")
            self.finish_progress()
        except Exception as e:
            self.write_ui_log(f"Full cleanup error: {e}\n")
            self.finish_progress()

    async def run_python_script(self, args: List[str], title: str) -> None:
        """Execute um script Python em subprocesso e mostre a saída no Log widget."""
        # If first arg is "-m", treat as module invocation
        if args[0] == "-m":
            # python -u -m module_name [args...] (-u = unbuffered for real-time output)
            cmd = [sys.executable, "-u"] + args
        else:
            # Otherwise try to find script file
            script = args[0]
            script_path = Path(script)
            if not script_path.exists():
                # try relative to repo
                repo_root = Path(__file__).parent
                script_path = repo_root / script
            if not script_path.exists():
                self.write_ui_log(f"Script não encontrado: {args[0]}")
                return
            cmd = [sys.executable, "-u", str(script_path)] + args[1:]

        self.write_ui_log(f"Executando: {' '.join(cmd)}")

        try:
            # Set PYTHONUNBUFFERED environment variable for immediate output
            env = os.environ.copy()
            env['PYTHONUNBUFFERED'] = '1'
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
        except Exception as e:
            self.write_ui_log(f"Erro ao iniciar processo: {e}")
            return

        async def stream_reader(stream, name: str):
            """Read from a stream and write each line to the UI."""
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                if text:
                    self.write_ui_log(f"[{title}] {text}")

        # Start readers as tasks
        stdout_task = asyncio.create_task(stream_reader(process.stdout, "stdout"))
        stderr_task = asyncio.create_task(stream_reader(process.stderr, "stderr"))

        # Wait for process to finish
        await process.wait()
        
        # Wait for readers to complete as well
        await asyncio.gather(stdout_task, stderr_task, return_exceptions=True)

        rc = process.returncode
        self.write_ui_log(f"[{title}] Processo finalizado com código {rc}")

    def on_mount(self) -> None:
        """Called when app is mounted: initialize the daily file writer."""
        # Provide a UI-only writer callback used by DailyLogWriter to avoid recursion
        def ui_write_direct(text: str) -> None:
            # This is a sync callback that only writes to the UI widget
            # Ensure it is scheduled in the app thread
            self.call_from_thread(lambda: self.write_ui_log_widget(text))

        self.daily_writer = DailyLogWriter(ui_write=ui_write_direct)

        # Configure Python logging to write into the daily writer as well
        root_logger = logging.getLogger()
        # Add handler if not present to prevent duplicates
        found = False
        for h in list(root_logger.handlers):
            if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) == self.daily_writer:
                found = True
                break
        if not found:
            handler = logging.StreamHandler(self.daily_writer)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
            root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

        # Unhandled exception hooks
        def _handle_unhandled_exception(exc_type, exc_value, exc_tb):
            logging.getLogger("app").exception("Uncaught exception", exc_info=(exc_type, exc_value, exc_tb))

        sys.excepthook = _handle_unhandled_exception

        # Asyncio loop exception handler
        def _loop_exception(loop, context):
            # context may contain message and/or exception
            exc = context.get("exception")
            if exc:
                logging.getLogger("asyncio").exception("Unhandled async exception", exc_info=(type(exc), exc, getattr(exc, '__traceback__', None)))
            else:
                logging.getLogger("asyncio").error("Unhandled async exception: %s", context.get("message"))

        try:
            loop = asyncio.get_running_loop()
            loop.set_exception_handler(_loop_exception)
        except RuntimeError:
            # no running loop at mount time
            pass
        # Threading exceptions (Python 3.8+) — capture uncaught exceptions in thread workers
        try:
            import threading

            def _thread_exc_handler(args):
                exc = getattr(args, "exc_value", None)
                if exc:
                    logging.getLogger("threading").exception("Unhandled thread exception", exc_info=(type(exc), exc, getattr(exc, "__traceback__", None)))

            threading.excepthook = _thread_exc_handler
        except Exception:
            pass

        # Redirect stderr to our daily writer so python tracebacks printed to stderr are captured
        try:
            self._orig_stderr = sys.stderr

            class _StderrRedirect:
                def __init__(self, writer, orig):
                    self.writer = writer
                    self.orig = orig

                def write(self, text: str) -> None:
                    try:
                        self.writer.write(text)
                    except Exception:
                        pass
                    try:
                        self.orig.write(text)
                    except Exception:
                        pass

                def flush(self) -> None:
                    try:
                        self.writer.flush()
                    except Exception:
                        pass
                    try:
                        self.orig.flush()
                    except Exception:
                        pass

            sys.stderr = _StderrRedirect(self.daily_writer, self._orig_stderr)
        except Exception:
            pass

        # Track number of active workers; used to show/hide a spinner indicator
        self._active_workers = 0
        
        # Log de inicialização com status de admin
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            admin_msg = "com privilégios de administrador" if is_admin else "SEM privilégios de administrador"
            self.write_ui_log(f"=== Docker-Clennear Iniciado {admin_msg} ===\n")
            if not is_admin:
                self.write_ui_log("⚠ AVISO: Algumas operações podem falhar sem privilégios de administrador.\n")
        except Exception:
            self.write_ui_log("=== Docker-Clennear Iniciado ===\n")

    def on_worker_state_changed(self, event) -> None:
        """Track worker states to show a spinner and log errors.

        This method increments a counter for RUNNING workers and decrements when they
        complete or error. When there are any active workers, it shows a spinner in
        the UI; otherwise it hides it.
        """
        try:
            # Identify worker (use its name if provided)
            worker_name = getattr(event.worker, "name", None) or repr(event.worker)
            logging.getLogger().info("Worker state changed: %s -> %s", worker_name, event.state)
            # show spinner when worker is running
            try:
                if event.state == WorkerState.RUNNING:
                    self._active_workers += 1
                    spinner = self.query_one("#spinner", LoadingIndicator)
                    if spinner and "hidden" in spinner.classes:
                        spinner.remove_class("hidden")
                else:
                    # treat non-running as completed/errored → decrement
                    self._active_workers = max(0, getattr(self, "_active_workers", 0) - 1)
                    if getattr(self, "_active_workers", 0) == 0:
                        try:
                            spinner = self.query_one("#spinner", LoadingIndicator)
                            if spinner and "hidden" not in spinner.classes:
                                spinner.add_class("hidden")
                        except Exception:
                            pass
            except Exception:
                pass
            # If an error state, try to log the exception details (best-effort)
            if event.state == WorkerState.ERROR:
                try:
                    worker_obj = None
                    if hasattr(self.workers, "_workers"):
                        for w in self.workers._workers:
                            if w is event.worker:
                                worker_obj = w
                                break
                    if worker_obj:
                        err = getattr(worker_obj, "_error", None) or getattr(worker_obj, "error", None)
                        if err:
                            logging.getLogger().exception("Worker %s errored with exception", worker_name, exc_info=(type(err), err, getattr(err, "__traceback__", None)))
                        else:
                            logging.getLogger().error("Worker %s errored (no error object available)", worker_name)
                except Exception:
                    logging.getLogger().exception("Failed to extract worker error for %s", worker_name)
        except Exception:
            # Avoid crashing the app event handler; this is noisy but safe
            pass

    async def _ask_elevate_and_relaunch(self, operation_name: str) -> None:
        """Show confirmation modal asking the user whether to relaunch the app with admin rights.

        This coroutine should be scheduled on the app's main loop via call_from_thread
        when invoked from a worker thread.
        """
        try:
            message = f"A operação '{operation_name}' requer privilégios de administrador. Deseja reiniciar o aplicativo como administrador?"
            confirm = ConfirmScreen(message)
            await self.push_screen(confirm)
            if not confirm.result:
                self.write_ui_log(f"{operation_name} cancelada pelo usuário (não concedeu admin).")
                return
            # Launch elevated process and exit this app instance.
            # If operation is a specific admin task, attempt to run the `cli.admin_tasks` helper elevated
            try:
                # Map operation to helper task name if present
                op_map = {
                    "Compactar VHDX": "compact_vhdx",
                    "Full Cleanup": ""  # empty means re-launch whole app as admin
                }
                helper_task = op_map.get(operation_name, "")
                if helper_task:
                    # Run the admin helper with ShellExecute runas
                    python_exe = sys.executable
                    params = f'-m cli.admin_tasks {helper_task}'
                    import ctypes
                    ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, params, None, 1)
                    self.write_ui_log(f"Administrador solicitado: rodando helper {helper_task}")
                    # If helper is invoked, exit current app to avoid duplicate operations
                    self.exit()
                else:
                    # Perform full relaunch as admin if op_map doesn't list a helper
                    from docker_cleaner.core import WSLDockerCleaner
                    cleaner = WSLDockerCleaner()
                    cleaner.run_as_admin()
            except Exception as e:
                self.write_ui_log(f"Erro ao solicitar elevação: {e}")
        except Exception as e:
            self.write_ui_log(f"Erro ao solicitar confirmação de elevação: {e}")


if __name__ == "__main__":
    import ctypes
    import sys
    
    # Verificar se está rodando como administrador (apenas Windows)
    def is_admin():
        """Verifica se o script está rodando como administrador."""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            return False
    
    # Se não estiver como admin, solicitar elevação automaticamente
    if sys.platform.startswith('win') and not is_admin():
        try:
            # Reiniciar o script com privilégios de administrador
            python_exe = sys.executable
            script_path = os.path.abspath(__file__)
            
            # Usar ShellExecute com "runas" para solicitar UAC
            ctypes.windll.shell32.ShellExecuteW(
                None,
                "runas",
                python_exe,
                f'"{script_path}"',
                None,
                1  # SW_SHOW
            )
            
            # Sair da instância não-elevada
            sys.exit(0)
        except Exception as e:
            # Se falhar, continuar sem admin (usuário pode ter cancelado UAC)
            print(f"Aviso: Não foi possível elevar privilégios: {e}")
            print("Algumas operações podem falhar sem privilégios de administrador.")
            print("Continuando sem elevação...\n")
    
    # Executar o app
    app = CommandRunnerApp()
    app.run()
