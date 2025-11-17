import pytest
from textual.widgets import Checkbox
from main import ConfirmScreen, CleanupOptionsScreen, CommandRunnerApp


@pytest.mark.asyncio
async def test_confirm_screen_accept(textual_app):
    """Test ConfirmScreen accepts confirmation."""
    app = CommandRunnerApp()
    screen = ConfirmScreen("Test message")
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.click("#confirm_yes")
        await pilot.pause()
        # Check screen was dismissed
        assert app.screen != screen


@pytest.mark.asyncio
async def test_confirm_screen_cancel(textual_app):
    """Test ConfirmScreen cancels."""
    app = CommandRunnerApp()
    screen = ConfirmScreen("Test message")
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.click("#confirm_no")
        await pilot.pause()
        assert app.screen != screen


@pytest.mark.asyncio
async def test_cleanup_options_screen_quick_preset(textual_app):
    """Test CleanupOptionsScreen quick preset sets correct checkboxes."""
    app = CommandRunnerApp()
    defaults = {"opt_prune_containers": False, "opt_prune_images": False, "opt_prune_volumes": False}
    screen = CleanupOptionsScreen("Test", defaults=defaults)
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.click("#opts_preset_quick")
        await pilot.pause()
        
        # Check checkboxes are set
        assert screen.query_one("#opt_prune_containers", Checkbox).value is True
        assert screen.query_one("#opt_prune_images", Checkbox).value is True
        assert screen.query_one("#opt_prune_volumes", Checkbox).value is True
        assert screen.query_one("#opt_stop_wsl", Checkbox).value is False


@pytest.mark.asyncio
async def test_cleanup_options_screen_full_preset(textual_app):
    """Test CleanupOptionsScreen full preset sets all checkboxes."""
    app = CommandRunnerApp()
    screen = CleanupOptionsScreen("Test")
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.click("#opts_preset_full")
        await pilot.pause()
        
        # Check all checkboxes are set
        for chk in screen.query("Checkbox"):
            assert chk.value is True


@pytest.mark.asyncio
async def test_cleanup_options_screen_clear(textual_app):
    """Test CleanupOptionsScreen clear unsets all checkboxes."""
    app = CommandRunnerApp()
    screen = CleanupOptionsScreen("Test", {"opt_prune_containers": True})
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.click("#opts_clear")
        await pilot.pause()
        
        # Check all checkboxes are unset
        for chk in screen.query("Checkbox"):
            assert chk.value is False


@pytest.mark.asyncio
async def test_cleanup_options_screen_execute(textual_app):
    """Test CleanupOptionsScreen execute dismisses with selected options."""
    app = CommandRunnerApp()
    screen = CleanupOptionsScreen("Test")
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.click("#opt_prune_containers")  # Select one option
        await pilot.click("#opts_exec")
        await pilot.pause()
        
        assert screen.selected_options["opt_prune_containers"] is True
        assert screen.selected_options["opt_prune_images"] is False
        # Check dismissed
        assert app.screen != screen


@pytest.mark.asyncio
async def test_cleanup_options_screen_cancel(textual_app):
    """Test CleanupOptionsScreen cancel dismisses without result."""
    app = CommandRunnerApp()
    screen = CleanupOptionsScreen("Test")
    async with app.run_test() as pilot:
        await app.push_screen(screen)
        await pilot.click("#opts_cancel")
        await pilot.pause()
        
        assert screen.selected_options == {}
        assert app.screen != screen
