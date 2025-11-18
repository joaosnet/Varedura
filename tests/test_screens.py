import pytest
from textual.widgets import Checkbox
from main import ConfirmScreen, CleanupOptionsScreen, CommandRunnerApp


@pytest.mark.asyncio
async def test_confirm_screen_accept(textual_app):
    """Test ConfirmScreen accepts confirmation."""
    app = CommandRunnerApp()
    screen = ConfirmScreen("Test message")
    async with app.run_test(size=(80, 24)) as pilot:
        await app.push_screen(screen)
        await pilot.click("#confirm_yes")
        await pilot.pause(0.5)
        # Check screen was dismissed
        assert app.screen != screen


@pytest.mark.asyncio
async def test_confirm_screen_cancel(textual_app):
    """Test ConfirmScreen cancels."""
    app = CommandRunnerApp()
    screen = ConfirmScreen("Test message")
    async with app.run_test(size=(80, 24)) as pilot:
        await app.push_screen(screen)
        await pilot.click("#confirm_no")
        await pilot.pause(1.0)
        assert app.screen != screen


@pytest.mark.asyncio
async def test_cleanup_options_screen_execute(textual_app):
    """Test CleanupOptionsScreen execute dismisses with selected options."""
    app = CommandRunnerApp()
    screen = CleanupOptionsScreen("Test")
    async with app.run_test(size=(200, 50)) as pilot:
        await app.push_screen(screen)
        await pilot.click("#opt_prune_containers")  # Select one option
        await pilot.click("#opts_exec")
        await pilot.pause(0.5)
        
        assert screen.selected_options["opt_prune_containers"] is True
        assert screen.selected_options["opt_prune_images"] is False
        # Check dismissed
        assert app.screen != screen


@pytest.mark.asyncio
async def test_cleanup_options_screen_cancel(textual_app):
    """Test CleanupOptionsScreen cancel dismisses without result."""
    app = CommandRunnerApp()
    screen = CleanupOptionsScreen("Test")
    async with app.run_test(size=(200, 50)) as pilot:
        await app.push_screen(screen)
        await pilot.click("#opts_cancel")
        await pilot.pause(0.5)
        
        assert screen.selected_options == {}
        assert app.screen != screen
