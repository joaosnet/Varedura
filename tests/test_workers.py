import pytest
from main import CommandRunnerApp
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_worker_full_cleanup(textual_app):
    """Test full cleanup worker completes successfully."""
    app = CommandRunnerApp()
    
    from unittest.mock import MagicMock
    
    async def mock_run_command_async(cmd, shell=False, stream_callback=None):
        mock_result = MagicMock()
        mock_result.stdout = "mock output"
        if stream_callback:
            if "docker cleanup" in cmd:
                stream_callback("Docker cleanup done\n")
            elif "stop" in cmd:
                stream_callback("Stop WSL done\n")
            elif "sparse" in cmd:
                stream_callback("Sparse done\n")
            elif "compact" in cmd:
                stream_callback("Compact done\n")
        return mock_result
    
    with patch('docker_cleaner.core.WSLDockerCleaner.run_command_async', side_effect=mock_run_command_async):
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.click("#docker_cleanup")
            await pilot.pause(delay=3.0)  # Wait for worker to complete
            
            # Check log contains completion message
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "LIMPEZA DO DOCKER CONCLUÍDA" in log_content


@pytest.mark.asyncio
async def test_run_prune_containers(textual_app):
    """Test prune containers worker."""
    app = CommandRunnerApp()
    
    async def mock_run_command_async(cmd, shell=False, stream_callback=None):
        if stream_callback:
            stream_callback("Prune containers completo\n")
        return True
    
    with patch('docker_cleaner.core.WSLDockerCleaner.run_command_async', side_effect=mock_run_command_async):
        async with app.run_test(size=(120, 40)) as pilot:
            app._run_prune_containers()
            await pilot.pause(delay=2.0)
            
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "Prune containers completo" in log_content


@pytest.mark.asyncio
async def test_run_prune_images(textual_app):
    """Test prune images worker."""
    app = CommandRunnerApp()
    
    async def mock_run_command_async(cmd, shell=False, stream_callback=None):
        if stream_callback:
            stream_callback("Prune images completo\n")
        return True
    
    with patch('docker_cleaner.core.WSLDockerCleaner.run_command_async', side_effect=mock_run_command_async):
        async with app.run_test(size=(120, 40)) as pilot:
            app._run_prune_images()
            await pilot.pause(delay=2.0)
            
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "Prune images completo" in log_content


@pytest.mark.asyncio
async def test_run_prune_volumes(textual_app):
    """Test prune volumes worker."""
    app = CommandRunnerApp()
    
    async def mock_run_command_async(cmd, shell=False, stream_callback=None):
        if stream_callback:
            stream_callback("Prune volumes completo\n")
        return True
    
    with patch('docker_cleaner.core.WSLDockerCleaner.run_command_async', side_effect=mock_run_command_async):
        async with app.run_test(size=(120, 40)) as pilot:
            app._run_prune_volumes()
            await pilot.pause(delay=2.0)
            
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "Prune volumes completo" in log_content


@pytest.mark.asyncio
async def test_run_compact_vhdx(textual_app):
    """Test compact vhdx worker."""
    app = CommandRunnerApp()
    
    async def mock_run_command_async(cmd, shell=False, stream_callback=None):
        if stream_callback:
            stream_callback("Compact VHDX concluído com sucesso\n")
        return True
    
    with patch('docker_cleaner.core.WSLDockerCleaner.run_command_async', side_effect=mock_run_command_async):
        async with app.run_test(size=(120, 40)) as pilot:
            app._run_compact_vhdx()
            await pilot.pause(delay=2.0)
            
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "Compact VHDX concluído com sucesso" in log_content


@pytest.mark.asyncio
async def test_worker_prune_containers(textual_app):
    """Test prune containers worker via options screen."""
    app = CommandRunnerApp()
    
    async def mock_run_command_async(cmd, shell=False, stream_callback=None):
        if stream_callback:
            stream_callback("Prune containers completo\n")
        return True
    
    with patch('docker_cleaner.core.WSLDockerCleaner.run_command_async', side_effect=mock_run_command_async):
        async with app.run_test(size=(120, 40)) as pilot:
            app._run_prune_containers()
            await pilot.pause(delay=2.0)
            
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "Prune containers completo" in log_content


@pytest.mark.asyncio
async def test_worker_stop_wsl(textual_app):
    """Test stop WSL worker via options screen."""
    app = CommandRunnerApp()
    
    async def mock_run_command_async(cmd, shell=False, stream_callback=None):
        if stream_callback:
            stream_callback("Stop WSL concluído\n")
        return True
    
    with patch('docker_cleaner.core.WSLDockerCleaner.run_command_async', side_effect=mock_run_command_async):
        async with app.run_test(size=(120, 40)) as pilot:
            app._run_stop_wsl()
            await pilot.pause(delay=2.0)
            
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "Stop WSL concluído" in log_content


@pytest.mark.asyncio
async def test_worker_cleanup_temp(textual_app):
    """Test cleanup temp worker via options screen."""
    app = CommandRunnerApp()
    
    mock_process = MagicMock()
    mock_process.returncode = 0
    mock_process.stdout = ""
    mock_process.stderr = ""
    
    with patch('docker_cleaner.core.subprocess.run', return_value=mock_process):
        async with app.run_test(size=(120, 40)) as pilot:
            app._run_cleanup_temp()
            await pilot.pause(delay=2.0)
            
            log_widget = app.query_one("#log")
            log_content = "\n".join(str(line) for line in log_widget.lines)
            assert "Cleanup temp error" in log_content


@pytest.mark.asyncio
async def test_worker_models_generator(textual_app):
    """Test models generator worker."""
    app = CommandRunnerApp()
    async with app.run_test(size=(120, 40)) as pilot:
        # Set input value
        input_widget = app.query_one("#models_path")
        input_widget.value = "lmarena_models.txt"
        
        await pilot.click("#run_models")
        await pilot.pause(delay=2.0)
        
        log_widget = app.query_one("#log")
        log_content = "\n".join(str(line) for line in log_widget.lines)
        assert "Models Generator" in log_content
        assert "Processo finalizado" in log_content
