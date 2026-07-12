"""Mascot exports with the Pillow/rich-pixels renderer loaded on demand."""

from __future__ import annotations

from typing import Any

from mascot.frames import FRAMES, STATES

__all__ = ["FRAMES", "STATES", "MascotRenderer"]


def __getattr__(name: str) -> Any:
    if name == "MascotRenderer":
        from mascot.renderer import MascotRenderer

        return MascotRenderer
    raise AttributeError(name)
