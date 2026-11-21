"""Breakpoints únicos da TUI: uma só régua de largura para todas as abas.

Antes cada aba tinha seus próprios limites (48, 54, 68, 70, 76, 82, 90, 104,
108, 110, 112, 132, 140 colunas).  Agora há três faixas e o número de colunas
de cada grade é função da faixa.  Módulo puro, sem dependências.
"""

from __future__ import annotations

NARROW_MAX = 76  # abaixo disso: celular em retrato / terminal estreito
WIDE_MIN = 112  # a partir disso: desktop largo

NARROW = "narrow"
MEDIUM = "medium"
WIDE = "wide"
TIERS = (NARROW, MEDIUM, WIDE)

# Colunas por grade em (estreito, médio, largo).
GRID_COLUMNS: dict[str, tuple[int, int, int]] = {
    "network-cards": (1, 2, 3),
    "network-controls": (2, 3, 4),
    "repair-actions": (1, 2, 3),
    "step-grid": (1, 2, 3),
    "termux-tools": (1, 2, 3),
    "camera-cards": (1, 1, 2),
}


def layout_tier(width: int) -> str:
    """Faixa de layout para a largura do terminal em colunas."""
    if width < NARROW_MAX:
        return NARROW
    return WIDE if width >= WIDE_MIN else MEDIUM


def columns_for(grid: str, width: int) -> int:
    """Número de colunas da grade ``grid`` na largura dada."""
    return GRID_COLUMNS[grid][TIERS.index(layout_tier(width))]


__all__ = [
    "GRID_COLUMNS",
    "MEDIUM",
    "NARROW",
    "NARROW_MAX",
    "TIERS",
    "WIDE",
    "WIDE_MIN",
    "columns_for",
    "layout_tier",
]
