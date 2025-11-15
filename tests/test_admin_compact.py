import os
import pytest

from docker_cleaner.core import WSLDockerCleaner
from main import CommandRunnerApp, ConfirmScreen
import asyncio


def test_compact_vhdx_requires_admin(monkeypatch):
    cleaner = WSLDockerCleaner()
    # Ensure is_admin returns False to simulate lack of privileges
    monkeypatch.setattr(cleaner, "is_admin", lambda: False)
    cleaner.log_messages = []
    res = cleaner.compact_vhdx_files()
    assert res is False
    assert any("Execução como administrador recomendada" in m for m in cleaner.log_messages)


def test_docker_cleanup_logs_error_when_docker_not_found(monkeypatch, tmp_path):
    cleaner = WSLDockerCleaner()
    # Make the cleaner report docker not running
    monkeypatch.setattr(cleaner, "is_docker_running", lambda: False)
    # Ensure file existence check for Docker Desktop exe returns False
    monkeypatch.setattr(os.path, "exists", lambda path: False)
    cleaner.log_messages = []
    res = cleaner.docker_cleanup()
    assert res is False
    assert any("Docker Desktop não encontrado" in m for m in cleaner.log_messages)


def test_ask_elevate_and_cancel(monkeypatch):
    app = CommandRunnerApp()
    messages = []
    monkeypatch.setattr(app, "write_ui_log", lambda msg: messages.append(msg))

    async def fake_push_screen(screen):
        # Simulate the user pressing "Cancelar" in the ConfirmScreen
        if isinstance(screen, ConfirmScreen):
            screen.result = False
        return None

    monkeypatch.setattr(app, "push_screen", fake_push_screen)
    # Replace ShellExecute invocation to avoid actual elevation during tests
    monkeypatch.setattr("ctypes.windll.shell32.ShellExecuteW", lambda *args, **kwargs: 1)
    asyncio.run(app._ask_elevate_and_relaunch("Teste Elevação"))
    assert any("cancelada pelo usuário" in m for m in messages)


def test_ask_elevate_and_confirm_runs_helper(monkeypatch):
    app = CommandRunnerApp()
    messages = []
    monkeypatch.setattr(app, "write_ui_log", lambda msg: messages.append(msg))

    async def fake_push_screen(screen):
        # Simulate the user pressing "Confirmar" in the ConfirmScreen
        if isinstance(screen, ConfirmScreen):
            screen.result = True
        return None

    monkeypatch.setattr(app, "push_screen", fake_push_screen)
    # Replace ShellExecute method so we don't actually elevate the process
    import ctypes
    monkeypatch.setattr(ctypes.windll.shell32, "ShellExecuteW", lambda *a, **k: 1)
    import asyncio
    asyncio.run(app._ask_elevate_and_relaunch("Compactar VHDX"))
    assert any("Administrador solicitado" in m for m in messages)
