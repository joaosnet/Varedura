"""Aba 'Câmeras' (descoberta/validação de câmeras IP·RTSP) para a TUI do Varedura.

Mixin com a UI e os workers, integrados no VareduraTextualApp. Toda a lógica
vive no pacote `rtsp/`; aqui ficam a composição das 4 sub-abas, os workers em
thread e a gamificação (radar/progresso/contador), com strings via i18n (t()).

Originalmente um app Textual standalone (scan_rsp); fundido como uma aba.
"""

from __future__ import annotations

import subprocess
import sys
from urllib.parse import quote, urlsplit, urlunsplit

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.coordinate import Coordinate
from textual.timer import Timer
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Input,
    Label,
    ProgressBar,
    RadioButton,
    RadioSet,
    Static,
    TabbedContent,
    TabPane,
)

from i18n import t
from rtsp.credenciais import (
    Par,
    adicionar_par,
    carregar_conhecidos,
    carregar_lista,
    carregar_vault,
    combinar_credenciais,
    esquecer_ip,
    remover_par,
    resolver_ip,
    salvar_vault,
)
from rtsp.geo import geolocalizar
from rtsp.log import ARQUIVO_LOG, obter_logger
from rtsp.mapa import Pino, cor_para, render as render_mapa
from rtsp.paths import caminhos as caminhos_conhecidos
from rtsp.rede import detectar_redes
from rtsp.regioes import (
    TIPO_CAMERA,
    TIPO_REDE,
    Regiao,
    adicionar_regiao,
    carregar_regioes,
    remover_regiao,
    salvar_regioes,
)
from rtsp.scanner import (
    escanear_portas_camera,
    escanear_rede,
    hosts_da_faixa,
    normalizar_faixa,
    testar_porta,
    testar_rtsp,
)
from rtsp.video import (
    abrir_stream,
    descobrir_stream,
    detectar_player,
    erro_se_morreu,
    validar_stream,
)

_log = obter_logger("cameras_tab")

# Workers da aba ficam num grupo próprio para que o `exclusive=True` do scan não
# cancele os workers de rede/dashboard do Varedura (que vivem no grupo default).
_GRUPO = "cameras"

_RADAR_FRAMES = ["◜ ", " ◝", " ◞", "◟ "]

# CSS específico da aba. Os seletores de TIPO genéricos (DataTable, Input) são
# escopados sob `#cameras` para não afetar o resto da TUI; classes/ids são únicos.
CAMERAS_CSS = """
#cameras .painel {
    background: $panel;
    border: round $primary;
    padding: 1 2;
    margin: 1 1 0 1;
    height: auto;
}
#cameras .painel-titulo { text-style: bold; color: $accent; margin-bottom: 1; }
#cameras .campo { height: auto; width: 1fr; margin-right: 2; }
#cameras .campo:last-of-type { margin-right: 0; }
#cameras .rotulo { color: $text-muted; text-style: bold; padding-left: 1; }
#cameras Input { margin-top: 0; }
#cameras .linha { height: auto; }
#cameras .acoes { height: auto; margin-top: 1; align-horizontal: left; }
#cameras .acoes Button { margin-right: 2; }
#cameras .dica { color: $text-muted; margin: 1 1 0 2; }
#cameras DataTable {
    height: 1fr;
    margin: 1 1 1 1;
    border: round $primary-darken-2;
}
#cameras DataTable > .datatable--header { text-style: bold; background: $primary-darken-2; }
#cameras DataTable > .datatable--cursor { background: $accent 40%; }
#rtsp-saida {
    background: $panel;
    border: round $primary-darken-2;
    margin: 1 1 1 1;
    padding: 1 2;
    height: auto;
    min-height: 5;
}
#cameras .aba-scroll { height: 1fr; }
#cameras .mapa {
    height: auto;
    border: round $primary-darken-2;
    padding: 0 1;
    margin: 0 0 1 0;
    color: $primary-darken-2;
}
#cameras .cards-rede { height: auto; }
#cameras .card-rede {
    width: 1fr;
    height: 3;
    margin: 0 0 1 0;
    content-align: left middle;
    border: tall $primary;
}
#cameras .card-row { height: 3; margin: 0 0 1 0; }
#cameras .card-row .card-regiao {
    width: 1fr;
    height: 3;
    margin: 0;
    content-align: left middle;
    border: tall $secondary;
}
#cameras .card-del { width: 5; min-width: 5; height: 3; margin: 0 0 0 1; border: tall $error; }
#cameras .oculto { display: none; }
#rede-tabela { height: 16; min-height: 6; }

/* Aba credenciais: 2 colunas responsivas (formulários | tabelas). */
#cred-layout { height: 1fr; }
#cred-forms { width: 40%; }
#cred-tables { width: 1fr; padding: 0 1; }
#cred-tabela, #cred-ips-tabela { height: 1fr; min-height: 3; }
/* Tela estreita: empilha em coluna única (classe alternada via on_resize). */
#cred-layout.cred-narrow { layout: vertical; }
#cred-layout.cred-narrow #cred-forms { width: 1fr; height: 45%; }
#cred-layout.cred-narrow #cred-tables { width: 1fr; height: 1fr; }
#cameras .scan-feedback {
    height: auto;
    background: $panel;
    border: round $accent;
    padding: 1 2;
    margin: 1 1 0 1;
}
#radar { color: $accent; text-style: bold; height: 1; }
#rede-progress { margin: 1 0; }
#rede-contador { color: $success; text-style: bold; }
"""


def _campo(rotulo: str, **input_kwargs) -> Vertical:
    """Um campo de formulário: rótulo em cima, input embaixo."""
    with Vertical(classes="campo") as wrap:
        yield Label(rotulo, classes="rotulo")
        yield Input(**input_kwargs)
    return wrap


# Código do diálogo nativo de "Abrir arquivo" (roda num subprocesso isolado para
# não conflitar com o loop/terminal do Textual). argv: título, rótulo .txt, todos.
_DIALOGO_CODE = (
    "import sys, tkinter, tkinter.filedialog as fd\n"
    "r = tkinter.Tk(); r.withdraw()\n"
    "try:\n"
    "    r.attributes('-topmost', True)\n"
    "except Exception:\n"
    "    pass\n"
    "p = fd.askopenfilename(title=sys.argv[1], "
    "filetypes=[(sys.argv[2], '*.txt'), (sys.argv[3], '*.*')])\n"
    "r.destroy()\n"
    "sys.stdout.write(p or '')\n"
)


def _escolher_arquivo_txt(titulo: str, rotulo_txt: str, rotulo_todos: str) -> tuple[str, bool]:
    """Abre o explorador de arquivos nativo e retorna (caminho, abriu_ok).

    caminho vazio = usuário cancelou. abriu_ok=False -> não foi possível abrir o
    diálogo (ex.: sem tkinter); o chamador cai no campo manual.
    """
    try:
        proc = subprocess.run(
            [sys.executable, "-c", _DIALOGO_CODE, titulo, rotulo_txt, rotulo_todos],
            capture_output=True,
            text=True,
            timeout=300,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        _log.warning("Falha ao abrir o explorador de arquivos: %s", exc)
        return "", False
    if proc.returncode != 0:
        _log.warning("Explorador retornou erro: %s", proc.stderr.strip())
        return "", False
    return proc.stdout.strip(), True


class CamerasMixin:
    """UI + workers da aba Câmeras, fundida no VareduraTextualApp."""

    # ------------------------------------------------------------------ #
    # Estado / ciclo de vida (chamados pelo app hospedeiro)              #
    # ------------------------------------------------------------------ #
    def _init_cameras_state(self) -> None:
        self._urls_rede: dict[str, str] = {}
        self._falhas_rede: dict[str, str] = {}
        self._players: list = []
        self._vault: list[Par] = []
        self._conhecidos: dict = {}
        self._redes: list = []
        self._regioes: list[Regiao] = []
        self._radar_timer: Timer | None = None
        self._radar_frame: int = 0
        self._cameras_encontradas: int = 0
        self._val_total: int = 0
        self._val_feita: int = 0
        self._itens_mapa: list[dict] = []
        self._ip_externo: str | None = None
        self._regiao_focada: int | None = None
        self._cameras_rendered: bool = False

    def _compose_cameras(self) -> ComposeResult:
        with TabbedContent(initial="tab-rede", id="cameras-subtabs"):
            # ---------- Aba principal: rede ----------
            with TabPane(t("rtsp.tab_rede"), id="tab-rede"):
                with VerticalScroll(classes="aba-scroll"):
                    with Container(classes="painel"):
                        yield Static(t("rtsp.rede_titulo"), classes="painel-titulo")
                        yield Vertical(id="cards-rede", classes="cards-rede")
                        with Collapsible(
                            title=t("rtsp.mapa_titulo"), collapsed=True, id="col-mapa"
                        ):
                            yield Static(id="mapa-mundi", classes="mapa")
                        with Collapsible(
                            title=t("rtsp.outras_redes"),
                            collapsed=True,
                            id="col-outras",
                            classes="oculto",
                        ):
                            yield Vertical(id="outras-redes")
                        with Horizontal(classes="acoes"):
                            yield Button(t("rtsp.btn_atualizar"), id="btn-rede-refresh")
                            yield Button(t("rtsp.btn_log"), id="btn-cam-log")
                        with Vertical(id="rede-manual", classes="oculto"):
                            yield from _campo(
                                t("rtsp.rede_manual"),
                                placeholder=t("rtsp.ph_rede_manual"),
                                id="rede-base",
                            )
                            yield Button(t("rtsp.btn_varrer"), variant="primary", id="btn-rede")

                    with Vertical(id="scan-feedback", classes="scan-feedback oculto"):
                        yield Static("", id="radar")
                        yield ProgressBar(id="rede-progress", total=254, show_eta=False)
                        yield Static(t("rtsp.contador_cam", n=0), id="rede-contador")

                    yield Label(t("rtsp.dica_abrir"), classes="dica")
                    yield DataTable(id="rede-tabela", cursor_type="row", zebra_stripes=True)

                    with Collapsible(title=t("rtsp.add_regiao"), collapsed=True):
                        with Horizontal(classes="linha"):
                            yield from _campo(
                                t("rtsp.campo_rotulo"), placeholder=t("rtsp.ph_rotulo"), id="regiao-rotulo"
                            )
                            yield from _campo(
                                t("rtsp.campo_endereco"), placeholder=t("rtsp.ph_endereco"), id="regiao-endereco"
                            )
                            yield from _campo(
                                t("rtsp.campo_porta"), placeholder=t("rtsp.ph_porta"), id="regiao-porta"
                            )
                        with Horizontal(classes="linha"):
                            with RadioSet(id="regiao-tipo"):
                                yield RadioButton(t("rtsp.tipo_rede"), value=True, id="tipo-rede")
                                yield RadioButton(t("rtsp.tipo_camera"), id="tipo-camera")
                        with Horizontal(classes="acoes"):
                            yield Button(t("rtsp.add_regiao"), variant="primary", id="btn-regiao-add")
                    with Collapsible(title=t("rtsp.opcoes_avancadas"), collapsed=True):
                        with Horizontal(classes="linha"):
                            yield from _campo(
                                t("rtsp.campo_caminho"), placeholder=t("rtsp.ph_auto"), id="rede-path"
                            )
                            yield from _campo(
                                t("rtsp.campo_marca"), placeholder=t("rtsp.ph_marca"), id="rede-marca"
                            )
                        with Horizontal(classes="linha"):
                            yield from _campo(
                                t("rtsp.campo_usuario"), placeholder=t("rtsp.ph_usuario"), id="rede-user"
                            )
                            yield from _campo(
                                t("rtsp.campo_senha"), placeholder=t("rtsp.ph_senha"), password=True, id="rede-pass"
                            )

            # ---------- Aba: RTSP único ----------
            with TabPane(t("rtsp.tab_rtsp"), id="tab-rtsp"):
                with VerticalScroll(classes="aba-scroll"):
                    with Container(classes="painel"):
                        yield Static(t("rtsp.rtsp_titulo"), classes="painel-titulo")
                        yield from _campo(t("rtsp.campo_url"), placeholder=t("rtsp.ph_url"), id="rtsp-url")
                        with Horizontal(classes="linha"):
                            yield from _campo(
                                t("rtsp.campo_usuario"), placeholder=t("rtsp.ph_usuario"), id="rtsp-user"
                            )
                            yield from _campo(
                                t("rtsp.campo_senha"), placeholder=t("rtsp.ph_senha"), password=True, id="rtsp-pass"
                            )
                        with Horizontal(classes="acoes"):
                            yield Button(t("rtsp.btn_testar"), variant="primary", id="btn-rtsp")
                            yield Button(t("rtsp.btn_abrir_video"), variant="success", id="btn-rtsp-abrir")
                    yield Static("", id="rtsp-saida")

            # ---------- Aba: portas ----------
            with TabPane(t("rtsp.tab_portas"), id="tab-portas"):
                with Container(classes="painel"):
                    yield Static(t("rtsp.portas_titulo"), classes="painel-titulo")
                    yield from _campo(t("rtsp.campo_host"), placeholder=t("rtsp.ph_host"), id="portas-host")
                    with Horizontal(classes="acoes"):
                        yield Button(t("rtsp.btn_portas"), variant="primary", id="btn-portas")
                yield DataTable(id="portas-tabela", zebra_stripes=True)

            # ---------- Aba: credenciais (2 colunas, responsivo) ----------
            with TabPane(t("rtsp.tab_cred"), id="tab-cred"):
                with Horizontal(id="cred-layout"):
                    # Coluna esquerda: formulários (rola se faltar altura).
                    with VerticalScroll(id="cred-forms"):
                        with Container(classes="painel"):
                            yield Static(t("rtsp.cred_titulo"), classes="painel-titulo")
                            with Horizontal(classes="linha"):
                                yield from _campo(
                                    t("rtsp.campo_usuario"), placeholder=t("rtsp.ph_usuario"), id="cred-user"
                                )
                                yield from _campo(
                                    t("rtsp.campo_senha"), placeholder=t("rtsp.ph_senha"), password=True, id="cred-pass"
                                )
                            with Horizontal(classes="acoes"):
                                yield Button(t("rtsp.btn_add"), variant="primary", id="btn-cred-add")
                                yield Button(t("rtsp.btn_remover_sel"), variant="error", id="btn-cred-del")
                        with Container(classes="painel"):
                            yield Static(t("rtsp.imp_titulo"), classes="painel-titulo")
                            with Horizontal(classes="linha"):
                                yield from _campo(
                                    t("rtsp.imp_users"), placeholder=t("rtsp.ph_imp"), id="imp-users"
                                )
                                yield from _campo(
                                    t("rtsp.imp_pass"), placeholder=t("rtsp.ph_imp"), id="imp-pass"
                                )
                            with Horizontal(classes="acoes"):
                                yield Button(t("rtsp.btn_browse_users"), id="btn-browse-users")
                                yield Button(t("rtsp.btn_browse_pass"), id="btn-browse-pass")
                            with Horizontal(classes="acoes"):
                                yield Button(t("rtsp.btn_import"), variant="primary", id="btn-cred-import")
                    # Coluna direita: tabelas que preenchem a altura disponível.
                    with Vertical(id="cred-tables"):
                        yield Static(t("rtsp.cred_vault_titulo"), classes="painel-titulo")
                        yield DataTable(id="cred-tabela", cursor_type="row", zebra_stripes=True)
                        yield Static(t("rtsp.ips_titulo"), classes="painel-titulo")
                        with Horizontal(classes="acoes"):
                            yield Button(t("rtsp.btn_esquecer_ip"), variant="warning", id="btn-ip-forget")
                        yield DataTable(id="cred-ips-tabela", cursor_type="row", zebra_stripes=True)

    def _cameras_on_mount(self) -> None:
        self.query_one("#portas-tabela", DataTable).add_columns(
            t("rtsp.col_porta"), t("rtsp.col_status")
        )
        self.query_one("#rede-tabela", DataTable).add_columns(
            t("rtsp.col_ip"),
            t("rtsp.col_video"),
            t("rtsp.col_credencial"),
            t("rtsp.col_caminho"),
            t("rtsp.col_resolucao"),
            t("rtsp.col_codec"),
        )
        self.query_one("#cred-tabela", DataTable).add_columns(
            t("rtsp.col_usuario"), t("rtsp.col_senha")
        )
        self.query_one("#cred-ips-tabela", DataTable).add_columns(
            t("rtsp.col_ip"),
            t("rtsp.col_usuario"),
            t("rtsp.col_caminho"),
            t("rtsp.col_resolucao"),
            t("rtsp.col_codec"),
        )
        self._vault = carregar_vault()
        self._conhecidos = carregar_conhecidos()
        self._refresh_cred_tabela()
        self._refresh_ips_tabela()

    def _maybe_render_cameras(self) -> None:
        """Detecta redes/regiões e geolocaliza ao abrir a aba pela 1ª vez."""
        if self._cameras_rendered:
            return
        self._cameras_rendered = True
        self.run_worker(self._render_cards(), group=_GRUPO)

    def _cameras_on_unmount(self) -> None:
        if self._radar_timer is not None:
            self._radar_timer.stop()
        for proc in self._players:
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    # Despacho de eventos (delegado pelo app hospedeiro)                 #
    # ------------------------------------------------------------------ #
    def _cameras_handle_button(self, bid: str) -> None:
        if bid == "btn-rede":
            base = self.query_one("#rede-base", Input).value.strip()
            if base:
                self._scan_faixa(base)
            else:
                self.notify(t("rtsp.nf_informe_prefixo"), severity="warning")
        elif bid == "btn-rede-refresh":
            self.run_worker(self._render_cards(), group=_GRUPO)
        elif bid == "btn-cam-log":
            self.action_cam_log()
        elif bid == "btn-regiao-add":
            self.run_worker(self._add_regiao(), group=_GRUPO)
        elif bid.startswith("del-regiao-"):
            self.run_worker(self._del_regiao(int(bid.rsplit("-", 1)[1])), group=_GRUPO)
        elif bid == "btn-portas":
            self._run_portas()
        elif bid == "btn-rtsp":
            self._run_rtsp()
        elif bid == "btn-rtsp-abrir":
            self._abrir_rtsp_unico()
        elif bid == "btn-cred-add":
            self._add_credencial()
        elif bid == "btn-cred-del":
            self._del_credencial()
        elif bid == "btn-cred-import":
            self._importar_credenciais()
        elif bid == "btn-browse-users":
            self._browse_arquivo("imp-users")
        elif bid == "btn-browse-pass":
            self._browse_arquivo("imp-pass")
        elif bid == "btn-ip-forget":
            self._esquecer_ip()
        elif bid == "card-externa":
            if self._ip_externo:
                self._scan_externa(self._ip_externo)
            else:
                self.notify(t("rtsp.nf_ip_publico_pendente"), severity="warning")
        elif bid.startswith("card-rede-"):
            self._scan_faixa(self._cam_base_de_card_id(bid))
        elif bid.startswith("card-regiao-"):
            self._abrir_regiao(int(bid.rsplit("-", 1)[1]))

    def _cameras_on_row_selected(self, event) -> None:
        if event.data_table.id == "rede-tabela":
            self._abrir_por_chave(event.row_key.value)

    def _cameras_on_focus(self, event) -> None:
        wid = getattr(event, "widget", None)
        if wid is not None and wid.id and wid.id.startswith("card-regiao-"):
            self._regiao_focada = int(wid.id.rsplit("-", 1)[1])

    def _cameras_on_resize(self, width: int) -> None:
        """Reflow responsivo da aba credenciais: 2 colunas (largo) ou
        empilhado em coluna única (estreito)."""
        try:
            self.query_one("#cred-layout").set_class(width < 90, "cred-narrow")
        except Exception:
            pass

    def _cameras_on_worker_state(self, event) -> None:
        from textual.worker import WorkerState

        if getattr(event.worker, "group", None) != _GRUPO:
            return
        if event.state is WorkerState.ERROR:
            _log.exception("Worker '%s' falhou: %s", event.worker.name, event.worker.error)
            self.notify(t("rtsp.nf_erro_interno", erro=event.worker.error), severity="error")
            self._parar_radar()
            try:
                self.query_one("#scan-feedback", Vertical).add_class("oculto")
            except Exception:
                pass

    # ---- Actions (bindings delete/l, escopadas à aba Câmeras) ----
    async def action_cam_del_regiao(self) -> None:
        if self.query_one("#main-tabs", TabbedContent).active != "cameras":
            return
        if self._regiao_focada is None:
            self.notify(t("rtsp.nf_regiao_sel"), severity="warning")
            return
        await self._del_regiao(self._regiao_focada)
        self._regiao_focada = None

    def action_cam_log(self) -> None:
        import os

        self.notify(t("rtsp.nf_log", caminho=str(ARQUIVO_LOG)))
        try:
            os.startfile(ARQUIVO_LOG)  # type: ignore[attr-defined]  # Windows
        except (AttributeError, OSError) as exc:
            _log.warning("Não consegui abrir o log no sistema: %s", exc)

    # ------------------------------------------------------------------ #
    # Helpers                                                            #
    # ------------------------------------------------------------------ #
    def _monta_url(self, host: str, path: str, user, pwd, porta: int = 554) -> str:
        cred = ""
        if user:
            cred = quote(user, safe="")
            if pwd:
                cred += ":" + quote(pwd, safe="")
            cred += "@"
        caminho = path if path.startswith("/") or not path else f"/{path}"
        return f"rtsp://{cred}{host}:{porta}{caminho}"

    def _com_credenciais(self, url: str, user, pwd) -> str:
        if not user:
            return url
        p = urlsplit(url)
        userinfo = quote(user, safe="")
        if pwd:
            userinfo += ":" + quote(pwd, safe="")
        host = p.hostname or ""
        netloc = f"{userinfo}@{host}" + (f":{p.port}" if p.port else "")
        return urlunsplit((p.scheme, netloc, p.path, p.query, p.fragment))

    def _so_path(self, url: str) -> str:
        p = urlsplit(url)
        return (p.path + (f"?{p.query}" if p.query else "")) or "/"

    @staticmethod
    def _rotulo_par(par) -> str:
        return par.usuario or t("rtsp.sem_auth")

    def _lancar_player(self, url: str, ip: str | None = None) -> None:
        _log.info("Usuário pediu para abrir: %s", ip or url)
        player = detectar_player()
        proc = abrir_stream(url, titulo=ip)
        if proc is None:
            self.notify(t("rtsp.nf_nenhum_player"), severity="error")
            return
        self._players.append(proc)
        nome = player[0] if player else "player"
        self.notify(t("rtsp.nf_abrindo", alvo=ip or t("rtsp.stream"), player=nome))
        self.run_worker(lambda: self._vigia_player(proc, ip), thread=True, group=_GRUPO)

    def _vigia_player(self, proc, ip) -> None:
        erro = erro_se_morreu(proc)
        if erro:
            self.call_from_thread(
                self.notify,
                t("rtsp.nf_player_falhou", alvo=ip or t("rtsp.stream"), erro=erro),
                severity="error",
            )

    # ---- Aba Rede: cartões de região ----
    def _cam_id_rede(self, base: str) -> str:
        return "card-rede-" + base.replace(".", "-")

    def _cam_base_de_card_id(self, bid: str) -> str:
        return bid[len("card-rede-"):].replace("-", ".")

    async def _render_cards(self) -> None:
        self._redes = detectar_redes()
        self._regioes = carregar_regioes()

        principais = [r for r in self._redes if r.primaria]
        outras = [r for r in self._redes if not r.primaria]

        itens: list[dict] = []
        if self._redes:
            itens.append(
                {
                    "tipo": "externa",
                    "grupo": "main",
                    "icone": "🌍",
                    "card_id": "card-externa",
                    "rotulo": t("rtsp.card_externa"),
                    "host": "",
                    "geo": None,
                }
            )
        for i, reg in enumerate(self._regioes):
            icone = "🎥" if reg.tipo == TIPO_CAMERA else "🌐"
            if reg.tipo == TIPO_CAMERA:
                geo_host = reg.endereco
            elif "/" in reg.endereco:
                geo_host = hosts_da_faixa(reg.endereco)[0]
            elif reg.endereco.count(".") == 2:
                geo_host = f"{reg.endereco}.1"
            else:
                geo_host = reg.endereco
            itens.append(
                {
                    "tipo": "regiao",
                    "grupo": "main",
                    "icone": icone,
                    "card_id": f"card-regiao-{i}",
                    "rotulo": reg.descricao(),
                    "host": geo_host,
                    "geo": None,
                }
            )
        for r in principais:
            itens.append(self._item_rede(r))
        for r in outras:
            item = self._item_rede(r)
            item["grupo"] = "outras"
            itens.append(item)

        contador = 0
        for it in itens:
            if it["tipo"] in ("externa", "regiao"):
                contador += 1
                it["numero"] = contador
            else:
                it["numero"] = None
        self._itens_mapa = itens

        def _widget(it: dict):
            numero = it["numero"]
            if numero is not None:
                cor = cor_para(numero - 1)
                prefixo = f"[b {cor}]{numero}[/]  "
            else:
                prefixo = "[dim]•[/]  "
            rotulo = f"{prefixo}{it['icone']} {it['rotulo']}"
            if it["tipo"] != "regiao":
                return Button(rotulo, id=it["card_id"], classes="card-rede")
            idx = int(it["card_id"].rsplit("-", 1)[1])
            return Horizontal(
                Button(rotulo, id=it["card_id"], classes="card-regiao"),
                Button("✕", id=f"del-regiao-{idx}", classes="card-del"),
                classes="card-row",
            )

        cont = self.query_one("#cards-rede", Vertical)
        cont_outras = self.query_one("#outras-redes", Vertical)
        await cont.remove_children()
        await cont_outras.remove_children()

        principais_w, outras_w = [], []
        for it in itens:
            (outras_w if it["grupo"] == "outras" else principais_w).append(_widget(it))
        if principais_w:
            await cont.mount_all(principais_w)
        if outras_w:
            await cont_outras.mount_all(outras_w)

        col_outras = self.query_one("#col-outras", Collapsible)
        if outras_w:
            col_outras.remove_class("oculto")
            col_outras.title = t("rtsp.outras_redes_count", n=len(outras_w))
        else:
            col_outras.add_class("oculto")

        manual = self.query_one("#rede-manual", Vertical)
        if not itens:
            manual.remove_class("oculto")
            self.query_one("#mapa-mundi", Static).update(render_mapa([]))
        else:
            manual.add_class("oculto")
            self.query_one("#mapa-mundi", Static).update(t("rtsp.localizando"))
            self.run_worker(self._worker_geo, thread=True, group=_GRUPO)

    def _item_rede(self, r) -> dict:
        rotulo = t(
            "rtsp.rede_local",
            base=r.base,
            octeto=r.ultimo_octeto,
            star=" ★" if r.primaria else "",
        )
        return {
            "tipo": "rede",
            "grupo": "main",
            "icone": "📍",
            "card_id": self._cam_id_rede(r.base),
            "rotulo": rotulo,
            "host": "",
            "geo": None,
        }

    def _worker_geo(self) -> None:
        pinos = []
        for it in self._itens_mapa:
            numero = it.get("numero")
            if numero is None:
                continue
            g = geolocalizar(it["host"])
            it["geo"] = g
            if it["tipo"] == "externa" and g is not None:
                self._ip_externo = g.query
            if g is not None:
                pinos.append(Pino(g.lat, g.lon, numero, cor_para(numero - 1)))
        self.call_from_thread(self._aplicar_geo, pinos)

    def _aplicar_geo(self, pinos: list) -> None:
        self.query_one("#mapa-mundi", Static).update(render_mapa(pinos))
        for it in self._itens_mapa:
            numero = it.get("numero")
            g = it["geo"]
            if numero is None or g is None:
                continue
            cor = cor_para(numero - 1)
            rotulo = f"[b {cor}]{numero}[/]  {it['icone']} {it['rotulo']} · [i]{g.local_txt}[/]"
            try:
                self.query_one(f"#{it['card_id']}", Button).label = rotulo
            except Exception:
                pass

    async def _add_regiao(self) -> None:
        rotulo = self.query_one("#regiao-rotulo", Input).value.strip()
        endereco = self.query_one("#regiao-endereco", Input).value.strip()
        porta_txt = self.query_one("#regiao-porta", Input).value.strip()
        if not rotulo or not endereco:
            self.notify(t("rtsp.nf_informe_rotulo_endereco"), severity="warning")
            return
        try:
            porta = int(porta_txt) if porta_txt else 554
        except ValueError:
            self.notify(t("rtsp.nf_porta_invalida"), severity="warning")
            return
        tipo = TIPO_CAMERA if self.query_one("#tipo-camera", RadioButton).value else TIPO_REDE
        if tipo == TIPO_REDE:
            try:
                endereco = normalizar_faixa(endereco)
            except ValueError as exc:
                self.notify(t("rtsp.nf_faixa_invalida", erro=exc), severity="warning")
                return
        if not adicionar_regiao(self._regioes, rotulo, tipo, endereco, porta):
            self.notify(t("rtsp.nf_regiao_existe"), severity="warning")
            return
        salvar_regioes(self._regioes)
        for cid in ("#regiao-rotulo", "#regiao-endereco", "#regiao-porta"):
            self.query_one(cid, Input).value = ""
        await self._render_cards()
        self.notify(t("rtsp.nf_regiao_add", rotulo=rotulo))

    async def _del_regiao(self, indice: int) -> None:
        if not (0 <= indice < len(self._regioes)):
            return
        rotulo = self._regioes[indice].rotulo
        remover_regiao(self._regioes, indice)
        salvar_regioes(self._regioes)
        await self._render_cards()
        self.notify(t("rtsp.nf_regiao_removida", rotulo=rotulo))

    def _abrir_regiao(self, indice: int) -> None:
        if not (0 <= indice < len(self._regioes)):
            return
        reg = self._regioes[indice]
        if reg.tipo == TIPO_CAMERA:
            self._conectar_camera(reg.endereco, reg.porta, reg.caminho)
        else:
            self._scan_faixa(reg.endereco)

    # ---- Aba Rede: varre faixa + valida ----
    def _ler_avancado(self) -> tuple:
        path = self.query_one("#rede-path", Input).value.strip()
        marca = self.query_one("#rede-marca", Input).value.strip() or None
        user = self.query_one("#rede-user", Input).value.strip() or None
        pwd = self.query_one("#rede-pass", Input).value.strip() or None
        return path, marca, user, pwd

    def _preparar_scan(self, total: int) -> None:
        self.query_one("#rede-tabela", DataTable).clear()
        self._urls_rede.clear()
        self._falhas_rede.clear()
        self._cameras_encontradas = 0
        self._val_total = 0
        self._val_feita = 0
        self._atualizar_contador()
        pb = self.query_one("#rede-progress", ProgressBar)
        pb.update(total=total, progress=0)
        self.query_one("#scan-feedback", Vertical).remove_class("oculto")
        self._iniciar_radar()

    def _scan_faixa(self, base: str) -> None:
        try:
            total = len(hosts_da_faixa(base))
        except ValueError as exc:
            self.notify(t("rtsp.nf_faixa_invalida", erro=exc), severity="warning")
            return
        path, marca, user, pwd = self._ler_avancado()
        self._preparar_scan(total)
        alvo = base if "/" in base else f"{base}.x"
        self.notify(t("rtsp.nf_varrendo", alvo=alvo, total=total))
        self.run_worker(
            lambda: self._worker_rede(base, path, marca, user, pwd),
            thread=True,
            exclusive=True,
            group=_GRUPO,
        )

    def _conectar_camera(self, host: str, porta: int, caminho: str) -> None:
        path, marca, user, pwd = self._ler_avancado()
        caminho_final = caminho or path
        self._preparar_scan(1)
        self.notify(t("rtsp.nf_conectando", host=host, porta=porta))
        self.run_worker(
            lambda: self._worker_camera(host, porta, caminho_final, marca, user, pwd),
            thread=True,
            exclusive=True,
            group=_GRUPO,
        )

    def _scan_externa(self, ip: str) -> None:
        path, marca, user, pwd = self._ler_avancado()
        self._preparar_scan(1)
        self.notify(t("rtsp.nf_procurando_publico", ip=ip))
        self.run_worker(
            lambda: self._worker_externa(ip, path, marca, user, pwd),
            thread=True,
            exclusive=True,
            group=_GRUPO,
        )

    def _worker_externa(self, ip, path, marca, user, pwd) -> None:
        portas = escanear_portas_camera(ip)
        abertas = [p for p, ok in portas.items() if ok]
        self.call_from_thread(self._atualizar_progresso, 1, 1)
        if not abertas:
            self.call_from_thread(
                self.notify, t("rtsp.nf_sem_porta_publico", ip=ip), severity="warning"
            )
            self.call_from_thread(self._finalizar_scan)
            return
        self.call_from_thread(
            self.notify, t("rtsp.nf_portas_abertas_validando", ip=ip, portas=abertas)
        )
        candidatos = [path] if path else caminhos_conhecidos(marca)
        self.call_from_thread(self._iniciar_fase_validacao, len(abertas))
        for idx, porta in enumerate(abertas, 1):
            def monta(h, c, u, p, _pt=porta):
                return self._monta_url(h, c, u, p, porta=_pt)
            if user:
                info = descobrir_stream(
                    lambda c, _pt=porta: self._monta_url(ip, c, user, pwd, porta=_pt),
                    candidatos,
                    ao_tentar=lambda c, _pt=porta: self.call_from_thread(
                        self._status_tentativa_cred, f"{ip}:{_pt}", c, user
                    ),
                )
                par_usado = Par(user, pwd or "") if info and info.funciona else None
            else:
                resultado = resolver_ip(
                    ip,
                    candidatos,
                    self._vault,
                    self._conhecidos,
                    monta_url=monta,
                    ao_tentar=lambda _h, c, rot, _pt=porta: self.call_from_thread(
                        self._status_tentativa_cred, f"{ip}:{_pt}", c, rot
                    ),
                )
                info, par_usado = (resultado[0], resultado[1]) if resultado else (None, None)
            chave = f"{ip}:{porta}"
            if info and info.funciona:
                self._urls_rede[chave] = info.url
                cred_label = self._rotulo_par(par_usado) if par_usado else "—"
                self.call_from_thread(
                    self.query_one("#rede-tabela", DataTable).add_row,
                    chave,
                    t("rtsp.video_ok"),
                    cred_label,
                    self._so_path(info.url),
                    info.resolucao,
                    info.codec or "—",
                    key=chave,
                )
            else:
                # Porta aberta mas sem stream validado -> salva mesmo assim.
                self._urls_rede[chave] = self._monta_url(ip, candidatos[0], user, pwd, porta=porta)
                self._falhas_rede[chave] = t("rtsp.falha_sem_video")
                self.call_from_thread(
                    self.query_one("#rede-tabela", DataTable).add_row,
                    chave,
                    t("rtsp.video_aberto"),
                    "—",
                    "—",
                    "—",
                    "—",
                    key=chave,
                )
            self.call_from_thread(self._incrementar_cameras)
            self.call_from_thread(self._passo_validacao, idx)
        self.call_from_thread(self._refresh_ips_tabela)
        self.call_from_thread(self._finalizar_scan)

    def _worker_rede(self, base: str, path: str, marca, user, pwd) -> None:
        def _prog(testados, total, ip_aberto):
            self.call_from_thread(self._atualizar_progresso, testados, total)

        ips = escanear_rede(base, ao_progresso=_prog)
        if not ips:
            self.call_from_thread(self.notify, t("rtsp.nf_nenhuma_porta_rtsp"))
            self.call_from_thread(self._finalizar_scan)
            return
        candidatos = [path] if path else caminhos_conhecidos(marca)
        modo = t("rtsp.modo_manual") if user else t("rtsp.modo_cofre", n=len(self._vault))
        self.call_from_thread(
            self.notify,
            t("rtsp.nf_hosts_testando", hosts=len(ips), caminhos=len(candidatos), modo=modo),
        )
        self.call_from_thread(self._iniciar_fase_validacao, len(ips))
        for idx, ip in enumerate(ips, 1):
            if user:
                info = descobrir_stream(
                    lambda c, _ip=ip: self._monta_url(_ip, c, user, pwd),
                    candidatos,
                    ao_tentar=lambda c, _ip=ip: self.call_from_thread(
                        self._status_tentativa_cred, _ip, c, user
                    ),
                )
                par_usado = Par(user, pwd or "") if info and info.funciona else None
            else:
                resultado = resolver_ip(
                    ip,
                    candidatos,
                    self._vault,
                    self._conhecidos,
                    monta_url=self._monta_url,
                    ao_tentar=lambda _ip, c, rot: self.call_from_thread(
                        self._status_tentativa_cred, _ip, c, rot
                    ),
                )
                info, par_usado = (resultado[0], resultado[1]) if resultado else (None, None)

            if info and info.funciona:
                self._urls_rede[ip] = info.url
                cred_label = self._rotulo_par(par_usado) if par_usado else "—"
                self.call_from_thread(
                    self.query_one("#rede-tabela", DataTable).add_row,
                    ip,
                    t("rtsp.video_ok"),
                    cred_label,
                    self._so_path(info.url),
                    info.resolucao,
                    info.codec or "—",
                    key=ip,
                )
                self.call_from_thread(self._incrementar_cameras)
            else:
                # Porta 554 aberta mas sem credencial válida -> salva mesmo assim.
                self._urls_rede[ip] = self._monta_url(ip, candidatos[0], user, pwd)
                self._falhas_rede[ip] = (
                    t("rtsp.falha_nenhuma_cred") if not user else t("rtsp.falha_cred_informada")
                )
                self.call_from_thread(
                    self.query_one("#rede-tabela", DataTable).add_row,
                    ip,
                    t("rtsp.video_aberto"),
                    "—",
                    "—",
                    "—",
                    "—",
                    key=ip,
                )
                self.call_from_thread(self._incrementar_cameras)
            self.call_from_thread(self._passo_validacao, idx)
        self.call_from_thread(self._refresh_ips_tabela)
        self.call_from_thread(self._finalizar_scan)

    def _worker_camera(self, host, porta, caminho, marca, user, pwd) -> None:
        self.call_from_thread(self._atualizar_progresso, 0, 1)
        if not testar_porta(host, porta, timeout=4.0):
            self.call_from_thread(
                self.notify, t("rtsp.nf_host_sem_resposta", host=host, porta=porta), severity="error"
            )
            self.call_from_thread(self._finalizar_scan)
            return
        candidatos = [caminho] if caminho else caminhos_conhecidos(marca)

        def monta(h, c, u, p):
            return self._monta_url(h, c, u, p, porta=porta)

        if user:
            info = descobrir_stream(
                lambda c: monta(host, c, user, pwd),
                candidatos,
                ao_tentar=lambda c: self.call_from_thread(
                    self._status_tentativa_cred, host, c, user
                ),
            )
            par_usado = Par(user, pwd or "") if info and info.funciona else None
        else:
            resultado = resolver_ip(
                host,
                candidatos,
                self._vault,
                self._conhecidos,
                monta_url=monta,
                ao_tentar=lambda _h, c, rot: self.call_from_thread(
                    self._status_tentativa_cred, _h, c, rot
                ),
            )
            info, par_usado = (resultado[0], resultado[1]) if resultado else (None, None)

        self.call_from_thread(self._atualizar_progresso, 1, 1)
        if info and info.funciona:
            self._urls_rede[host] = info.url
            cred_label = self._rotulo_par(par_usado) if par_usado else "—"
            self.call_from_thread(
                self.query_one("#rede-tabela", DataTable).add_row,
                host,
                t("rtsp.video_ok"),
                cred_label,
                self._so_path(info.url),
                info.resolucao,
                info.codec or "—",
                key=host,
            )
            self.call_from_thread(self._incrementar_cameras)
        else:
            # Porta aberta (testar_porta passou) mas sem stream -> salva mesmo assim.
            self._urls_rede[host] = self._monta_url(host, candidatos[0], user, pwd, porta=porta)
            self._falhas_rede[host] = t("rtsp.falha_sem_video")
            self.call_from_thread(self._incrementar_cameras)
            self.call_from_thread(
                self.query_one("#rede-tabela", DataTable).add_row,
                host,
                t("rtsp.video_aberto"),
                "—",
                "—",
                "—",
                "—",
                key=host,
            )
        self.call_from_thread(self._refresh_ips_tabela)
        self.call_from_thread(self._finalizar_scan)

    def _status_tentativa_cred(self, ip: str, caminho: str, rotulo: str) -> None:
        self.sub_title = t("rtsp.testando_cred", ip=ip, caminho=caminho, rotulo=rotulo)

    # ---- Gamificação: radar + progresso + contador ----
    def _atualizar_progresso(self, testados: int, total: int) -> None:
        self.query_one("#rede-progress", ProgressBar).update(total=total, progress=testados)

    def _incrementar_cameras(self) -> None:
        self._cameras_encontradas += 1
        self._atualizar_contador()

    def _atualizar_contador(self) -> None:
        cam = t("rtsp.contador_cam", n=self._cameras_encontradas)
        if self._val_total:
            texto = t("rtsp.contador_val", feita=self._val_feita, total=self._val_total, cam=cam)
        else:
            texto = cam
        self.query_one("#rede-contador", Static).update(texto)

    def _iniciar_fase_validacao(self, total: int) -> None:
        self._val_total = total
        self._val_feita = 0
        self.query_one("#rede-progress", ProgressBar).update(total=total, progress=0)
        self._atualizar_contador()

    def _passo_validacao(self, feitos: int) -> None:
        self._val_feita = feitos
        self.query_one("#rede-progress", ProgressBar).update(progress=feitos)
        self._atualizar_contador()

    def _iniciar_radar(self) -> None:
        self._radar_frame = 0
        if self._radar_timer is None:
            self._radar_timer = self.set_interval(0.12, self._tick_radar)
        else:
            self._radar_timer.resume()

    def _tick_radar(self) -> None:
        frame = _RADAR_FRAMES[self._radar_frame % len(_RADAR_FRAMES)]
        self._radar_frame += 1
        acao = t("rtsp.acao_validando") if self._val_total else t("rtsp.acao_varrendo")
        self.query_one("#radar", Static).update(f"[b]{frame}[/] {acao}…")

    def _parar_radar(self) -> None:
        if self._radar_timer is not None:
            self._radar_timer.pause()
        try:
            self.query_one("#radar", Static).update("")
        except Exception:
            pass

    def _finalizar_scan(self) -> None:
        self._parar_radar()
        pb = self.query_one("#rede-progress", ProgressBar)
        pb.update(progress=pb.total or 0)
        self.query_one("#scan-feedback", Vertical).add_class("oculto")
        self.sub_title = t("menu.subtitle")
        self.notify(t("rtsp.nf_varredura_concluida", n=self._cameras_encontradas))

    # ---- Aba Credenciais ----
    def _refresh_cred_tabela(self) -> None:
        tabela = self.query_one("#cred-tabela", DataTable)
        tabela.clear()
        for i, par in enumerate(self._vault):
            senha = ("•" * len(par.senha)) if par.senha else t("rtsp.senha_vazia")
            tabela.add_row(par.usuario or t("rtsp.sem_auth"), senha, key=str(i))

    def _refresh_ips_tabela(self) -> None:
        tabela = self.query_one("#cred-ips-tabela", DataTable)
        tabela.clear()
        for ip, cred in self._conhecidos.items():
            tabela.add_row(
                ip,
                cred.usuario or t("rtsp.sem_auth"),
                cred.caminho,
                cred.resolucao,
                cred.codec or "—",
                key=ip,
            )

    def _add_credencial(self) -> None:
        user = self.query_one("#cred-user", Input).value.strip()
        pwd = self.query_one("#cred-pass", Input).value
        if not user and not pwd:
            self.notify(t("rtsp.nf_informe_user_senha"), severity="warning")
            return
        if not adicionar_par(self._vault, user, pwd):
            self.notify(t("rtsp.nf_par_existe"), severity="warning")
            return
        salvar_vault(self._vault)
        self.query_one("#cred-user", Input).value = ""
        self.query_one("#cred-pass", Input).value = ""
        self._refresh_cred_tabela()
        self.notify(t("rtsp.nf_cred_add", rotulo=user or t("rtsp.sem_auth")))

    def _importar_credenciais(self) -> None:
        """Importa .txt de usuários e/ou senhas e combina (produto cartesiano)."""
        upath = self.query_one("#imp-users", Input).value.strip()
        ppath = self.query_one("#imp-pass", Input).value.strip()
        usuarios = carregar_lista(upath) if upath else []
        senhas = carregar_lista(ppath) if ppath else []
        if not usuarios and not senhas:
            self.notify(t("rtsp.nf_import_vazio"), severity="warning")
            return
        pares = combinar_credenciais(usuarios, senhas)
        novos = sum(1 for par in pares if adicionar_par(self._vault, par.usuario, par.senha))
        salvar_vault(self._vault)
        self._refresh_cred_tabela()
        self.notify(t("rtsp.nf_import_ok", novos=novos, total=len(pares)))

    def _browse_arquivo(self, input_id: str) -> None:
        """Abre o explorador de arquivos (em thread) e preenche o campo escolhido."""
        self.run_worker(lambda: self._worker_browse(input_id), thread=True, group=_GRUPO)

    def _worker_browse(self, input_id: str) -> None:
        caminho, abriu = _escolher_arquivo_txt(
            t("rtsp.dlg_titulo"), t("rtsp.dlg_txt"), t("rtsp.dlg_todos")
        )
        if not abriu:
            self.call_from_thread(
                self.notify, t("rtsp.nf_explorador_falhou"), severity="warning"
            )
            return
        if caminho:
            self.call_from_thread(self._set_browse_input, input_id, caminho)

    def _set_browse_input(self, input_id: str, valor: str) -> None:
        self.query_one(f"#{input_id}", Input).value = valor

    def _del_credencial(self) -> None:
        tabela = self.query_one("#cred-tabela", DataTable)
        if not tabela.row_count:
            self.notify(t("rtsp.nf_nenhum_par"), severity="warning")
            return
        chave = tabela.coordinate_to_cell_key(Coordinate(tabela.cursor_row, 0)).row_key.value
        remover_par(self._vault, int(chave))
        salvar_vault(self._vault)
        self._refresh_cred_tabela()
        self.notify(t("rtsp.nf_cred_removida"))

    def _esquecer_ip(self) -> None:
        tabela = self.query_one("#cred-ips-tabela", DataTable)
        if not tabela.row_count:
            self.notify(t("rtsp.nf_nenhum_ip"), severity="warning")
            return
        ip = tabela.coordinate_to_cell_key(Coordinate(tabela.cursor_row, 0)).row_key.value
        esquecer_ip(self._conhecidos, ip)
        self._refresh_ips_tabela()
        self.notify(t("rtsp.nf_ip_esquecido", ip=ip))

    def _abrir_por_chave(self, ip: str | None) -> None:
        url = self._urls_rede.get(ip or "")
        if not url:
            return
        motivo = self._falhas_rede.get(ip or "")
        if motivo:
            self.notify(t("rtsp.nf_camera_nao_validou", ip=ip, motivo=motivo), severity="warning")
        self._lancar_player(url, ip)

    # ---- Aba RTSP único ----
    def _run_rtsp(self) -> None:
        url = self.query_one("#rtsp-url", Input).value.strip()
        if not url:
            self.notify(t("rtsp.nf_informe_url"), severity="warning")
            return
        user = self.query_one("#rtsp-user", Input).value.strip() or None
        pwd = self.query_one("#rtsp-pass", Input).value.strip() or None
        self.query_one("#rtsp-saida", Static).update(t("rtsp.testando_curto"))
        self.run_worker(
            lambda: self._worker_rtsp(url, user, pwd), thread=True, exclusive=True, group=_GRUPO
        )

    def _worker_rtsp(self, url: str, user, pwd) -> None:
        r = testar_rtsp(url, user, pwd)
        url_auth = self._com_credenciais(url, user, pwd)
        info = validar_stream(url_auth) if r.acessivel else None
        linhas = []
        if r.acessivel:
            linhas.append(t("rtsp.rtsp_responde"))
        else:
            linhas.append(t("rtsp.rtsp_nao_responde"))
        linhas.append(t("rtsp.rtsp_status", code=r.status_code, msg=r.mensagem))
        if info:
            if info.funciona:
                linhas.append(t("rtsp.rtsp_entrega_video", res=info.resolucao, codec=info.codec))
            else:
                linhas.append(t("rtsp.rtsp_sem_video", msg=info.mensagem))
        self.call_from_thread(self.query_one("#rtsp-saida", Static).update, "\n".join(linhas))

    def _abrir_rtsp_unico(self) -> None:
        url = self.query_one("#rtsp-url", Input).value.strip()
        if not url:
            self.notify(t("rtsp.nf_informe_url"), severity="warning")
            return
        user = self.query_one("#rtsp-user", Input).value.strip() or None
        pwd = self.query_one("#rtsp-pass", Input).value.strip() or None
        self._lancar_player(self._com_credenciais(url, user, pwd))

    # ---- Aba Portas ----
    def _run_portas(self) -> None:
        host = self.query_one("#portas-host", Input).value.strip()
        if not host:
            self.notify(t("rtsp.nf_informe_host"), severity="warning")
            return
        self.query_one("#portas-tabela", DataTable).clear()
        self.run_worker(
            lambda: self._worker_portas(host), thread=True, exclusive=True, group=_GRUPO
        )

    def _worker_portas(self, host: str) -> None:
        for porta, aberta in escanear_portas_camera(host).items():
            status = t("rtsp.porta_aberta") if aberta else t("rtsp.porta_fechada")
            self.call_from_thread(
                self.query_one("#portas-tabela", DataTable).add_row, str(porta), status
            )
