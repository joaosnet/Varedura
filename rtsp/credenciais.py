"""Cofre de credenciais + mapa de IPs já resolvidos (auto-login).

Dois arquivos JSON texto puro, na pasta do projeto (gitignored):
- credenciais.json  -> lista de pares usuário/senha gerenciada no TUI
- ips_conhecidos.json -> ip -> par/caminho/url que funcionou (consultado primeiro)
"""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from rtsp import DATA_DIR as _DIR
from rtsp.log import obter_logger
from rtsp.video import (
    ERRO_AUTH,
    ERRO_BLOQUEIO,
    ERRO_FERRAMENTA,
    ERRO_REDE,
    InfoStream,
    descobrir_stream,
    validar_stream,
)

_log = obter_logger("credenciais")

ARQUIVO_VAULT = _DIR / "credenciais.json"
ARQUIVO_CONHECIDOS = _DIR / "ips_conhecidos.json"
DEFAULT_MAX_FALHAS_AUTH = 4
DEFAULT_INTERVALO_AUTH = 0.5


@dataclass
class Par:
    """Um par usuário/senha do cofre."""

    usuario: str
    senha: str

    def chave(self) -> tuple[str, str]:
        return (self.usuario, self.senha)

    def rotulo(self) -> str:
        return self.usuario or "(sem auth)"


@dataclass
class CredencialIP:
    """Credencial que funcionou para um IP específico."""

    usuario: str
    senha: str
    caminho: str
    url: str
    codec: str | None = None
    resolucao: str = "—"
    atualizado_em: str = ""


# --------------------------------------------------------------------------
# Escrita atômica
# --------------------------------------------------------------------------

def _salvar_json(caminho: Path, dados: dict) -> None:
    """Grava JSON de forma atômica (tmp + os.replace)."""
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, caminho)


# --------------------------------------------------------------------------
# Cofre (vault)
# --------------------------------------------------------------------------

def carregar_vault() -> list[Par]:
    """Lê credenciais.json. Ausente/corrompido -> lista vazia (loga warning)."""
    if not ARQUIVO_VAULT.exists():
        return []
    try:
        dados = json.loads(ARQUIVO_VAULT.read_text(encoding="utf-8"))
        pares = [Par(p["usuario"], p.get("senha", "")) for p in dados.get("pares", [])]
        _log.info("Vault carregado: %d par(es)", len(pares))
        return pares
    except (json.JSONDecodeError, OSError, KeyError, TypeError) as exc:
        _log.warning("Falha ao ler vault (%s): %s", ARQUIVO_VAULT, exc)
        return []


def salvar_vault(pares: list[Par]) -> None:
    """Escreve credenciais.json (version=1)."""
    _salvar_json(ARQUIVO_VAULT, {"version": 1, "pares": [asdict(p) for p in pares]})
    _log.info("Vault salvo: %d par(es)", len(pares))


def adicionar_par(pares: list[Par], usuario: str, senha: str) -> bool:
    """Acrescenta se (usuario, senha) ainda não existe. False se duplicado."""
    if any(p.chave() == (usuario, senha) for p in pares):
        return False
    pares.append(Par(usuario, senha))
    return True


def remover_par(pares: list[Par], indice: int) -> None:
    if 0 <= indice < len(pares):
        pares.pop(indice)


def carregar_lista(caminho) -> list[str]:
    """Lê um arquivo texto com uma entrada por linha.

    Ignora linhas em branco e comentários (iniciados por '#'). Remove duplicatas
    preservando a ordem. Arquivo ausente/ilegível -> lista vazia.
    """
    p = Path(caminho)
    if not p.exists():
        return []
    try:
        bruto = p.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        _log.warning("Falha ao ler lista (%s): %s", p, exc)
        return []
    entradas = [s for linha in bruto.splitlines() if (s := linha.strip()) and not s.startswith("#")]
    return list(dict.fromkeys(entradas))


def combinar_credenciais(usuarios: list[str], senhas: list[str]) -> list[Par]:
    """Produto cartesiano usuários×senhas -> pares do cofre.

    Se só uma lista vier preenchida: usuários viram pares sem senha e senhas
    viram pares sem usuário. Ambas vazias -> [].
    """
    if usuarios and senhas:
        return [Par(u, s) for u in usuarios for s in senhas]
    if usuarios:
        return [Par(u, "") for u in usuarios]
    if senhas:
        return [Par("", s) for s in senhas]
    return []


# --------------------------------------------------------------------------
# Mapa de IPs conhecidos
# --------------------------------------------------------------------------

def carregar_conhecidos() -> dict[str, CredencialIP]:
    """Lê ips_conhecidos.json. Ausente/corrompido -> dict vazio."""
    if not ARQUIVO_CONHECIDOS.exists():
        return {}
    try:
        dados = json.loads(ARQUIVO_CONHECIDOS.read_text(encoding="utf-8"))
        mapa = {
            ip: CredencialIP(**cred) for ip, cred in dados.get("ips", {}).items()
        }
        _log.info("IPs conhecidos carregados: %d", len(mapa))
        return mapa
    except (json.JSONDecodeError, OSError, TypeError) as exc:
        _log.warning("Falha ao ler ips conhecidos (%s): %s", ARQUIVO_CONHECIDOS, exc)
        return {}


def salvar_conhecidos(mapa: dict[str, CredencialIP]) -> None:
    _salvar_json(
        ARQUIVO_CONHECIDOS,
        {"version": 1, "ips": {ip: asdict(c) for ip, c in mapa.items()}},
    )


def lembrar_ip(mapa: dict[str, CredencialIP], ip: str, cred: CredencialIP) -> None:
    """Insere/atualiza mapa[ip] e persiste."""
    cred.atualizado_em = datetime.now().isoformat(timespec="seconds")
    mapa[ip] = cred
    salvar_conhecidos(mapa)
    _log.info("IP %s salvo no mapa de conhecidos (usuario=%s)", ip, cred.usuario)


def esquecer_ip(mapa: dict[str, CredencialIP], ip: str) -> None:
    if ip in mapa:
        del mapa[ip]
        salvar_conhecidos(mapa)
        _log.info("IP %s esquecido", ip)


# --------------------------------------------------------------------------
# Resolver: descobre par + caminho que entrega vídeo para um IP
# --------------------------------------------------------------------------

def _so_path(url: str) -> str:
    p = urlsplit(url)
    return (p.path + (f"?{p.query}" if p.query else "")) or "/"


def _promover_caminho(candidatos: list[str], caminho: str | None) -> None:
    """Move um caminho conhecido para o início da lista de tentativas."""
    if caminho and caminho in candidatos:
        candidatos.remove(caminho)
        candidatos.insert(0, caminho)


def resolver_ip(
    ip: str,
    candidatos: list[str],
    vault: list[Par],
    conhecidos: dict[str, CredencialIP],
    monta_url: Callable[[str, str, str, str], str],
    *,
    ao_tentar: Callable[[str, str, str], None] | None = None,
    timeout: float = 6.0,
    max_falhas_auth: int = DEFAULT_MAX_FALHAS_AUTH,
    intervalo_auth: float = DEFAULT_INTERVALO_AUTH,
    diagnostico: dict[str, Any] | None = None,
) -> tuple[InfoStream, Par, str] | None:
    """Resolve (InfoStream, Par, caminho) para um IP com proteção anti-bloqueio.

    1. Lembrado primeiro: se ip está em conhecidos, testa exatamente aquele
       par+caminho. Sucesso -> retorna sem força bruta.
    2. Se o lembrado falhar por caminho (ex.: 404), tenta os demais caminhos
       com a credencial já conhecida antes de abrir o cofre.
    3. Se falhar por autenticação (401/403), descarta o par que falhou, promove
       o caminho conhecido ao topo e interrompe ao atingir ``max_falhas_auth``
       falhas com pausa ``intervalo_auth`` entre tentativas, evitando lockout.
    """
    tentativas = 0
    falhas_auth = 0
    limite_atingido = False
    ultimo_erro: InfoStream | None = None
    pares_descartados: set[tuple[str, str]] = set()
    candidatos_ordenados = list(dict.fromkeys(candidatos))

    def _registrar_diag(*, sucesso: bool = False) -> None:
        if diagnostico is None:
            return
        diagnostico["erro_tipo"] = None if sucesso else (ultimo_erro.erro_tipo if ultimo_erro else None)
        diagnostico["mensagem"] = "" if sucesso else (ultimo_erro.mensagem if ultimo_erro else "")
        diagnostico["tentativas"] = tentativas
        diagnostico["falhas_auth"] = falhas_auth
        diagnostico["limite_atingido"] = False if sucesso else limite_atingido

    def _sucesso(info: InfoStream, par: Par) -> tuple[InfoStream, Par, str]:
        caminho = _so_path(info.url)
        cred = CredencialIP(
            usuario=par.usuario,
            senha=par.senha,
            caminho=caminho,
            url=info.url,
            codec=info.codec,
            resolucao=info.resolucao,
        )
        lembrar_ip(conhecidos, ip, cred)
        _log.info("IP %s resolvido: usuario=%s caminho=%s", ip, par.usuario, caminho)
        _registrar_diag(sucesso=True)
        return (info, par, caminho)

    def _tratar_falha_step(par: Par, diag_step: dict[str, Any]) -> bool:
        """Atualiza estado pós-descobrir_stream; retorna True se deve abortar."""
        nonlocal falhas_auth, limite_atingido, ultimo_erro
        step_erro = diag_step.get("ultimo_erro")
        if step_erro is None:
            return False
        ultimo_erro = step_erro
        if step_erro.erro_tipo in (ERRO_FERRAMENTA, ERRO_BLOQUEIO, ERRO_REDE):
            return True
        if step_erro.erro_tipo == ERRO_AUTH:
            pares_descartados.add(par.chave())
            usa_cred = bool(par.usuario or par.senha)
            if usa_cred:
                falhas_auth += 1
            _promover_caminho(candidatos_ordenados, diag_step.get("caminho_auth"))
            if usa_cred and falhas_auth >= max_falhas_auth:
                limite_atingido = True
                _log.warning(
                    "IP %s: limite de %d falhas de autenticação atingido; interrompendo redescoberta",
                    ip,
                    max_falhas_auth,
                )
                return True
        return False

    # 1. Lembrado primeiro
    lembrado = conhecidos.get(ip)
    if lembrado:
        url_montada = monta_url(ip, lembrado.caminho, lembrado.usuario, lembrado.senha)
        porta_lembrada = urlsplit(lembrado.url).port or 554
        porta_alvo = urlsplit(url_montada).port or 554
        url_lembrado = lembrado.url if porta_lembrada == porta_alvo else url_montada

        if ao_tentar:
            ao_tentar(ip, lembrado.caminho, f"{lembrado.usuario or '(sem auth)'} ★")
        info = validar_stream(url_lembrado, timeout=timeout)
        tentativas += 1
        if info.funciona:
            return _sucesso(info, Par(lembrado.usuario, lembrado.senha))

        ultimo_erro = info
        par_lembrado = Par(lembrado.usuario, lembrado.senha)
        _log.info("IP %s: lembrado falhou (%s)", ip, info.erro_tipo or "desconhecido")

        if info.erro_tipo in (ERRO_FERRAMENTA, ERRO_BLOQUEIO, ERRO_REDE):
            _registrar_diag()
            return None

        if info.erro_tipo == ERRO_AUTH:
            pares_descartados.add(par_lembrado.chave())
            if par_lembrado.usuario or par_lembrado.senha:
                falhas_auth += 1
            _promover_caminho(candidatos_ordenados, lembrado.caminho)
            if falhas_auth >= max_falhas_auth:
                limite_atingido = True
                _log.warning(
                    "IP %s: limite de %d falhas de autenticação atingido; interrompendo redescoberta",
                    ip,
                    max_falhas_auth,
                )
                _registrar_diag()
                return None
        else:
            outros_caminhos = [c for c in candidatos_ordenados if c != lembrado.caminho]
            if outros_caminhos:
                diag_step: dict[str, Any] = {}
                info_ok = descobrir_stream(
                    lambda c, _p=par_lembrado: monta_url(ip, c, _p.usuario, _p.senha),
                    outros_caminhos,
                    timeout=timeout,
                    ao_tentar=(
                        (lambda c, _p=par_lembrado: ao_tentar(ip, c, _p.rotulo()))
                        if ao_tentar
                        else None
                    ),
                    diagnostico=diag_step,
                )
                tentativas += diag_step.get("tentativas", 0)
                if info_ok and info_ok.funciona:
                    return _sucesso(info_ok, par_lembrado)
                if _tratar_falha_step(par_lembrado, diag_step):
                    _registrar_diag()
                    return None
            pares_descartados.add(par_lembrado.chave())

    # 2. Cofre com limite anti-bloqueio + 3. fallback sem auth
    tentativas_pares: list[Par] = []
    vistos: set[tuple[str, str]] = set(pares_descartados)
    for p in vault:
        ch = p.chave()
        if ch not in vistos:
            vistos.add(ch)
            tentativas_pares.append(p)
    if ("", "") not in vistos:
        tentativas_pares.append(Par("", ""))

    for par in tentativas_pares:
        usa_cred = bool(par.usuario or par.senha)
        if usa_cred and falhas_auth >= max_falhas_auth:
            limite_atingido = True
            _log.warning(
                "IP %s: limite de %d falhas de autenticação atingido; interrompendo redescoberta",
                ip,
                max_falhas_auth,
            )
            break
        if not usa_cred and limite_atingido:
            break
        if usa_cred and falhas_auth > 0 and intervalo_auth > 0:
            time.sleep(intervalo_auth)

        diag_step = {}
        info = descobrir_stream(
            lambda c, _p=par: monta_url(ip, c, _p.usuario, _p.senha),
            candidatos_ordenados,
            timeout=timeout,
            ao_tentar=(
                (lambda c, _p=par: ao_tentar(ip, c, _p.rotulo()))
                if ao_tentar
                else None
            ),
            diagnostico=diag_step,
        )
        tentativas += diag_step.get("tentativas", 0)
        if info and info.funciona:
            return _sucesso(info, par)
        if _tratar_falha_step(par, diag_step):
            break

    _registrar_diag()
    return None
