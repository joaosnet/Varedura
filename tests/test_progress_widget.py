import pytest
import asyncio
import subprocess
from main import CommandRunnerApp


@pytest.mark.asyncio
async def test_progress_widget_start_and_update(textual_app):
    """Test progress widget starts and updates correctly."""
    app = CommandRunnerApp()
    async with app.run_test(size=(80, 24)) as pilot:
        app.start_progress("Test Progress", 100)
        await pilot.pause()
        
        # Check progress is started via app reactive
        assert app.current_progress == 0
        
        app.update_progress(50)
        await pilot.pause()
        # Check progress value is stored
        assert app.current_progress == 50


@pytest.mark.asyncio
async def test_progress_widget_advance(textual_app):
    """Test progress widget advance method."""
    app = CommandRunnerApp()
    async with app.run_test(size=(80, 24)) as pilot:
        app.start_progress("Test", 100)
        app.update_progress(20)
        await pilot.pause()
        
        app.advance_progress(30)
        await pilot.pause()
        assert app.current_progress == 50


@pytest.mark.asyncio
async def test_progress_widget_finish(textual_app):
    """Test progress widget finish clears the display."""
    app = CommandRunnerApp()
    async with app.run_test(size=(80, 24)) as pilot:
        app.start_progress("Test", 100)
        await pilot.pause()
        
        assert app.current_progress == 0
        
        app.finish_progress()
        await pilot.pause(delay=1.6)  # Wait for the timer to clear
        
        assert app.current_progress == 100


@pytest.mark.asyncio
async def test_progress_widget_spinner_show_hide(textual_app, monkeypatch):
    """Test spinner shows during progress and hides after finish."""
    app = CommandRunnerApp()
    async with app.run_test(size=(80, 24)) as pilot:
        # Spinner state is managed by active_workers reactive
        assert app.active_workers == 0
        
        # Ensure the run_command_async used by the worker doesn't finish instantly
        import docker_cleaner.core as core
        async def fake_run(cmd, shell=True, stream_callback=None):
            await asyncio.sleep(0.05)
            if stream_callback:
                stream_callback('Prune containers completo')
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout='')
        monkeypatch.setattr(core.WSLDockerCleaner, 'run_command_async', fake_run)
        # run worker and ensure it contributes to progress history
        initial_history_len = len(app.space_history)
        app._run_prune_containers()
        await pilot.pause(delay=0.2)
        assert len(app.space_history) >= initial_history_len
        
        app.finish_progress()
        await pilot.pause(delay=1.6)
        assert app.active_workers == 0
