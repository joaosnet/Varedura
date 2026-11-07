"""Configuração central de logging do scanner RTSP do Varedura.

Grava em arquivo (logs/rtsp.log, com rotação) para diagnóstico posterior.
Use `obter_logger(__name__)` em cada módulo.
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

ARQUIVO_LOG = Path(__file__).resolve().parents[1] / "logs" / "rtsp.log"

_configurado = False

_RTSP_URL_RE = re.compile(r"""(?i)\brtsps?://[^\s<>"'{}]+""")
_SECRET_FIELD_RE = re.compile(
    r"(?i)\b(password|passwd|pwd|senha|token)=([^&\s,;]+)"
)
_BASIC_AUTH_RE = re.compile(r"(?i)(authorization:\s*basic\s+)[A-Za-z0-9+/=]+")


def redact_sensitive(value: Any) -> str:
    """Remove credenciais de texto destinado a logs ou respostas públicas.

    A URL RTSP inteira é opaca: nem userinfo, host/IP, caminho ou query chegam
    ao handler. Campos de senha e cabeçalhos Basic Auth também são removidos.
    """
    text = str(value)

    def replace_rtsp(match: re.Match[str]) -> str:
        raw = match.group(0)
        trailing = ""
        while raw and raw[-1] in ".,;:!?)]}":
            trailing = raw[-1] + trailing
            raw = raw[:-1]
        scheme = "rtsps" if raw[:6].casefold() == "rtsps:" else "rtsp"
        return f"{scheme}://<redacted>{trailing}"

    text = _RTSP_URL_RE.sub(replace_rtsp, text)
    text = _SECRET_FIELD_RE.sub(r"\1=<redacted>", text)
    return _BASIC_AUTH_RE.sub(r"\1<redacted>", text)


def _redact_arg(value: Any) -> Any:
    if isinstance(value, tuple):
        return tuple(_redact_arg(item) for item in value)
    if isinstance(value, list):
        return [_redact_arg(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact_arg(item) for key, item in value.items()}
    if isinstance(value, str):
        return redact_sensitive(value)
    return value


class RedactingFilter(logging.Filter):
    """Filtro central aplicado a todo registro do namespace ``rtsp``."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive(record.msg)
        record.args = _redact_arg(record.args)
        if record.exc_text:
            record.exc_text = redact_sensitive(record.exc_text)
        return True


class RedactingFormatter(logging.Formatter):
    """Última barreira, incluindo texto produzido por ``formatException``."""

    def format(self, record: logging.LogRecord) -> str:
        return redact_sensitive(super().format(record))


def configurar(nivel: int = logging.DEBUG) -> Path:
    """Configura o logging raiz para gravar em arquivo. Idempotente."""
    global _configurado
    if _configurado:
        return ARQUIVO_LOG

    try:
        ARQUIVO_LOG.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            ARQUIVO_LOG,
            maxBytes=1_000_000,  # 1 MB por arquivo
            backupCount=3,
            encoding="utf-8",
        )
        handler.addFilter(RedactingFilter())
        handler.setFormatter(
            RedactingFormatter(
                "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
    except OSError:
        handler = logging.NullHandler()
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
