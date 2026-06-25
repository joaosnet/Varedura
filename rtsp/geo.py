"""Geolocalização de IP/host via ip-api.com (stdlib, com cache)."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from rtsp.log import obter_logger

_log = obter_logger("geo")

# Cache em memória: host -> Geo | None (None = falhou/privado).
_cache: dict[str, "Geo | None"] = {}


@dataclass(frozen=True)
class Geo:
    lat: float
    lon: float
    cidade: str
    pais: str
    query: str

    @property
    def local_txt(self) -> str:
        partes = [p for p in (self.cidade, self.pais) if p]
        return ", ".join(partes) or self.query


def geolocalizar(host: str = "", timeout: float = 5.0) -> Geo | None:
    """Geolocaliza um IP/hostname. host vazio = IP público desta máquina.

    Retorna None se falhar ou se for um IP privado (a API recusa).
    Resultados são cacheados por host.
    """
    chave = host or "__self__"
    if chave in _cache:
        return _cache[chave]

    url = f"http://ip-api.com/json/{host}" if host else "http://ip-api.com/json/"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "varedura-rtsp/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            dados = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError) as exc:
        _log.warning("Geolocalização falhou (%s): %s", host or "self", exc)
        _cache[chave] = None
        return None

    if dados.get("status") != "success":
        _log.info("Geo sem sucesso (%s): %s", host or "self", dados.get("message"))
        _cache[chave] = None
        return None

    geo = Geo(
        lat=float(dados.get("lat", 0.0)),
        lon=float(dados.get("lon", 0.0)),
        cidade=dados.get("city", ""),
        pais=dados.get("country", ""),
        query=dados.get("query", host),
    )
    _log.info("Geo %s -> %s (%.3f, %.3f)", host or "self", geo.local_txt, geo.lat, geo.lon)
    _cache[chave] = geo
    return geo
