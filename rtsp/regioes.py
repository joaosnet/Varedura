"""Regiões salvas (cartões fixos): faixas remotas e câmeras únicas.

Persistido em regioes.json (texto puro, gitignored). Cada região vira um
cartão clicável na aba de rede, ao lado das redes locais detectadas.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from rtsp import DATA_DIR as _DIR
from rtsp.log import obter_logger

_log = obter_logger("regioes")

ARQUIVO_REGIOES = _DIR / "regioes.json"

TIPO_REDE = "rede"
TIPO_CAMERA = "camera"


@dataclass
class Regiao:
    """Uma região salva: faixa de rede ('rede') ou câmera única ('camera')."""

    rotulo: str
    tipo: str              # "rede" | "camera"
    endereco: str          # rede: "200.150.10" ou CIDR "10.0.0.0/22" | camera: host/IP/DDNS
    porta: int = 554       # usado no tipo "camera"
    caminho: str = ""      # opcional p/ camera (ex.: "/stream1")

    def chave(self) -> tuple:
        return (self.tipo, self.endereco, self.porta, self.caminho)

    def descricao(self) -> str:
        if self.tipo == TIPO_CAMERA:
            alvo = f"{self.endereco}:{self.porta}"
        elif "/" in self.endereco:
            alvo = self.endereco
        else:
            alvo = f"{self.endereco}.x"
        return f"📍 {self.rotulo} · {alvo}"


def _salvar_json(caminho: Path, dados: dict) -> None:
    tmp = caminho.with_suffix(caminho.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, caminho)


def carregar_regioes() -> list[Regiao]:
    """Lê regioes.json. Ausente/corrompido -> lista vazia (loga warning)."""
    if not ARQUIVO_REGIOES.exists():
        return []
    try:
        dados = json.loads(ARQUIVO_REGIOES.read_text(encoding="utf-8"))
        regioes = [
            Regiao(
                rotulo=r["rotulo"],
                tipo=r.get("tipo", TIPO_REDE),
                endereco=r["endereco"],
                porta=int(r.get("porta", 554)),
                caminho=r.get("caminho", ""),
            )
            for r in dados.get("regioes", [])
        ]
        _log.info("Regiões carregadas: %d", len(regioes))
        return regioes
    except (json.JSONDecodeError, OSError, KeyError, TypeError, ValueError) as exc:
        _log.warning("Falha ao ler regiões (%s): %s", ARQUIVO_REGIOES, exc)
        return []


def salvar_regioes(regioes: list[Regiao]) -> None:
    _salvar_json(
        ARQUIVO_REGIOES, {"version": 1, "regioes": [asdict(r) for r in regioes]}
    )
    _log.info("Regiões salvas: %d", len(regioes))


def adicionar_regiao(
    regioes: list[Regiao],
    rotulo: str,
    tipo: str,
    endereco: str,
    porta: int = 554,
    caminho: str = "",
) -> bool:
    """Acrescenta se ainda não existe (mesma chave). False se duplicado."""
    nova = Regiao(rotulo=rotulo, tipo=tipo, endereco=endereco, porta=porta, caminho=caminho)
    if any(r.chave() == nova.chave() for r in regioes):
        return False
    regioes.append(nova)
    return True


def remover_regiao(regioes: list[Regiao], indice: int) -> None:
    if 0 <= indice < len(regioes):
        regioes.pop(indice)
