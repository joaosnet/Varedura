"""Mapa-múndi real em Braille (alta resolução) com pins por lat/lon.

A terra é definida por bandas de latitude (lon_min, lon_max) por continente e
interpolada, gerando silhuetas reconhecíveis. É rasterizada num bitmap e
empacotada em caracteres Braille (2x4 pontos por caractere). Os pins são
sobrepostos como números coloridos na célula correspondente.
"""

from __future__ import annotations

from dataclasses import dataclass

from rich.text import Text

# Resolução do bitmap (pixels). Braille = 2 col x 4 lin por caractere.
PX_W, PX_H = 128, 72
COLS, LINS = PX_W // 2, PX_H // 4  # 64 x 18 caracteres

_CORES_PIN = ["green", "cyan", "magenta", "yellow", "red", "blue"]

# Bandas (lat: (lon_min, lon_max)) por continente, do norte ao sul.
_CONTINENTES: list[list[tuple[float, float, float]]] = [
    [  # América do Norte
        (72, -90, -60), (70, -160, -60), (60, -165, -58), (55, -160, -55),
        (50, -128, -58), (45, -125, -62), (40, -124, -70), (35, -120, -75),
        (30, -116, -80), (25, -110, -83), (20, -106, -86), (15, -95, -83),
        (12, -90, -83),
    ],
    [  # Groenlândia
        (82, -40, -20), (78, -55, -18), (70, -52, -22), (62, -48, -40),
    ],
    [  # América do Sul
        (12, -72, -60), (10, -78, -50), (5, -80, -48), (0, -80, -35),
        (-5, -80, -35), (-10, -78, -35), (-15, -73, -38), (-20, -70, -40),
        (-25, -72, -45), (-30, -73, -50), (-35, -73, -55), (-40, -74, -62),
        (-45, -75, -66), (-50, -75, -68), (-54, -74, -70),
    ],
    [  # Europa
        (71, 5, 40), (65, -10, 40), (60, -10, 42), (55, -10, 40),
        (50, -9, 40), (45, -8, 40), (42, -8, 30), (38, -8, 25), (36, -6, 22),
    ],
    [  # África
        (37, -6, 11), (35, -8, 30), (30, -10, 32), (25, -15, 36),
        (20, -17, 38), (15, -17, 42), (10, -12, 45), (5, -8, 43),
        (0, 8, 42), (-5, 12, 40), (-10, 13, 40), (-15, 12, 38),
        (-20, 14, 36), (-25, 16, 33), (-30, 17, 31), (-34, 18, 27),
    ],
    [  # Ásia
        (70, 60, 180), (65, 40, 180), (60, 30, 180), (55, 35, 170),
        (50, 40, 145), (45, 35, 145), (40, 26, 135), (35, 35, 140),
        (30, 45, 122), (25, 50, 122), (20, 55, 110), (15, 73, 105),
        (10, 76, 107), (7, 79, 100),
    ],
    [  # Indonésia / Sudeste Asiático
        (6, 95, 120), (2, 98, 140), (-2, 100, 150), (-8, 110, 150),
    ],
    [  # Oceania
        (-10, 130, 145), (-12, 125, 145), (-15, 122, 148), (-20, 114, 150),
        (-25, 114, 153), (-30, 115, 151), (-35, 118, 150), (-38, 140, 148),
    ],
]

# Mapa (dx, dy)->bit do caractere Braille.
_BRAILLE_BITS = {
    (0, 0): 0x01, (0, 1): 0x02, (0, 2): 0x04, (0, 3): 0x40,
    (1, 0): 0x08, (1, 1): 0x10, (1, 2): 0x20, (1, 3): 0x80,
}


@dataclass
class Pino:
    lat: float
    lon: float
    numero: int
    cor: str = "yellow"


def _interp(bandas: list[tuple[float, float, float]], lat: float):
    """Interpola (lon_min, lon_max) de um continente numa dada latitude."""
    if lat > bandas[0][0] or lat < bandas[-1][0]:
        return None
    for (lat_a, lo_a, hi_a), (lat_b, lo_b, hi_b) in zip(bandas, bandas[1:]):
        if lat_b <= lat <= lat_a:
            t = 0.0 if lat_a == lat_b else (lat_a - lat) / (lat_a - lat_b)
            return (lo_a + (lo_b - lo_a) * t, hi_a + (hi_b - hi_a) * t)
    return None


def _eh_terra(lat: float, lon: float) -> bool:
    for bandas in _CONTINENTES:
        faixa = _interp(bandas, lat)
        if faixa and faixa[0] <= lon <= faixa[1]:
            return True
    return False


def _px_para_latlon(px: int, py: int) -> tuple[float, float]:
    lon = px / (PX_W - 1) * 360 - 180
    lat = 90 - py / (PX_H - 1) * 180
    return lat, lon


def _gerar_bitmap() -> list[list[bool]]:
    return [
        [_eh_terra(*_px_para_latlon(px, py)) for px in range(PX_W)]
        for py in range(PX_H)
    ]


# Bitmap gerado uma vez (custa pouco e não muda).
_BITMAP = _gerar_bitmap()


def projetar_celula(lat: float, lon: float) -> tuple[int, int]:
    """lat/lon -> (coluna, linha) em caracteres."""
    px = round((lon + 180) / 360 * (PX_W - 1))
    py = round((90 - lat) / 180 * (PX_H - 1))
    cx = max(0, min(COLS - 1, px // 2))
    cy = max(0, min(LINS - 1, py // 4))
    return cx, cy


def render(pinos: list[Pino]) -> Text:
    """Renderiza o mapa Braille com os pinos como números coloridos."""
    # Posições dos pinos por célula (resolve colisão deslocando à direita).
    pin_por_celula: dict[tuple[int, int], Pino] = {}
    for p in pinos:
        cx, cy = projetar_celula(p.lat, p.lon)
        while (cx, cy) in pin_por_celula and cx < COLS - 1:
            cx += 1
        pin_por_celula[(cx, cy)] = p

    texto = Text()
    for cy in range(LINS):
        for cx in range(COLS):
            pino = pin_por_celula.get((cx, cy))
            if pino is not None:
                rotulo = str(pino.numero) if pino.numero <= 9 else "*"
                texto.append(rotulo, style=f"bold {pino.cor}")
                continue
            bits = 0
            for (dx, dy), bit in _BRAILLE_BITS.items():
                px, py = cx * 2 + dx, cy * 4 + dy
                if py < PX_H and px < PX_W and _BITMAP[py][px]:
                    bits |= bit
            texto.append(chr(0x2800 + bits), style="grey39")
        if cy < LINS - 1:
            texto.append("\n")
    return texto


def cor_para(indice: int) -> str:
    return _CORES_PIN[indice % len(_CORES_PIN)]
