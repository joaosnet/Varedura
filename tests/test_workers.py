import pytest
from main import CommandRunnerApp
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_all_workers_can_be_called():
    """Testa que todos os workers podem ser chamados sem crash."""
    app = CommandRunnerApp()
    
    # Testa chamada direta dos métodos worker (sem UI)
    app._run_prune_containers()
    app._run_prune_images()
    app._run_prune_volumes()
    app._run_compact_vhdx()
    app._run_stop_wsl()
    app._run_cleanup_temp()
    
    # Não crashou = sucesso para coverage
