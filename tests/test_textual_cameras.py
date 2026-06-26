"""Tests for the integrated Câmeras (RTSP) tab in the Varedura Textual app."""

import asyncio

import pytest

from cli import ui_shared
from cli.textual_app import VareduraTextualApp
from i18n import init as i18n_init
from textual.widgets import DataTable, TabbedContent


@pytest.fixture(autouse=True)
def isolated_state(monkeypatch, tmp_path):
    """Keep the RTSP vault/regions and prefs off the real files, and offline."""
    import rtsp.credenciais as cred
    import rtsp.regioes as reg
    import monitor.netinfo as netinfo
    import monitor.stalker as stalker

    monkeypatch.setattr(cred, "ARQUIVO_VAULT", tmp_path / "credenciais.json")
    monkeypatch.setattr(cred, "ARQUIVO_CONHECIDOS", tmp_path / "ips_conhecidos.json")
    monkeypatch.setattr(reg, "ARQUIVO_REGIOES", tmp_path / "regioes.json")
    monkeypatch.setattr(ui_shared, "PREFS_FILE", tmp_path / "prefs.json")
    monkeypatch.setattr(ui_shared, "MCP_CONFIG_FILE", tmp_path / ".vscode" / "mcp.json")
    # Stay offline: no real gateway detection / ping from the dashboard poller.
    monkeypatch.setattr(netinfo, "detect_default_gateway", lambda: None)
    monkeypatch.setattr(stalker, "run_ping", lambda host: 12.0)

    import i18n

    monkeypatch.setattr(i18n, "_PREFS_FILE", tmp_path / "lang.json")
    i18n_init("en")
    yield
    i18n_init("en")


async def wait_until(predicate, pilot, attempts: int = 30) -> None:
    for _ in range(attempts):
        await pilot.pause()
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not reached")


@pytest.mark.asyncio
async def test_cameras_tab_renders(monkeypatch):
    # Avoid any real network during card render / geolocation.
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "cameras"
        await pilot.pause()

        # The four sub-tabs and their tables exist with the expected columns.
        assert app.query_one("#cameras-subtabs", TabbedContent)
        assert len(app.query_one("#rede-tabela", DataTable).columns) == 6
        assert len(app.query_one("#portas-tabela", DataTable).columns) == 2
        assert app._cameras_rendered is True


@pytest.mark.asyncio
async def test_cameras_port_scan_populates_table(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)
    monkeypatch.setattr(
        "cli.textual_cameras.escanear_portas_camera",
        lambda host: {554: True, 80: False, 8554: True},
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "cameras"
        app.query_one("#cameras-subtabs", TabbedContent).active = "tab-portas"
        await pilot.pause()
        app.query_one("#portas-host").value = "192.168.1.10"
        await pilot.click("#btn-portas")
        await wait_until(
            lambda: app.query_one("#portas-tabela", DataTable).row_count == 3, pilot
        )


@pytest.mark.asyncio
async def test_cameras_credential_add_and_remove(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "cameras"
        app.query_one("#cameras-subtabs", TabbedContent).active = "tab-cred"
        await pilot.pause()

        app.query_one("#cred-user").value = "admin"
        app.query_one("#cred-pass").value = "1234"
        await pilot.click("#btn-cred-add")
        await pilot.pause()
        assert app.query_one("#cred-tabela", DataTable).row_count == 1
        assert len(app._vault) == 1

        await pilot.click("#btn-cred-del")
        await pilot.pause()
        assert app.query_one("#cred-tabela", DataTable).row_count == 0


@pytest.mark.asyncio
async def test_cameras_import_credential_lists(monkeypatch, tmp_path):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)
    users = tmp_path / "users.txt"
    users.write_text("admin\nroot\n# comment\n", encoding="utf-8")
    passwords = tmp_path / "pass.txt"
    passwords.write_text("1234\nsenha\n", encoding="utf-8")

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 55)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "cameras"
        app.query_one("#cameras-subtabs", TabbedContent).active = "tab-cred"
        await pilot.pause()
        app.query_one("#imp-users").value = str(users)
        app.query_one("#imp-pass").value = str(passwords)
        app.query_one("#btn-cred-import").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#btn-cred-import")
        await pilot.pause()
        # 2 users × 2 passwords = 4 vault pairs.
        assert app.query_one("#cred-tabela", DataTable).row_count == 4
        assert len(app._vault) == 4


@pytest.mark.asyncio
async def test_cameras_browse_fills_input(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)
    # Mock the native file dialog: return a chosen path without opening a window.
    monkeypatch.setattr(
        "cli.textual_cameras._escolher_arquivo_txt",
        lambda *a, **k: ("C:/tmp/usuarios.txt", True),
    )

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 60)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "cameras"
        app.query_one("#cameras-subtabs", TabbedContent).active = "tab-cred"
        await pilot.pause()
        app.query_one("#btn-browse-users").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#btn-browse-users")
        await wait_until(
            lambda: app.query_one("#imp-users").value == "C:/tmp/usuarios.txt", pilot
        )


@pytest.mark.asyncio
async def test_saved_camera_opens_on_single_click(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    app = VareduraTextualApp()
    opened = {}
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "cameras"
        await pilot.pause()
        # Não abre um player de verdade no teste.
        monkeypatch.setattr(
            app, "_lancar_player", lambda url, ip=None: opened.update(url=url, ip=ip)
        )
        # Simula uma câmera salva na tabela de resultados.
        app._urls_rede["192.168.1.50"] = "rtsp://192.168.1.50:554/stream"
        tabela = app.query_one("#rede-tabela", DataTable)
        tabela.add_row("192.168.1.50", "ok", "-", "-", "-", "-", key="192.168.1.50")
        tabela.scroll_visible(animate=False)
        await pilot.pause()
        # Um único clique na primeira linha de dados deve abrir a câmera.
        # (offset y=2: linha 0 = borda, linha 1 = cabeçalho, linha 2 = 1ª linha)
        await pilot.click("#rede-tabela", offset=(4, 2))
        await wait_until(lambda: opened.get("ip") == "192.168.1.50", pilot)


@pytest.mark.asyncio
async def test_cameras_open_port_saved_without_credential(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)
    monkeypatch.setattr(
        "cli.textual_cameras.escanear_rede", lambda base, ao_progresso=None: ["192.168.1.50"]
    )
    # No credential combination validates a stream.
    monkeypatch.setattr("cli.textual_cameras.resolver_ip", lambda *a, **k: None)

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 55)) as pilot:
        await pilot.pause()
        app.query_one("#main-tabs", TabbedContent).active = "cameras"
        await pilot.pause()
        # Port 554 open but no credential -> still saved and counted as a camera.
        app._scan_faixa("192.168.1")
        await wait_until(
            lambda: app.query_one("#rede-tabela", DataTable).row_count == 1, pilot
        )
        assert app._cameras_encontradas == 1
        assert "192.168.1.50" in app._urls_rede
