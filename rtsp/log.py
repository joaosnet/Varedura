"""Configuração central de logging do scanner RTSP do Varedura.

Grava em arquivo (logs/rtsp.log, com rotação) para diagnóstico posterior.
Use `obter_logger(__name__)` em cada módulo.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

ARQUIVO_LOG = Path(__file__).resolve().parents[1] / "logs" / "rtsp.log"

_configurado = False


def configurar(nivel: int = logging.DEBUG) -> Path:
    """Configura o logging raiz para gravar em arquivo. Idempotente."""
    global _configurado
    if _configurado:
        return ARQUIVO_LOG

    ARQUIVO_LOG.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        ARQUIVO_LOG,
        maxBytes=1_000_000,  # 1 MB por arquivo
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    raiz = logging.getLogger("rtsp")
    raiz.setLevel(nivel)
    raiz.addHandler(handler)
    raiz.propagate = False
    raiz.info("=== Sessão iniciada ===")
    _configurado = True
    return ARQUIVO_LOG


def obter_logger(nome: str) -> logging.Logger:
    """Retorna um logger filho do namespace rtsp, configurando se preciso."""
    configurar()
    return logging.getLogger(f"rtsp.{nome}")
