"""Cofre de credenciais + mapa de IPs já resolvidos (auto-login).

Dois arquivos JSON texto puro, na pasta do projeto (gitignored):
- credenciais.json  -> lista de pares usuário/senha gerenciada no TUI
- ips_conhecidos.json -> ip -> par/caminho/url que funcionou (consultado primeiro)
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from rtsp import DATA_DIR as _DIR
from rtsp.log import obter_logger
from rtsp.video import InfoStream, descobrir_stream, validar_stream

_log = obter_logger("credenciais")

ARQUIVO_VAULT = _DIR / "credenciais.json"
ARQUIVO_CONHECIDOS = _DIR / "ips_conhecidos.json"


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
    from urllib.parse import urlsplit

    p = urlsplit(url)
    return (p.path + (f"?{p.query}" if p.query else "")) or "/"


def resolver_ip(
    ip: str,
    candidatos: list[str],
    vault: list[Par],
    conhecidos: dict[str, CredencialIP],
    monta_url: Callable[[str, str, str, str], str],
    *,
    ao_tentar: Callable[[str, str, str], None] | None = None,
    timeout: float = 6.0,
) -> tuple[InfoStream, Par, str] | None:
    """Resolve (InfoStream, Par, caminho) para um IP, com ordenação eficiente.

    1. Lembrado primeiro: se ip está em conhecidos, testa exatamente aquele
       par+caminho (1 ffprobe). Sucesso -> retorna sem força bruta.
    2. Força bruta no cofre: para cada Par, usa descobrir_stream sobre os caminhos.
    3. Fallback sem auth: tenta uma passada com par vazio (câmeras sem senha).

    No primeiro sucesso, persiste no mapa de conhecidos e retorna.
    """

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
        return (info, par, caminho)

    # 1. Lembrado primeiro
    lembrado = conhecidos.get(ip)
    if lembrado:
        if ao_tentar:
            ao_tentar(ip, lembrado.caminho, f"{lembrado.usuario or '(sem auth)'} ★")
        info = validar_stream(lembrado.url, timeout=timeout)
        if info.funciona:
            return _sucesso(info, Par(lembrado.usuario, lembrado.senha))
        _log.info("IP %s: lembrado falhou, re-descobrindo", ip)

    # 2. Força bruta no cofre + 3. fallback sem auth
    tentativas = list(vault)
    if not any(p.usuario == "" and p.senha == "" for p in tentativas):
        tentativas.append(Par("", ""))

    for par in tentativas:
        info = descobrir_stream(
            lambda c, _p=par: monta_url(ip, c, _p.usuario, _p.senha),
            candidatos,
            timeout=timeout,
            ao_tentar=(
                (lambda c, _p=par: ao_tentar(ip, c, _p.rotulo()))
                if ao_tentar
                else None
            ),
        )
        if info and info.funciona:
            return _sucesso(info, par)

    return None
