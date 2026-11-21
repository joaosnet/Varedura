"""Tema próprio do Varedura (escuro e claro) para a TUI Textual.

Uma única paleta para todas as abas, em vez do tema padrão do Textual.  As
variáveis ``$primary``, ``$accent``, ``$success`` etc. usadas no CSS do app
passam a vir daqui, então o visual é o mesmo no Windows, Linux e Termux.
"""

from __future__ import annotations

from textual.theme import Theme

DARK = "varedura-dark"
LIGHT = "varedura-light"

VAREDURA_DARK = Theme(
    name=DARK,
    dark=True,
    primary="#3B82F6",
    secondary="#22D3EE",
    accent="#F59E0B",
    success="#22C55E",
    warning="#EAB308",
    error="#EF4444",
    foreground="#E6EDF3",
    background="#0D1117",
    surface="#161B22",
    panel="#1C2430",
    variables={
        "footer-key-foreground": "#F59E0B",
        "border": "#30507A",
        "border-blurred": "#263347",
    },
)

VAREDURA_LIGHT = Theme(
    name=LIGHT,
    dark=False,
    primary="#1351B4",
    secondary="#0E7490",
    accent="#B45309",
    success="#15803D",
    warning="#A16207",
    error="#B91C1C",
    foreground="#1F2328",
    background="#F6F8FA",
    surface="#FFFFFF",
    panel="#E7ECF2",
    variables={
        "footer-key-foreground": "#B45309",
    },
)

THEMES = (VAREDURA_DARK, VAREDURA_LIGHT)


def theme_name(dark: bool) -> str:
    return DARK if dark else LIGHT


__all__ = ["DARK", "LIGHT", "THEMES", "VAREDURA_DARK", "VAREDURA_LIGHT", "theme_name"]
