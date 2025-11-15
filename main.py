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
from textual.widgets import Header, Footer, Button, Static, Input, Label, RichLog, Checkbox
from textual.screen import Screen
from typing import Callable
from rich.console import Console as RichConsole
from cli.richlog import DailyLogWriter
import logging
import asyncio
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
        yield Static(f"[bold yellow]{self.message}[/bold yellow]\n")
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
            # Preset buttons to quickly set common combos
            with Horizontal():
                yield Button("Preset: Quick (containers, images, volumes)", id="opts_preset_quick")
                yield Button("Preset: Full (all prunes + compact)", id="opts_preset_full")
        # Footer controls — always visible at the bottom of the modal
        with Horizontal(id="opts_footer"):
            yield Button("Executar", id="opts_exec")
            yield Button("Salvar", id="opts_save")
            yield Button("Cancelar", id="opts_cancel")
            yield Button("Sair", id="opts_exit")

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
        # Save selected options as default preferences
        if event.button.id == "opts_save":
            opts = {chk.id: chk.value for chk in self.query(Checkbox)}
            # Persist to user home
            try:
                from pathlib import Path
                import json
                config_path = Path.home() / ".docker_clennear_prefs.json"
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(opts, f, indent=2)
                # If hosted under an app with write_ui_log, use it
                try:
                    getattr(self.app, "write_ui_log", lambda *_: None)(f"Preferences saved: {config_path}")
                except Exception:
                    pass
                # Dismiss modal and mark result False (no immediate execution)
                self.result = False
                self.dismiss()
                return
            except Exception as e:
                try:
                    getattr(self.app, "write_ui_log", lambda *_: None)(f"Failed to save preferences: {e}")
                except Exception:
                    pass
                return
        # Exit application from modal
        if event.button.id == "opts_exit":
            try:
                # Request application exit
                self.app.exit()
            except Exception:
                pass
            return
        # Collect checkbox values
        opts = {}
        for chk in self.query(Checkbox):
            opts[chk.id] = chk.value
        self.selected_options = opts
        self.result = True
        self.dismiss()


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
        padding: 1 1;
    }
    #log {
        height: 10;
    }
    """

    TITLE = "Docker-Clennear UI"

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Static("[bold]Ações Disponíveis[/bold]", id="menu_title")
                yield Button("Limpeza Docker", id="docker_cleanup")
                yield Button("LMArena: Gerar Models", id="models_generator")
                yield Button("Abrir pasta de logs", id="open_logs")
                yield Button("Limpar logs UI", id="clear_logs")
                yield Button("Sair", id="exit")
            with Container(id="main"):
                yield Static("[bold]Detalhes / Controles[/bold]", id="details_title")
                yield Label("Selecione uma ação à esquerda e use os botões abaixo para rodar.")
                default_models = "lmarena_models.txt" if Path("lmarena_models.txt").exists() else ""
                yield Input(value=default_models, placeholder="Caminho do arquivo para models (ex: lmarena_models.txt)", id="models_path")
                yield Button("Executar Generator", id="run_models")
                yield Static("Logs de saída:")
                yield RichLog(id="log", highlight=True, markup=True)
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "exit":
            self.exit()
            return
        if button_id == "docker_cleanup":
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
                from pathlib import Path
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
                self.run_worker(self._run_stop_wsl(), name="stop-wsl")
            # Run prune commands selected
            if selected.get("opt_prune_containers"):
                self.write_ui_log("Executando prune containers...")
                self.run_worker(self._run_prune_containers(), name="prune-containers")
            if selected.get("opt_prune_images"):
                self.write_ui_log("Executando prune images...")
                self.run_worker(self._run_prune_images(), name="prune-images")
            if selected.get("opt_prune_volumes"):
                self.write_ui_log("Executando prune volumes...")
                self.run_worker(self._run_prune_volumes(), name="prune-volumes")
            if selected.get("opt_prune_networks"):
                self.write_ui_log("Executando prune networks...")
                self.run_worker(self._run_prune_networks(), name="prune-networks")
            if selected.get("opt_prune_builder"):
                self.write_ui_log("Executando prune builder...")
                self.run_worker(self._run_prune_builder(), name="prune-builder")
            if selected.get("opt_prune_system"):
                self.write_ui_log("Executando prune system (docker system prune -af --volumes)...")
                self.run_worker(self._run_prune_system(), name="prune-system")
            # Removed legacy quick/full options: execution now maps to the granular options selected above.
            if selected.get("opt_configure_sparse"):
                self.write_ui_log("Configurando sparse (WSL)...")
                self.run_worker(self._run_configure_sparse(), name="configure-sparse")
            if selected.get("opt_compact_vhdx"):
                self.write_ui_log("Compactando VHDX (pode requerer administrador)...")
                self.run_worker(self._run_compact_vhdx(), name="compact-vhdx")
            if selected.get("opt_cleanup_temp"):
                self.write_ui_log("Limpando arquivos temporários...")
                self.run_worker(self._run_cleanup_temp(), name="cleanup-temp")
            return
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
            await self.run_python_script(["models_generator.py", path], "Models Generator")

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
        # Public method: write to UI and persist to daily log file.
        # Prefer using the daily writer (which will call the UI callback) to avoid duplicates.
        if hasattr(self, "daily_writer") and self.daily_writer:
            try:
                self.daily_writer.write(message)
                return
            except Exception:
                # Fallback to UI-only write
                pass
        # No daily writer available: write only to the UI widget
        self.write_ui_log_widget(message)

    def write_ui_log_widget(self, message: str) -> None:
        """Directly write to the UI widget (no file persistence)."""
        logger = self.query_one(RichLog)
        logger.write(message)

    class _LogWriter:
        """File-like writer that streams data into the app's Log widget.

        It uses `call_from_thread` to safely schedule UI updates when writing from a worker.
        """

        def __init__(self, app: "CommandRunnerApp", prefix: str = "") -> None:
            self.app = app
            self.prefix = prefix
            # Attach a daily file writer that also writes to the UI
            # Compose a UI writer callback that simply writes to the Log widget
            def ui_write(text: str) -> None:
                # schedule call to the app to avoid thread-safety issues
                self.app.call_from_thread(lambda: self.app.write_ui_log(f"{self.prefix}{text}"))

            # Use the app's daily_writer if available; otherwise create own
            self._daily_writer = None

        def write(self, text: str) -> None:
            # Ensure writing to the widget occurs on the app thread
            # Stream to UI and file writer
            # Console(file=writer) can supply partial lines; handle those
            try:
                # Prefer app-level writer to avoid multiple file instances
                writer = getattr(self.app, "daily_writer", None) or self._daily_writer
                if writer:
                    writer.write(f"{self.prefix}{text}")
                else:
                    # Fallback: write only to the UI
                    self.app.call_from_thread(lambda: self.app.write_ui_log_widget(f"{self.prefix}{text}"))
            except Exception:
                # On error still attempt to write to the UI
                self.app.call_from_thread(lambda: self.app.write_ui_log(f"{self.prefix}{text}"))

        def flush(self) -> None:
            return None

    from textual import work
    from textual.worker import Worker, WorkerState

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
            success = quick_cleanup(console=console)
            self.call_from_thread(lambda: self.write_ui_log(f"In-process Quick Cleanup finished: {success}"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"In-process Quick Cleanup error: {e}"))

    @work(thread=True)
    def _run_stop_wsl(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            writer = self._LogWriter(self, prefix="[Stop-WSL] ")
            cleaner = WSLDockerCleaner()
            # Replace console with our writer
            console = RichConsole(file=writer)
            res = cleaner.stop_docker_wsl()
            self.call_from_thread(lambda: self.write_ui_log(f"Stop WSL finished: {res}"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Stop WSL error: {e}"))

    @work(thread=True)
    def _run_configure_sparse(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            writer = self._LogWriter(self, prefix="[Configure-Sparse] ")
            cleaner = WSLDockerCleaner()
            res = cleaner.configure_wsl_sparse()
            self.call_from_thread(lambda: self.write_ui_log(f"Configure sparse finished: {res}"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Configure sparse error: {e}"))

    @work(thread=True)
    def _run_compact_vhdx(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            writer = self._LogWriter(self, prefix="[Compact-VHDX] ")
            cleaner = WSLDockerCleaner()
            res = cleaner.compact_vhdx_files()
            self.call_from_thread(lambda: self.write_ui_log(f"Compact VHDX finished: {res}"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Compact VHDX error: {e}"))

    @work(thread=True)
    def _run_cleanup_temp(self) -> None:
        try:
            from docker_cleaner.core import WSLDockerCleaner
            writer = self._LogWriter(self, prefix="[Cleanup-Temp] ")
            cleaner = WSLDockerCleaner()
            res = cleaner.cleanup_temp_files()
            self.call_from_thread(lambda: self.write_ui_log(f"Cleanup temp finished: {res}"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Cleanup temp error: {e}"))

    @work(thread=True)
    def _run_prune_containers(self) -> None:
        try:
            from cli.quick_cleanup import run_cmd
            writer = self._LogWriter(self, prefix="[Prune-Containers] ")
            console = RichConsole(file=writer)
            run_cmd(console, "docker container prune -f", "Removendo containers parados")
            self.call_from_thread(lambda: self.write_ui_log("Prune containers completo"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Prune containers error: {e}"))

    @work(thread=True)
    def _run_prune_images(self) -> None:
        try:
            from cli.quick_cleanup import run_cmd
            writer = self._LogWriter(self, prefix="[Prune-Images] ")
            console = RichConsole(file=writer)
            run_cmd(console, "docker image prune -af", "Removendo imagens não utilizadas")
            self.call_from_thread(lambda: self.write_ui_log("Prune images completo"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Prune images error: {e}"))

    @work(thread=True)
    def _run_prune_volumes(self) -> None:
        try:
            from cli.quick_cleanup import run_cmd
            writer = self._LogWriter(self, prefix="[Prune-Volumes] ")
            console = RichConsole(file=writer)
            run_cmd(console, "docker volume prune -f", "Removendo volumes não utilizados")
            self.call_from_thread(lambda: self.write_ui_log("Prune volumes completo"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Prune volumes error: {e}"))

    @work(thread=True)
    def _run_prune_networks(self) -> None:
        try:
            from cli.quick_cleanup import run_cmd
            writer = self._LogWriter(self, prefix="[Prune-Networks] ")
            console = RichConsole(file=writer)
            run_cmd(console, "docker network prune -f", "Removendo redes não utilizadas")
            self.call_from_thread(lambda: self.write_ui_log("Prune networks completo"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Prune networks error: {e}"))

    @work(thread=True)
    def _run_prune_builder(self) -> None:
        try:
            from cli.quick_cleanup import run_cmd
            writer = self._LogWriter(self, prefix="[Prune-Builder] ")
            console = RichConsole(file=writer)
            run_cmd(console, "docker builder prune -af", "Limpando cache de build")
            self.call_from_thread(lambda: self.write_ui_log("Prune builder completo"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Prune builder error: {e}"))

    @work(thread=True)
    def _run_prune_system(self) -> None:
        try:
            from cli.quick_cleanup import run_cmd
            writer = self._LogWriter(self, prefix="[Prune-System] ")
            console = RichConsole(file=writer)
            run_cmd(console, "docker system prune -af --volumes", "Limpando sistema Docker (agressivo)")
            self.call_from_thread(lambda: self.write_ui_log("Prune system completo"))
        except Exception as e:
            self.call_from_thread(lambda: self.write_ui_log(f"Prune system error: {e}"))

    async def run_python_script(self, args: List[str], title: str) -> None:
        """Execute um script Python em subprocesso e mostre a saída no Log widget."""
        # Resolve path relative to repo root
        script = args[0]
        script_path = Path(script)
        if not script_path.exists():
            # try relative to repo
            repo_root = Path(__file__).parent
            script_path = repo_root / script
        if not script_path.exists():
            self.write_ui_log(f"Script não encontrado: {args[0]}")
            return

        cmd = [sys.executable, str(script_path)] + args[1:]
        self.write_ui_log(f"Executando: {' '.join(cmd)}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except Exception as e:
            self.write_ui_log(f"Erro ao iniciar processo: {e}")
            return

        async def stream_reader(stream, name: str):
            while True:
                line = await stream.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip("\n")
                self.write_ui_log(f"[{title}] {text}")

        # Start readers
        tasks = [asyncio.create_task(stream_reader(process.stdout, "stdout")), asyncio.create_task(stream_reader(process.stderr, "stderr"))]

        # Wait for process to finish and readers to complete
        await process.wait()
        await asyncio.gather(*tasks, return_exceptions=True)

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

        def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
            """Log worker state changes and, if errored, attempt to log exception details."""
            try:
                # Identify worker (use its name if provided)
                worker_name = getattr(event.worker, "name", None) or repr(event.worker)
                logging.getLogger().info("Worker state changed: %s -> %s", worker_name, event.state)
                if event.state == WorkerState.ERROR:
                    # Try to locate the worker and log its error if available
                    try:
                        worker_obj = None
                        # Search internal workers list (best effort) by identity
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


if __name__ == "__main__":
    app = CommandRunnerApp()
    app.run()
