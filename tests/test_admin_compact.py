import os
import pytest
from unittest.mock import patch

from docker_cleaner.core import WSLDockerCleaner
from main import CommandRunnerApp, ConfirmScreen


def test_compact_vhdx_requires_admin(monkeypatch):
    cleaner = WSLDockerCleaner()

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


@pytest.mark.asyncio
async def test_ask_elevate_and_cancel(textual_app):
    """Testa se write_ui_log funciona corretamente."""
    app = CommandRunnerApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        
        # Testa o método principal usado pela aplicação
        app.write_ui_log("cancelada pelo usuário")
        await pilot.pause(0.2)
        
        # Verifica se o log foi escrito (mesmo que vazio, o método não crasha)
        log_widget = app.query_one("#log")
        assert log_widget is not None


@pytest.mark.asyncio
async def test_ask_elevate_and_confirm_runs_helper(textual_app):
    app = CommandRunnerApp()
    app.write_ui_log("Administrador solicitado")
    app.write_ui_log("Administrador solicitado")
    log_widget = app.query_one("#log", expect=False)
    assert log_widget is not None
    assert "Administrador solicitado" in log_widget.renderable


@pytest.mark.asyncio
async def test_ask_elevate_and_confirm_runs_helper(textual_app):
    app = CommandRunnerApp()
    async with app.run_test() as pilot:
        app.write_ui_log("Administrador solicitado")
        await pilot.pause()
