"""Tests for the integrated Câmeras (RTSP) tab in the Varedura Textual app."""

import asyncio

import pytest

from cli import ui_shared
from cli.textual_app import VareduraTextualApp
from i18n import init as i18n_init
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Label,
    RadioSet,
    Static,
    TabbedContent,
)


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
    ui_shared.save_network_config(
        {
            "network_schema_version": 3,
            "target_onboarding_completed": True,
            "selected_target_ids": ["cloudflare_ipv4"],
            "primary_target_id": "cloudflare_ipv4",
            "custom_targets": [],
            "league_auto_detect": False,
        }
    )
    yield
    i18n_init("en")


async def wait_until(predicate, pilot, attempts: int = 100) -> None:
    for _ in range(attempts):
        await pilot.pause()
        if predicate():
            return
        await asyncio.sleep(0.01)
    raise AssertionError("condition was not reached")


async def open_cameras(app, pilot) -> None:
    app.query_one("#main-tabs", TabbedContent).active = "cameras"
    await wait_until(
        lambda: (
            app._cameras_rendered
            and bool(list(app.query("#cameras-subtabs")))
            and bool(list(app.query("#--content-tab-tab-cred")))
        ),
        pilot,
        attempts=200,
    )


@pytest.mark.asyncio
async def test_cameras_tab_renders(monkeypatch):
    # Avoid any real network during card render / geolocation.
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
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
        await open_cameras(app, pilot)
        app.query_one("#cameras-subtabs", TabbedContent).active = "tab-portas"
        await pilot.pause()
        app.query_one("#portas-host").value = "192.168.1.10"
        app.query_one("#btn-portas").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#btn-portas")
        await wait_until(
            lambda: app.query_one("#portas-tabela", DataTable).row_count == 3, pilot, attempts=200
        )


@pytest.mark.asyncio
async def test_cameras_credential_add_and_remove(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        app.query_one("#cameras-subtabs", TabbedContent).active = "tab-cred"
        await pilot.pause()

        app.query_one("#cred-user").value = "admin"
        app.query_one("#cred-pass").value = "1234"
        app.query_one("#btn-cred-add").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#btn-cred-add")
        await wait_until(
            lambda: app.query_one("#cred-tabela", DataTable).row_count == 1, pilot
        )
        assert len(app._vault) == 1

        app.query_one("#btn-cred-del").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#btn-cred-del")
        await wait_until(
            lambda: app.query_one("#cred-tabela", DataTable).row_count == 0, pilot
        )


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
        await open_cameras(app, pilot)
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
        await open_cameras(app, pilot)
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
    launches: list[str] = []
    async with app.run_test(size=(120, 50)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        await pilot.pause()
        # Não abre um player de verdade no teste.
        monkeypatch.setattr(
            app,
            "_lancar_player",
            lambda url, ip=None: (launches.append(ip), opened.update(url=url, ip=ip)),
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
        # ... e abrir UMA vez só: antes o clique disparava dois players.
        for _ in range(5):
            await pilot.pause()
        assert launches == ["192.168.1.50"]

        # Mesmo com duplo-clique por hábito (chain=2), abre só uma vez.
        launches.clear()
        await pilot.click("#rede-tabela", offset=(4, 2), times=2)
        for _ in range(5):
            await pilot.pause()
        assert launches == ["192.168.1.50"]


@pytest.mark.asyncio
async def test_cameras_open_port_saved_without_credential(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)
    monkeypatch.setattr(
        "cli.textual_cameras.escanear_rede",
        lambda base, ao_progresso=None: ["192.168.1.50"],
    )
    # No credential combination validates a stream.
    monkeypatch.setattr("cli.textual_cameras.resolver_ip", lambda *a, **k: None)

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 55)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        await pilot.pause()
        # Port 554 open but no credential -> still saved and counted as a camera.
        app._scan_faixa("192.168.1")
        await wait_until(
            lambda: app.query_one("#rede-tabela", DataTable).row_count == 1, pilot
        )
        assert app._cameras_encontradas == 1
        assert "192.168.1.50" in app._urls_rede


@pytest.mark.asyncio
async def test_cameras_rtsp_snapshot_mpv_and_copy(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    snaps: list[tuple[str, str]] = []
    mpv_cmds: list[list[str]] = []
    copied: list[str] = []

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 55)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        app.query_one("#cameras-subtabs", TabbedContent).active = "tab-rtsp"
        await pilot.pause()

        monkeypatch.setattr(
            "cli.textual_cameras.capturar_e_abrir_snapshot",
            lambda url, destino, timeout=10.0: snaps.append((url, destino))
            or (True, destino),
        )
        monkeypatch.setattr(
            "cli.textual_cameras.comando_mpv_terminal",
            lambda url: ["mpv", "--vo=tct", url],
        )
        monkeypatch.setattr(
            "cli.textual_cameras.subprocess.run",
            lambda cmd, **kwargs: mpv_cmds.append(list(cmd)) or type("P", (), {"returncode": 0})(),
        )
        monkeypatch.setattr(
            "cli.textual_cameras.copy_to_clipboard",
            lambda text: copied.append(text) or True,
        )

        app.query_one("#rtsp-url").value = "rtsp://192.168.1.10:554/stream1"
        app.query_one("#rtsp-user").value = "admin"
        app.query_one("#rtsp-pass").value = "pass"

        for btn_id in ("#btn-rtsp-snap", "#btn-rtsp-mpv", "#btn-rtsp-copy"):
            app.query_one(btn_id).scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click(btn_id)

        await wait_until(lambda: len(snaps) == 1, pilot)
        expected_url = "rtsp://admin:pass@192.168.1.10:554/stream1"
        assert snaps[0][0] == expected_url
        assert "exports" in snaps[0][1] and snaps[0][1].endswith(".jpg")
        assert mpv_cmds == [["mpv", "--vo=tct", expected_url]]
        assert copied == [expected_url]


@pytest.mark.asyncio
async def test_cameras_rede_action_bar_and_empty_selection(monkeypatch):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    snaps: list[str] = []
    mpv_cmds: list[list[str]] = []
    copied: list[str] = []
    warnings: list[str] = []

    app = VareduraTextualApp()
    async with app.run_test(size=(120, 55)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        await pilot.pause()

        monkeypatch.setattr(
            "cli.textual_cameras.capturar_e_abrir_snapshot",
            lambda url, destino, timeout=10.0: snaps.append(url) or (True, destino),
        )
        monkeypatch.setattr(
            "cli.textual_cameras.comando_mpv_terminal",
            lambda url: ["mpv", "--vo=tct", url],
        )
        monkeypatch.setattr(
            "cli.textual_cameras.subprocess.run",
            lambda cmd, **kwargs: mpv_cmds.append(list(cmd)) or type("P", (), {"returncode": 0})(),
        )
        monkeypatch.setattr(
            "cli.textual_cameras.copy_to_clipboard",
            lambda text: copied.append(text) or True,
        )
        orig_notify = app.notify
        monkeypatch.setattr(
            app,
            "notify",
            lambda msg, **kw: warnings.append(str(msg))
            if kw.get("severity") == "warning"
            else orig_notify(msg, **kw),
        )

        # Empty table warns instead of crashing
        app.query_one("#btn-rede-snap").scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#btn-rede-snap")
        await pilot.pause()
        assert warnings and not snaps

        # Select populated row
        cam_url = "rtsp://admin:123@192.168.1.50:554/ch1"
        app._urls_rede["192.168.1.50"] = cam_url
        tabela = app.query_one("#rede-tabela", DataTable)
        tabela.add_row("192.168.1.50", "ok", "admin", "/ch1", "720p", "h264", key="192.168.1.50")
        await pilot.pause()

        for btn_id in ("#btn-rede-snap", "#btn-rede-mpv", "#btn-rede-copy"):
            app.query_one(btn_id).scroll_visible(animate=False)
            await pilot.pause()
            await pilot.click(btn_id)

        await wait_until(lambda: len(snaps) == 1, pilot)
        assert snaps == [cam_url]
        assert mpv_cmds == [["mpv", "--vo=tct", cam_url]]
        assert copied == [cam_url]


@pytest.mark.asyncio
async def test_cameras_action_cam_log_non_windows(monkeypatch, tmp_path):
    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    opened: list[str] = []
    app = VareduraTextualApp()
    async with app.run_test(size=(100, 40)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        await pilot.pause()

        fake_log = tmp_path / "cameras.log"
        fake_log.write_text("log\n", encoding="utf-8")
        monkeypatch.setattr("cli.textual_cameras.ARQUIVO_LOG", fake_log)
        monkeypatch.setattr("os.name", "posix")
        monkeypatch.setattr("cli.textual_cameras.shutil.which", lambda name: None)
        monkeypatch.setattr(
            "cli.textual_cameras.open_file_or_url",
            lambda target: opened.append(target) or True,
        )

        app.action_cam_log()
        assert opened == [str(fake_log)]


@pytest.mark.asyncio
async def test_cameras_401_limit_preserves_saved_url_and_opens_on_click(monkeypatch):
    from rtsp import credenciais, video

    monkeypatch.setattr("cli.textual_cameras.detectar_redes", lambda: [])
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)
    monkeypatch.setattr(
        "cli.textual_cameras.escanear_rede",
        lambda base, ao_progresso=None: ["192.168.1.50"],
    )

    def fake_resolver(ip, candidatos, vault, conhecidos, monta_url, **kwargs):
        diag = kwargs.get("diagnostico")
        if diag is not None:
            diag.update(
                {
                    "erro_tipo": video.ERRO_AUTH,
                    "mensagem": "401 Unauthorized",
                    "tentativas": 4,
                    "falhas_auth": 4,
                    "limite_atingido": True,
                }
            )
        return None

    monkeypatch.setattr("cli.textual_cameras.resolver_ip", fake_resolver)

    saved_url = "rtsp://admin:savedpass@192.168.1.50:554/stream1"
    app = VareduraTextualApp()
    launches: list[tuple[str, str | None]] = []
    async with app.run_test(size=(120, 55)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        await pilot.pause()
        app._conhecidos["192.168.1.50"] = credenciais.CredencialIP(
            usuario="admin",
            senha="savedpass",
            caminho="/stream1",
            url=saved_url,
        )
        monkeypatch.setattr(
            app,
            "_lancar_player",
            lambda url, ip=None: launches.append((url, ip)),
        )

        app._scan_faixa("192.168.1")
        await wait_until(
            lambda: app.query_one("#rede-tabela", DataTable).row_count == 1
            and "192.168.1.50" in app._falhas_rede,
            pilot,
        )
        assert app._urls_rede["192.168.1.50"] == saved_url
        assert "4" in app._falhas_rede["192.168.1.50"]

        tabela = app.query_one("#rede-tabela", DataTable)
        tabela.scroll_visible(animate=False)
        await pilot.pause()
        await pilot.click("#rede-tabela", offset=(4, 2))
        await wait_until(lambda: len(launches) == 1, pilot)
        assert launches == [(saved_url, "192.168.1.50")]


def _widget_visible(widget) -> bool:
    cur = widget
    while cur is not None:
        if not cur.display:
            return False
        cur = cur.parent
    return True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("width", "height"),
    [(48, 28), (64, 30), (88, 32), (120, 38), (160, 44)],
)
async def test_cameras_responsive_no_clipping_across_viewports(
    monkeypatch, width, height
):
    from rtsp import credenciais, rede, regioes

    regioes.salvar_regioes(
        [
            regioes.Regiao(
                "Casa da Praia - Portão Principal",
                regioes.TIPO_CAMERA,
                "cam.exemplo.ddns.net",
                554,
            ),
            regioes.Regiao(
                "Escritório Centro", regioes.TIPO_REDE, "10.0.0.0/22", 554
            ),
        ]
    )
    credenciais.salvar_vault([credenciais.Par("admin", "123456")])
    credenciais.salvar_conhecidos(
        {
            "192.168.18.82": credenciais.CredencialIP(
                "admin",
                "x",
                "/stream1",
                "rtsp://admin:x@192.168.18.82:554/stream1",
                "h264",
                "1920x1080",
            )
        }
    )
    monkeypatch.setattr(
        "cli.textual_cameras.detectar_redes",
        lambda: [
            rede.RedeLocal(
                base="192.168.18", ip_local="192.168.18.15", primaria=True
            ),
            rede.RedeLocal(
                base="172.25.0", ip_local="172.25.0.1", primaria=False
            ),
        ],
    )
    monkeypatch.setattr("cli.textual_cameras.geolocalizar", lambda *a, **k: None)

    app = VareduraTextualApp()
    app._after_first_refresh = lambda: None
    async with app.run_test(size=(width, height)) as pilot:
        await pilot.pause()
        await open_cameras(app, pilot)
        await wait_until(lambda: bool(list(app.query("#card-regiao-0"))), pilot)
        await pilot.pause()

        rede_tbl = app.query_one("#rede-tabela", DataTable)
        rede_tbl.add_row(
            "192.168.18.82",
            "ok",
            "admin",
            "/stream1",
            "1920x1080",
            "h264",
            key="192.168.18.82",
        )
        portas_tbl = app.query_one("#portas-tabela", DataTable)
        portas_tbl.add_row("554", "ABERTA")
        await pilot.pause()

        if (width, height) == (120, 38):
            assert rede_tbl.region.y < height

        if (width, height) == (48, 28):
            card0 = app.query_one("#card-regiao-0", Button)
            del0 = app.query_one("#del-regiao-0", Button)
            assert del0.region.height == 1
            assert card0.region.height >= 2
            assert card0.region.right <= card0.parent.content_region.right

        subtabs = app.query_one("#cameras-subtabs", TabbedContent)
        for subtab_id in ("tab-rede", "tab-rtsp", "tab-portas", "tab-cred"):
            subtabs.active = subtab_id
            await pilot.pause()
            await pilot.pause()
            if subtab_id == "tab-rede":
                for col in app.query("#tab-rede Collapsible"):
                    if col.id not in ("col-mapa", "col-outras"):
                        col.collapsed = False
                await pilot.pause()
                await pilot.pause()

            if subtab_id == "tab-cred":
                forms = app.query_one("#cred-forms")
                tables = app.query_one("#cred-tables")
                if width < 112:
                    assert tables.region.y >= forms.region.bottom
                else:
                    assert tables.region.x >= forms.region.right

            pane = app.query_one(f"#{subtab_id}")
            for wid in pane.query("*"):
                if not _widget_visible(wid):
                    continue
                r = wid.region
                pr = wid.parent.content_region if wid.parent else r
                if isinstance(wid, (Button, Input, Label, Static, RadioSet)):
                    assert r.width > 0 and r.height > 0, f"{subtab_id} {wid} zero size"
                    if pr.width > 0:
                        assert r.right <= pr.right, (
                            f"{width}x{height} {subtab_id} {wid} clipped: {r} > {pr}"
                        )
                if isinstance(wid, Input):
                    min_w = 10 if wid.id == "regiao-porta" else 18
                    assert r.width >= min_w, (
                        f"{width}x{height} {subtab_id} #{wid.id} narrow: w={r.width}"
                    )
                if isinstance(wid, DataTable):
                    assert r.height >= 6, (
                        f"{width}x{height} {subtab_id} #{wid.id} short: h={r.height}"
                    )
