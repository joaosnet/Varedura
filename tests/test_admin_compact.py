import os
import pytest

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
    app = CommandRunnerApp()
    async with app.run_test() as pilot:
        # Mock push_screen to simulate cancel
        async def mock_push_screen(screen, wait_for_dismiss=False):
            return False  # Cancel
        app.push_screen = mock_push_screen
        await app._ask_elevate_and_relaunch("Teste Elevação")
        
        log_widget = app.query_one("#log")
        log_content = "\n".join(str(line) for line in log_widget.lines)
        assert "cancelada pelo usuário" in log_content


@pytest.mark.asyncio
async def test_ask_elevate_and_confirm_runs_helper(textual_app):
    app = CommandRunnerApp()
    async with app.run_test() as pilot:
        # Mock push_screen to simulate confirm
        async def mock_push_screen(screen, wait_for_dismiss=False):
            return True  # Confirm
        app.push_screen = mock_push_screen
        await app._ask_elevate_and_relaunch("Compactar VHDX")
        
        log_widget = app.query_one("#log")
        log_content = "\n".join(str(line) for line in log_widget.lines)
        assert "Administrador solicitado" in log_content
