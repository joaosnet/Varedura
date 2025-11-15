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
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Button, Static, Input, Label, Log
from textual.screen import Screen
from typing import Callable
from rich.console import Console as RichConsole


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
                yield Button("Quick Cleanup (Subprocess)", id="quick_cleanup")
                yield Button("Quick Cleanup (In-Process)", id="quick_inprocess")
                yield Button("Full Cleanup (Subprocess)", id="full_cleanup")
                yield Button("Full Cleanup (Elevado)", id="full_cleanup_elevated")
                yield Button("LMArena: Gerar Models", id="models_generator")
                yield Button("Sair", id="exit")
            with Container(id="main"):
                yield Static("[bold]Detalhes / Controles[/bold]", id="details_title")
                yield Label("Selecione uma ação à esquerda e use os botões abaixo para rodar.")
                default_models = "lmarena_models.txt" if Path("lmarena_models.txt").exists() else ""
                yield Input(value=default_models, placeholder="Caminho do arquivo para models (ex: lmarena_models.txt)", id="models_path")
                yield Button("Executar Generator", id="run_models")
                yield Static("Logs de saída:")
                yield Log(id="log")
        yield Footer()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        if button_id == "exit":
            self.exit()
            return
        if button_id == "quick_cleanup":
            confirm = ConfirmScreen("Cleaning Docker is destructive. Confirm Quick Cleanup?")
            await self.push_screen(confirm)
            if not confirm.result:
                self.write_ui_log("Quick Cleanup cancelled by user.")
                return
            await self.run_python_script(["quick_wsl_cleanup.py"], "Quick Cleanup")
            return
        if button_id == "quick_inprocess":
            # Run the quick cleanup function inside a background worker thread, writing
            # output to the UI's log via a custom writer.
            self.write_ui_log("In-process Quick Cleanup starting...")
            self.run_worker(self._run_quick_in_process, name="quick-inprocess")
            return
        if button_id == "full_cleanup":
            confirm = ConfirmScreen("Cleaning Docker is destructive. Confirm Full Cleanup?")
            await self.push_screen(confirm)
            if not confirm.result:
                self.write_ui_log("Full Cleanup cancelled by user.")
                return
            await self.run_python_script(["wsl_docker_cleaner.py"], "Full Cleanup")
            return
        if button_id == "full_cleanup_elevated":
            confirm = ConfirmScreen("Cleaning Docker is destructive — run elevated. Confirm?")
            await self.push_screen(confirm)
            if not confirm.result:
                self.write_ui_log("Full Cleanup (Elevado) cancelled by user.")
                return
            # Launch elevated Python process using ShellExecuteW
            try:
                import ctypes
                repo_root = Path(__file__).parent
                script_path = repo_root / "wsl_docker_cleaner.py"
                if not script_path.exists():
                    self.write_ui_log("wsl_docker_cleaner.py not found for elevated run.")
                    return
                python_exe = sys.executable
                params = f'"{script_path}"'
                self.write_ui_log("Launching Full Cleanup elevated (UAC) — you will see a prompt")
                ctypes.windll.shell32.ShellExecuteW(None, "runas", python_exe, params, None, 1)
                self.write_ui_log("Elevated process launched.")
            except Exception as e:
                self.write_ui_log(f"Failed to launch elevated process: {e}")
            return
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

    def write_ui_log(self, message: str) -> None:
        logger = self.query_one(Log)
        logger.write(message)

    class _LogWriter:
        """File-like writer that streams data into the app's Log widget.

        It uses `call_from_thread` to safely schedule UI updates when writing from a worker.
        """

        def __init__(self, app: "CommandRunnerApp", prefix: str = "") -> None:
            self.app = app
            self.prefix = prefix

        def write(self, text: str) -> None:
            # Ensure writing to the widget occurs on the app thread
            def _write():
                self.app.write_ui_log(f"{self.prefix}{text}")

            self.app.call_from_thread(_write)

        def flush(self) -> None:
            return None

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


if __name__ == "__main__":
    app = CommandRunnerApp()
    app.run()
