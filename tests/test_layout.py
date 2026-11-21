"""Régua única de breakpoints e modo compacto da TUI."""

from __future__ import annotations

import pytest

from cli import ui_shared
from cli.layout import MEDIUM, NARROW, WIDE, columns_for, layout_tier
from cli.textual_app import VareduraTextualApp
from textual.widgets import Button, Digits, Label, TabbedContent


def test_layout_tiers_and_columns():
    assert [layout_tier(w) for w in (40, 75, 76, 111, 112, 200)] == [
        NARROW,
        NARROW,
        MEDIUM,
        MEDIUM,
        WIDE,
        WIDE,
    ]
    assert [columns_for("network-cards", w) for w in (54, 90, 140)] == [1, 2, 3]
    assert [columns_for("network-controls", w) for w in (54, 90, 140)] == [2, 3, 4]
    assert [columns_for("termux-tools", w) for w in (54, 90, 140)] == [1, 2, 3]
    assert [columns_for("camera-cards", w) for w in (54, 90, 140)] == [1, 1, 2]


@pytest.fixture
def _prefs(monkeypatch, tmp_path):
    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    ui_shared.save_network_config(
        {
            "target_onboarding_completed": True,
            "selected_target_ids": ["cloudflare_ipv4"],
            "primary_target_id": "cloudflare_ipv4",
            "custom_targets": [],
            "league_auto_detect": False,
        }
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("width", "compact"), [(54, True), (120, False)])
async def test_compact_mode_only_on_narrow_screens(_prefs, width, compact):
    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    app._start_network = lambda: None
    async with app.run_test(size=(width, 40)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "network"
        for _ in range(30):
            await pilot.pause()
            if "network" in app._hydrated_tabs:
                break
        await pilot.pause()

        assert app.screen.has_class("mobile-narrow") is compact
        assert app.screen.has_class("bp-narrow") is compact
        assert app.screen.has_class("bp-wide") is (width >= 112)

        button = app.query_one("#network-export", Button)
        card = app.query_one("#gateway-card")
        value = app.query_one("#gateway-value", Label)
        digits = app.query_one("#gateway-digits", Digits)
        if compact:
            # Botão de 1 linha e card de 2 linhas, com o valor em texto.
            assert button.outer_size.height == 1
            assert card.outer_size.height == 2
            assert value.display and not digits.display
        else:
            assert button.outer_size.height == 3
            assert card.outer_size.height == 12
            assert digits.display and not value.display


@pytest.mark.asyncio
async def test_theme_toggle_persists_and_narrow_header_has_no_subtitle(_prefs):
    from cli.theme import DARK, LIGHT
    from textual.widgets import Footer

    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    async with app.run_test(size=(54, 40)) as pilot:
        await pilot.pause()
        assert app.theme == DARK
        assert app.sub_title == ""  # subtítulo seria cortado em tela estreita
        footer = app.query_one(Footer)
        assert footer.compact and not footer.show_command_palette

        await pilot.press("d")
        await pilot.pause()
        assert app.theme == LIGHT
        assert ui_shared.load_dark_theme_pref() is False

    wide = VareduraTextualApp()
    wide._after_first_refresh = lambda: None
    async with wide.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert wide.theme == LIGHT  # escolha lembrada entre execuções
        assert wide.sub_title != ""
