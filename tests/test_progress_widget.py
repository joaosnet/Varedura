import pytest
from main import CommandRunnerApp


@pytest.mark.asyncio
async def test_progress_widget_start_and_update(textual_app):
    """Test progress widget starts and updates correctly."""
    app = CommandRunnerApp()
    async with app.run_test(size=(80, 24)) as pilot:
        app.start_progress("Test Progress", 100)
        await pilot.pause()
        
        progress_widget = app.query_one("#progress")
        # Check progress is started
        assert hasattr(progress_widget, "_progress") and progress_widget._progress is not None
        
        app.update_progress(50)
        await pilot.pause()
        # Check progress value is stored
        assert progress_widget.progress_value == 50


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
        assert app.query_one("#progress").progress_value == 50


@pytest.mark.asyncio
async def test_progress_widget_finish(textual_app):
    """Test progress widget finish clears the display."""
    app = CommandRunnerApp()
    async with app.run_test(size=(80, 24)) as pilot:
        app.start_progress("Test", 100)
        await pilot.pause()
        
        progress_widget = app.query_one("#progress")
        rendered = str(progress_widget.render())
        assert rendered != ""
        
        app.finish_progress()
        await pilot.pause(delay=1.6)  # Wait for the timer to clear
        
        assert str(progress_widget.render()) == ""


@pytest.mark.asyncio
async def test_progress_widget_spinner_show_hide(textual_app):
    """Test spinner shows during progress and hides after finish."""
    app = CommandRunnerApp()
    async with app.run_test(size=(80, 24)) as pilot:
        spinner = app.query_one("#spinner")
        assert "hidden" in spinner.classes
        
        app.start_progress("Test", 100)
        await pilot.pause()
        assert "hidden" not in spinner.classes
        
        app.finish_progress()
        await pilot.pause(delay=1.6)
        assert "hidden" in spinner.classes
